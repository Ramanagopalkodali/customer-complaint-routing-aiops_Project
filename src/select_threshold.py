"""Choose a human-review threshold from saved validation predictions only."""
import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def choose_threshold(actual, predicted, confidence,
                     target_accuracy=0.95, min_auto=100):
    """Select maximum coverage on a fixed threshold grid; otherwise review all."""
    actual = np.asarray(actual)
    predicted = np.asarray(predicted)
    confidence = np.asarray(confidence, dtype=float)
    if not (len(actual) == len(predicted) == len(confidence)) or not len(actual):
        raise ValueError("Prediction arrays must have equal, nonzero lengths")
    if not np.isfinite(confidence).all() or (
        (confidence < 0) | (confidence > 1)
    ).any():
        raise ValueError("Confidence must be finite and between zero and one")
    if not 0 < target_accuracy <= 1 or min_auto < 1:
        raise ValueError("Invalid operating requirements")

    records = []
    for threshold in np.round(np.arange(0.50, 1.00, 0.01), 2):
        accepted = confidence >= threshold
        count = int(accepted.sum())
        accuracy = (
            float((actual[accepted] == predicted[accepted]).mean())
            if count else None
        )
        records.append({
            "threshold": float(threshold),
            "automatic_count": count,
            "coverage": count / len(actual),
            "automatic_accuracy": accuracy,
        })
    curve = pd.DataFrame(records)
    eligible = curve[
        (curve["automatic_count"] >= min_auto)
        & (curve["automatic_accuracy"] >= target_accuracy)
    ]
    if eligible.empty:
        return {
            "threshold": None,
            "automatic_count": 0,
            "coverage": 0.0,
            "automatic_accuracy": None,
            "mode": "review_all",
        }, curve

    best = eligible.sort_values(
        ["coverage", "threshold"], ascending=[False, True]
    ).iloc[0]
    return {
        "threshold": float(best["threshold"]),
        "automatic_count": int(best["automatic_count"]),
        "coverage": float(best["coverage"]),
        "automatic_accuracy": float(best["automatic_accuracy"]),
        "mode": "threshold",
    }, curve


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def team_thresholds(data, target_accuracy=0.95, min_auto=100):
    """Select thresholds using predicted categories available at inference."""
    thresholds = {}
    curves = []
    for label in sorted(data["predicted"].unique()):
        group = data[data["predicted"] == label]
        selected, curve = choose_threshold(
            group["actual"], group["predicted"], group["confidence"],
            target_accuracy=target_accuracy, min_auto=min_auto,
        )
        thresholds[label] = selected["threshold"]
        curve.insert(0, "predicted_category", label)
        curves.append(curve)
    return thresholds, pd.concat(curves, ignore_index=True)


def routing_mask(predicted, confidence, thresholds):
    """Unknown or disabled categories always require human review."""
    return np.array([
        thresholds.get(label) is not None
        and float(score) >= thresholds[label]
        for label, score in zip(predicted, confidence)
    ], dtype=bool)


def main():
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs" / "threshold.log", mode="w"),
        ],
    )
    comparison = json.loads(
        (ROOT / "reports/training/comparison.json").read_text()
    )
    name = comparison["selected_model"]
    prediction_path = (
        ROOT / "reports/training" / name / "validation_predictions.csv"
    )
    model_path = ROOT / "artifacts/training" / f"{name}.joblib"
    data = pd.read_csv(prediction_path)
    thresholds, curve = team_thresholds(data)
    accepted = routing_mask(
        data["predicted"], data["confidence"], thresholds
    )
    correct = data["actual"].to_numpy() == data["predicted"].to_numpy()
    count = int(accepted.sum())

    policy = {
        "policy_version": 2,
        "mode": "per_predicted_category",
        "thresholds": thresholds,
        "default_action": "human_review",
        "review_rule": "review if category has no threshold or confidence is below it",
        "model_name": name,
        "training_run_id": comparison["results"][name]["run_id"],
        "model_sha256": sha256(model_path),
        "validation_predictions_sha256": sha256(prediction_path),
        "target_validation_routing_precision": 0.95,
        "minimum_validation_automatic_count_per_category": 100,
        "validation_rows": len(data),
        "automatic_count": count,
        "coverage": count / len(data),
        "automatic_accuracy": float(correct[accepted].mean()) if count else None,
        "test_set_used": False,
    }

    out = ROOT / "reports/threshold"
    out.mkdir(parents=True, exist_ok=True)
    curve.to_csv(out / "threshold_curve.csv", index=False)
    team_rows = []
    class_rows = []
    for label in sorted(set(data["actual"]) | set(data["predicted"])):
        routed = accepted & (data["predicted"].to_numpy() == label)
        actual = data["actual"].to_numpy() == label
        routed_count = int(routed.sum())
        actual_count = int(actual.sum())
        team_rows.append({
            "predicted_category": label,
            "threshold": thresholds.get(label),
            "automatically_routed": routed_count,
            "correctly_routed": int((routed & correct).sum()),
            "routing_precision": float(correct[routed].mean())
                if routed_count else None,
        })
        class_rows.append({
            "actual_class": label,
            "total": actual_count,
            "correctly_auto_routed": int((actual & accepted & correct).sum()),
            "fraction_correctly_auto_routed":
                float((actual & accepted & correct).sum() / actual_count)
                if actual_count else None,
        })
    team_report = pd.DataFrame(team_rows)
    team_report.to_csv(out / "predicted_team_routing.csv", index=False)
    pd.DataFrame(class_rows).to_csv(
        out / "per_class_routing.csv", index=False
    )
    (ROOT / "artifacts/policy.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n"
    )
    logging.info("Saved policy:\n%s", json.dumps(policy, indent=2))
    logging.info("Validation team routing:\n%s",
                 team_report.to_string(index=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Threshold selection FAILED")
        raise

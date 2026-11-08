"""Evaluate the frozen model and routing policy on October's held-out test set."""
import hashlib
import json
import logging
import subprocess
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay, accuracy_score, classification_report,
    confusion_matrix, f1_score,
)
from threadpoolctl import threadpool_limits

from src.select_threshold import routing_mask

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    """Save test metrics, routing results, predictions and MLflow provenance."""
    out = ROOT / "reports" / "test"
    out.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs" / "evaluation.log", mode="w"),
        ],
    )
    policy_path = ROOT / "artifacts/policy.json"
    policy = json.loads(policy_path.read_text())
    if policy["mode"] != "per_predicted_category":
        raise ValueError("Expected the frozen category-specific policy")
    model_path = (
        ROOT / "artifacts/training" / f"{policy['model_name']}.joblib"
    )
    if sha256(model_path) != policy["model_sha256"]:
        raise ValueError("Model does not match the frozen routing policy")

    test_path = ROOT / "data/processed/test.csv"
    data = pd.read_csv(test_path, dtype=str, keep_default_na=False)
    if data.empty or not data["date_received"].between(
        "2024-10-01", "2024-10-31"
    ).all():
        raise ValueError("Expected a nonempty October test set")

    model = joblib.load(model_path)
    if set(data["label"]) != set(model.classes_):
        raise ValueError("Test labels do not match model classes")
    logging.info("Evaluating frozen model on %s October complaints", len(data))
    with threadpool_limits(limits=2):
        probabilities = model.predict_proba(data["text"])
    if probabilities.shape != (len(data), len(model.classes_)):
        raise ValueError("Unexpected probability output shape")
    if not np.isfinite(probabilities).all() or (
        (probabilities < 0) | (probabilities > 1)
    ).any() or not np.allclose(probabilities.sum(axis=1), 1, atol=1e-5):
        raise ValueError("Invalid probability output")

    predicted = model.classes_[probabilities.argmax(axis=1)]
    confidence = probabilities.max(axis=1)
    accepted = routing_mask(predicted, confidence, policy["thresholds"])
    actual = data["label"].to_numpy()
    correct = actual == predicted
    count = int(accepted.sum())

    metrics = {
        "test_macro_f1": float(f1_score(actual, predicted, average="macro")),
        "test_accuracy": float(accuracy_score(actual, predicted)),
        "test_automatic_coverage": float(accepted.mean()),
        "test_review_rate": float((~accepted).mean()),
        "test_automatic_count": count,
    }
    if count:
        metrics["test_automatic_accuracy"] = float(correct[accepted].mean())

    routing_rows = []
    for label in model.classes_:
        routed = accepted & (predicted == label)
        true_class = actual == label
        routed_count = int(routed.sum())
        routing_rows.append({
            "category": label,
            "threshold": policy["thresholds"].get(label),
            "automatically_routed": routed_count,
            "routing_precision": float(correct[routed].mean())
                if routed_count else None,
            "true_class_count": int(true_class.sum()),
            "fraction_correctly_auto_routed": float(
                (true_class & accepted & correct).sum() / true_class.sum()
            ),
        })
    pd.DataFrame(routing_rows).to_csv(out / "team_routing.csv", index=False)
    pd.DataFrame({
        "complaint_id": data["complaint_id"],
        "actual": actual,
        "predicted": predicted,
        "confidence": confidence,
        "human_review": ~accepted,
    }).to_csv(out / "predictions.csv", index=False)

    (out / "classification_report.json").write_text(json.dumps(
        classification_report(
            actual, predicted, output_dict=True, zero_division=0
        ), indent=2
    ) + "\n")
    matrix = confusion_matrix(actual, predicted, labels=model.classes_)
    pd.DataFrame(
        matrix, index=model.classes_, columns=model.classes_
    ).to_csv(out / "confusion_matrix.csv")
    fig, ax = plt.subplots(figsize=(9, 7))
    ConfusionMatrixDisplay(matrix, display_labels=model.classes_).plot(
        ax=ax, xticks_rotation=35, colorbar=False
    )
    fig.tight_layout()
    fig.savefig(out / "confusion_matrix.png", dpi=140)
    plt.close(fig)

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("complaint-routing")
    with mlflow.start_run(run_name="frozen_october_test") as run:
        mlflow.set_tags({
            "git_commit": commit,
            "training_run_id": policy["training_run_id"],
            "policy_sha256": sha256(policy_path),
            "test_sha256": sha256(test_path),
        })
        mlflow.log_metrics(metrics)
        summary = {
            "model_name": policy["model_name"],
            "thresholds": policy["thresholds"],
            "metrics": metrics,
            "test_rows": len(data),
            "git_commit": commit,
            "training_run_id": policy["training_run_id"],
            "evaluation_run_id": run.info.run_id,
            "policy_sha256": sha256(policy_path),
            "test_sha256": sha256(test_path),
            "model_probability_checks": "PASS",
            "thresholds_changed_using_test": False,
        }
        (out / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n"
        )
        mlflow.log_artifacts(str(out), artifact_path="october_test")

    logging.info("Evaluation complete:\n%s", json.dumps(summary, indent=2))
    logging.info("Saved results: %s", out)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Evaluation FAILED")
        raise

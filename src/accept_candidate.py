"""Compare champion and candidate on the frozen acceptance period.

Save a selection decision without modifying the serving bundle.
December is reserved for subsequent final evaluation.
"""
import json
import logging
import subprocess
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score

from backend.model_loader import load_bundle
from src.monitor_lifecycle import file_hash, score
from src.select_threshold import routing_mask

ROOT = Path(__file__).resolve().parents[1]


def acceptance_checks(champion, candidate, settings):
    """Require every frozen performance and routing guardrail to pass."""
    ca = candidate.get("automatic_accuracy")
    ch = champion.get("automatic_accuracy")
    return {
        "macro_f1_improves": bool(
            candidate["macro_f1"] - champion["macro_f1"]
            >= settings["minimum_macro_f1_improvement"] - 1e-12
        ),
        "per_class_recall_preserved": bool(all(
            candidate["recall"][label] >= value
            - settings["maximum_per_class_recall_drop"] - 1e-12
            for label, value in champion["recall"].items()
        )),
        "sufficient_automatic_predictions": bool(
            candidate["automatic_count"] >= settings["minimum_automatic_count"]
        ),
        "automatic_accuracy_floor": bool(
            ca is not None and ca >= settings["minimum_automatic_accuracy"]
        ),
        "automatic_accuracy_preserved": bool(
            ca is not None and ch is not None
            and ca >= ch - settings["maximum_automatic_accuracy_drop"] - 1e-12
        ),
        "automatic_coverage_preserved": bool(
            candidate["automatic_coverage"] >= champion["automatic_coverage"]
            - settings["maximum_automatic_coverage_drop"] - 1e-12
        ),
    }


def evaluate(model, policy, frame, output):
    """Evaluate classification and actual serving-equivalent routing."""
    predicted, confidence, unrecognized = score(model, frame)
    classes = [str(label) for label in model.classes_]
    actual = frame["label"].to_numpy()
    accepted = routing_mask(predicted, confidence, policy["thresholds"])
    accepted &= ~unrecognized
    count = int(accepted.sum())
    recalls = recall_score(
        actual, predicted, labels=classes, average=None, zero_division=0
    )
    metrics = {
        "macro_f1": float(f1_score(
            actual, predicted, labels=classes, average="macro", zero_division=0
        )),
        "accuracy": float(accuracy_score(actual, predicted)),
        "automatic_count": count,
        "automatic_coverage": float(accepted.mean()),
        "automatic_accuracy": (
            float(accuracy_score(actual[accepted], predicted[accepted]))
            if count else None
        ),
        "recall": dict(zip(classes, map(float, recalls))),
    }
    pd.DataFrame({
        "complaint_id": frame["complaint_id"].to_numpy(),
        "actual": actual,
        "predicted": predicted,
        "confidence": confidence,
        "human_review": ~accepted,
    }).to_csv(output, index=False)
    return metrics


def main():
    out = ROOT / "reports/lifecycle/acceptance"
    out.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs/candidate_acceptance.log", mode="w"),
        ],
    )
    config_path = ROOT / "config/lifecycle.json"
    summary_path = ROOT / "reports/lifecycle/candidate/training_summary.json"
    config = json.loads(config_path.read_text())
    summary = json.loads(summary_path.read_text())
    if summary["status"] != "PASS":
        raise ValueError("Successful candidate training is required")
    if not config["acceptance"]["require_all_checks"]:
        raise ValueError("All acceptance checks must be required")
    if config["acceptance"]["on_failure"] != "retain_champion":
        raise ValueError("Expected retain-champion failure policy")

    paths = {
        "config_sha256": config_path,
        "original_train_sha256": ROOT / "data/processed/train.csv",
        "future_source_sha256": ROOT / "data/processed/future.csv",
        "parent_serving_manifest_sha256":
            ROOT / "artifacts/serving/manifest.json",
    }
    for key, path in paths.items():
        if file_hash(path) != summary["provenance"][key]:
            raise ValueError(f"Input changed since candidate training: {path}")

    model_path = ROOT / "artifacts/lifecycle/candidate/model.joblib"
    policy_path = ROOT / "artifacts/lifecycle/candidate/policy.json"
    if file_hash(model_path) != summary["candidate_model_sha256"]:
        raise ValueError("Candidate model hash mismatch")
    if file_hash(policy_path) != summary["candidate_policy_sha256"]:
        raise ValueError("Candidate policy hash mismatch")

    champion, champion_policy = load_bundle(ROOT / "artifacts/serving")
    candidate = joblib.load(model_path)
    candidate_policy = json.loads(policy_path.read_text())
    if champion_policy["training_run_id"] != config["champion_training_run_id"]:
        raise ValueError("Unexpected champion")
    if candidate_policy["training_run_id"] != summary["candidate_run_id"]:
        raise ValueError("Candidate run identity mismatch")
    if candidate_policy["model_sha256"] != file_hash(model_path):
        raise ValueError("Candidate policy/model mismatch")
    if not np.array_equal(champion.classes_, candidate.classes_):
        raise ValueError("Model class order differs")

    future = pd.read_csv(
        ROOT / "data/processed/future.csv", dtype=str, keep_default_na=False
    )
    start, end = config["periods"]["candidate_acceptance"]
    batch = future[future["date_received"].between(start, end)].copy()
    train_start, _ = config["periods"]["monitor_and_candidate_train"]
    _, tune_end = config["periods"]["candidate_threshold_selection"]
    development = future[
        future["date_received"].between(train_start, tune_end)
    ].copy()
    original = pd.read_csv(
        ROOT / "data/processed/train.csv", dtype=str, keep_default_na=False
    )
    development = pd.concat([original, development], ignore_index=True)
    if batch.empty or set(batch["label"]) != set(champion.classes_):
        raise ValueError("Acceptance batch must contain all supported classes")
    if not batch["complaint_id"].is_unique:
        raise ValueError("Repeated acceptance IDs")
    if development["date_received"].max() >= batch["date_received"].min():
        raise ValueError("Development dates overlap acceptance")
    if set(batch["complaint_id"]) & set(development["complaint_id"]):
        raise ValueError("Development/acceptance IDs overlap")

    def normalize(series):
        return series.map(lambda value: " ".join(value.split()).lower())

    if set(normalize(batch["text"])) & set(normalize(development["text"])):
        raise ValueError("Development/acceptance normalized text overlaps")
    del future, original, development

    logging.info("Comparing both models on %s acceptance complaints", len(batch))
    champion_metrics = evaluate(
        champion, champion_policy, batch, out / "champion_predictions.csv"
    )
    candidate_metrics = evaluate(
        candidate, candidate_policy, batch, out / "candidate_predictions.csv"
    )
    checks = acceptance_checks(
        champion_metrics, candidate_metrics, config["acceptance"]
    )
    approved = all(checks.values())
    decision = "candidate_accepted" if approved else "champion_retained"
    selected_run = (
        candidate_policy["training_run_id"] if approved
        else champion_policy["training_run_id"]
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("complaint-routing-lifecycle")
    with mlflow.start_run(run_name="november_candidate_acceptance") as run:
        mlflow.set_tags({
            "git_commit": commit,
            "config_sha256": file_hash(config_path),
            "candidate_training_summary_sha256": file_hash(summary_path),
            "champion_run_id": champion_policy["training_run_id"],
            "candidate_run_id": candidate_policy["training_run_id"],
            "decision": decision,
        })
        mlflow.log_params({
            "period_start": start,
            "period_end": end,
            "acceptance_rows": len(batch),
            **config["acceptance"],
        })
        for name, metrics in (
            ("champion", champion_metrics), ("candidate", candidate_metrics)
        ):
            mlflow.log_metrics({
                f"{name}_{key}": value for key, value in metrics.items()
                if key != "recall" and value is not None
            })
            mlflow.log_metrics({
                f"{name}_recall_{label}": value
                for label, value in metrics["recall"].items()
            })
        mlflow.log_metrics({
            f"check_{name}": int(passed) for name, passed in checks.items()
        })
        report = {
            "status": "PASS",
            "period": [start, end],
            "acceptance_rows": len(batch),
            "champion": champion_metrics,
            "candidate": candidate_metrics,
            "checks": checks,
            "decision": decision,
            "selected_run_id": selected_run,
            "champion_run_id": champion_policy["training_run_id"],
            "candidate_run_id": candidate_policy["training_run_id"],
            "acceptance_run_id": run.info.run_id,
            "config_sha256": file_hash(config_path),
            "candidate_training_summary_sha256": file_hash(summary_path),
            "future_source_sha256":
                summary["provenance"]["future_source_sha256"],
            "git_commit": commit,
            "serving_model_replaced": False,
            "december_evaluated": False,
            "note": "Selection decision only; serving deployment is a separate step.",
        }
        (out / "decision.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )
        mlflow.log_artifacts(str(out), artifact_path="acceptance")
    if file_hash(paths["parent_serving_manifest_sha256"]) != (
        summary["provenance"]["parent_serving_manifest_sha256"]
    ):
        raise RuntimeError("Serving manifest unexpectedly changed")
    logging.info("Acceptance complete:\n%s", json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Candidate acceptance FAILED")
        raise

"""Train an isolated candidate following the frozen chronological policy.

Automatic mode requires a monitoring trigger. --demonstration explicitly
allows a retraining rehearsal when no trigger occurred. Neither mode
replaces the serving model or evaluates the acceptance/December periods.
"""
import argparse
import json
import logging
import subprocess
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.base import clone
from sklearn.metrics import accuracy_score, f1_score
from threadpoolctl import threadpool_limits

from backend.model_loader import load_bundle
from src.monitor_lifecycle import file_hash, score
from src.select_threshold import routing_mask, team_thresholds

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--demonstration", action="store_true",
        help="Explicit rehearsal; does not claim monitoring triggered retraining",
    )
    args = parser.parse_args()

    output = ROOT / "reports/lifecycle/candidate"
    artifacts = ROOT / "artifacts/lifecycle/candidate"
    for directory in (output, artifacts, ROOT / "logs"):
        directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs/candidate_training.log", mode="w"),
        ],
    )

    config_path = ROOT / "config/lifecycle.json"
    monitoring_path = ROOT / "reports/lifecycle/monitoring.json"
    config = json.loads(config_path.read_text())
    monitoring = json.loads(monitoring_path.read_text())
    if monitoring["status"] != "PASS":
        raise ValueError("A successful monitoring report is required")
    if monitoring["provenance"]["config_sha256"] != file_hash(config_path):
        raise ValueError("Configuration changed since monitoring")

    triggered = monitoring["retraining_required"]
    if not triggered and not args.demonstration:
        logging.info("No retraining trigger: champion retained; no candidate trained.")
        return
    reason = "monitoring_trigger" if triggered else "explicit_demonstration"
    logging.info("Candidate training reason: %s", reason)

    changed = subprocess.check_output(
        ["git", "diff", "HEAD", "--",
         "src/retrain_candidate.py", "src/monitor_lifecycle.py",
         "src/select_threshold.py", "backend/model_loader.py",
         "config/lifecycle.json", "requirements.lock.txt"],
        cwd=ROOT, text=True,
    )
    if changed:
        raise RuntimeError("Commit lifecycle code/configuration before training")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()

    manifest_path = ROOT / "artifacts/serving/manifest.json"
    if file_hash(manifest_path) != monitoring["provenance"]["serving_manifest_sha256"]:
        raise ValueError("Serving bundle changed since monitoring")
    champion, champion_policy = load_bundle(ROOT / "artifacts/serving")
    if champion_policy["training_run_id"] != config["champion_training_run_id"]:
        raise ValueError("Unexpected champion identity")
    if config["candidate"]["model_type"] != "linear_svc_calibrated":
        raise ValueError("Unsupported candidate model type")

    train_path = ROOT / "data/processed/train.csv"
    future_path = ROOT / "data/processed/future.csv"
    for path, key in (
        (train_path, "reference_source_sha256"),
        (future_path, "future_source_sha256"),
    ):
        if file_hash(path) != monitoring["provenance"][key]:
            raise ValueError(f"Input changed since monitoring: {path.name}")

    original = pd.read_csv(train_path, dtype=str, keep_default_na=False)
    future = pd.read_csv(future_path, dtype=str, keep_default_na=False)
    train_start, train_end = config["periods"]["monitor_and_candidate_train"]
    tune_start, tune_end = config["periods"]["candidate_threshold_selection"]
    incoming = future[future["date_received"].between(train_start, train_end)].copy()
    tune = future[future["date_received"].between(tune_start, tune_end)].copy()
    del future
    train = pd.concat([original, incoming], ignore_index=True)
    classes = [str(label) for label in champion.classes_]

    for name, frame in (("candidate_train", train), ("threshold_selection", tune)):
        if frame.empty or set(frame["label"]) != set(classes):
            raise ValueError(f"{name} must contain every supported category")
        if not frame["complaint_id"].is_unique:
            raise ValueError(f"{name} contains repeated complaint IDs")
        normalized = frame["text"].map(lambda value: " ".join(value.split()).lower())
        if normalized.duplicated().any():
            raise ValueError(f"{name} contains repeated normalized text")

    if set(train["complaint_id"]) & set(tune["complaint_id"]):
        raise ValueError("Training and threshold-selection IDs overlap")
    train_text = train["text"].map(lambda value: " ".join(value.split()))
    tune_text = tune["text"].map(lambda value: " ".join(value.split()))
    if set(train_text.str.lower()) & set(tune_text.str.lower()):
        raise ValueError("Training and threshold-selection text overlaps")
    if train["date_received"].max() >= tune["date_received"].min():
        raise ValueError("Training must precede threshold selection")

    candidate = clone(champion)
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("complaint-routing-lifecycle")

    provenance = {
        "git_commit": commit,
        "config_sha256": file_hash(config_path),
        "monitoring_report_sha256": file_hash(monitoring_path),
        "original_train_sha256": file_hash(train_path),
        "future_source_sha256": file_hash(future_path),
        "parent_champion_run_id": champion_policy["training_run_id"],
        "parent_serving_manifest_sha256": file_hash(manifest_path),
        "training_reason": reason,
    }
    with mlflow.start_run(run_name="november_candidate_training") as run:
        mlflow.set_tags(provenance)
        mlflow.log_params({
            "model_type": config["candidate"]["model_type"],
            "candidate_train_rows": len(train),
            "incoming_train_rows": len(incoming),
            "threshold_selection_rows": len(tune),
            "incoming_train_start": train_start,
            "incoming_train_end": train_end,
            "threshold_selection_start": tune_start,
            "threshold_selection_end": tune_end,
            "parameters_inherited_from_champion": True,
            "tfidf_max_features": candidate.named_steps["tfidf"].max_features,
            "routing_precision_target":
                config["candidate"]["routing_precision_target"],
            "minimum_threshold_count":
                config["candidate"]["minimum_threshold_selection_count_per_category"],
        })

        logging.info("Fitting candidate on %s rows; threshold selection uses %s rows",
                     len(train), len(tune))
        with threadpool_limits(limits=2):
            candidate.fit(train_text, train["label"])
        if set(candidate.classes_) != set(classes):
            raise ValueError("Candidate categories differ from champion")

        predicted, confidence, unrecognized = score(candidate, tune)
        predictions = pd.DataFrame({
            "complaint_id": tune["complaint_id"].to_numpy(),
            "actual": tune["label"].to_numpy(),
            "predicted": predicted,
            "confidence": confidence,
        })
        thresholds, curves = team_thresholds(
            predictions,
            target_accuracy=config["candidate"]["routing_precision_target"],
            min_auto=config["candidate"]["minimum_threshold_selection_count_per_category"],
        )
        thresholds = {label: thresholds.get(label) for label in classes}
        accepted = routing_mask(predicted, confidence, thresholds)
        accepted &= ~unrecognized
        actual = tune["label"].to_numpy()
        count = int(accepted.sum())
        metrics = {
            "threshold_selection_macro_f1": float(f1_score(
                actual, predicted, labels=classes,
                average="macro", zero_division=0,
            )),
            "threshold_selection_accuracy": float(accuracy_score(actual, predicted)),
            "threshold_selection_automatic_count": count,
            "threshold_selection_automatic_coverage": float(accepted.mean()),
        }
        if count:
            metrics["threshold_selection_automatic_accuracy"] = float(
                accuracy_score(actual[accepted], predicted[accepted])
            )

        prediction_path = output / "threshold_predictions.csv"
        predictions.to_csv(prediction_path, index=False)
        curves.to_csv(output / "threshold_curve.csv", index=False)
        model_path = artifacts / "model.joblib"
        joblib.dump(candidate, model_path)

        policy = {
            "policy_version": 2,
            "mode": "per_predicted_category",
            "thresholds": thresholds,
            "default_action": "human_review",
            "model_name": "linear_svc_calibrated",
            "training_run_id": run.info.run_id,
            "model_sha256": file_hash(model_path),
            "validation_predictions_sha256": file_hash(prediction_path),
            "target_validation_routing_precision":
                config["candidate"]["routing_precision_target"],
            "minimum_validation_automatic_count_per_category":
                config["candidate"]["minimum_threshold_selection_count_per_category"],
            "validation_rows": len(tune),
            "test_set_used": False,
            "parent_training_run_id": champion_policy["training_run_id"],
        }
        (artifacts / "policy.json").write_text(
            json.dumps(policy, indent=2, allow_nan=False) + "\n"
        )

        example = np.array(["My credit card was charged twice."])
        signature = infer_signature(example, candidate.predict(example))
        model_info = mlflow.sklearn.log_model(
            candidate, name="candidate_model",
            signature=signature, input_example=example,
            pip_requirements=str(ROOT / "requirements.lock.txt"),
        )
        restored = mlflow.sklearn.load_model(model_info.model_uri)
        if not np.allclose(
            restored.predict_proba(example),
            candidate.predict_proba(example),
            rtol=1e-7, atol=1e-9,
        ):
            raise ValueError("MLflow candidate reload equivalence failed")

        summary = {
            "status": "PASS",
            "training_reason": reason,
            "automatic_trigger_occurred": bool(triggered),
            "monitoring_trigger_reasons": monitoring["trigger_reasons"],
            "candidate_run_id": run.info.run_id,
            "candidate_model_uri": model_info.model_uri,
            "training_rows": len(train),
            "new_training_rows": len(incoming),
            "threshold_selection_rows": len(tune),
            "thresholds": thresholds,
            "metrics": metrics,
            "model_reload_check": "PASS",
            "candidate_model_sha256": file_hash(model_path),
            "candidate_policy_sha256": file_hash(artifacts / "policy.json"),
            "provenance": provenance,
            "acceptance_period_evaluated": False,
            "december_evaluated": False,
            "serving_model_replaced": False,
        }
        summary_path = output / "training_summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, allow_nan=False) + "\n"
        )
        mlflow.log_metrics(metrics)
        mlflow.log_artifacts(str(output), artifact_path="candidate_reports")
        mlflow.log_artifact(str(artifacts / "policy.json"), artifact_path="policy")

    if file_hash(manifest_path) != provenance["parent_serving_manifest_sha256"]:
        raise RuntimeError("Serving manifest unexpectedly changed")
    logging.info("Candidate training complete:\n%s", json.dumps(summary, indent=2))
    logging.info("Champion retained. Candidate acceptance is the next step.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Candidate training FAILED")
        raise

"""Evaluate the selected, deployed model on the reserved December period.

No training, threshold adjustment or model selection occurs here.
"""
import json
import logging
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import pandas as pd
import requests
from sklearn.metrics import (
    classification_report, confusion_matrix, ConfusionMatrixDisplay,
)

from backend.model_loader import load_bundle
from src.accept_candidate import evaluate
from src.monitor_lifecycle import file_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "reports/lifecycle/final"
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.json"
    if summary_path.exists():
        raise FileExistsError(
            "Final evaluation already exists. Preserve it; do not tune against December."
        )
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs/lifecycle_final_evaluation.log", mode="w"),
        ],
    )
    config_path = ROOT / "config/lifecycle.json"
    decision_path = ROOT / "reports/lifecycle/acceptance/decision.json"
    packaging_path = ROOT / "reports/lifecycle/candidate_packaging.json"
    deployment_path = ROOT / "reports/lifecycle/deployment_verification.json"
    training_path = ROOT / "reports/lifecycle/candidate/training_summary.json"

    config = json.loads(config_path.read_text())
    decision = json.loads(decision_path.read_text())
    packaging = json.loads(packaging_path.read_text())
    deployment = json.loads(deployment_path.read_text())
    training = json.loads(training_path.read_text())

    if decision["decision"] != "candidate_accepted":
        raise ValueError("Expected the previously accepted candidate")
    if packaging["status"] != "PASS" or deployment["status"] != "PASS":
        raise ValueError("Packaging and deployment verification must pass")
    if file_hash(config_path) != decision["config_sha256"]:
        raise ValueError("Frozen configuration changed")
    if file_hash(decision_path) != packaging["acceptance_decision_sha256"]:
        raise ValueError("Acceptance decision changed")
    if file_hash(packaging_path) != deployment["packaging_report_sha256"]:
        raise ValueError("Packaging report changed")
    if file_hash(training_path) != decision["candidate_training_summary_sha256"]:
        raise ValueError("Candidate training summary changed")

    bundle = ROOT / packaging["bundle"]
    if file_hash(bundle / "manifest.json") != packaging["bundle_manifest_sha256"]:
        raise ValueError("Selected bundle changed")
    model, policy = load_bundle(bundle)
    version = policy["training_run_id"]
    if not (
        version == decision["selected_run_id"]
        == deployment["active_model_version"]
    ):
        raise ValueError("Selected/deployed model identities differ")

    response = requests.get("http://127.0.0.1:8000/healthz", timeout=15)
    response.raise_for_status()
    if response.json().get("model_version") != version:
        raise ValueError("Live backend is not serving the selected model")

    future_path = ROOT / "data/processed/future.csv"
    train_path = ROOT / "data/processed/train.csv"
    if file_hash(future_path) != decision["future_source_sha256"]:
        raise ValueError("Future dataset changed")
    if file_hash(train_path) != training["provenance"]["original_train_sha256"]:
        raise ValueError("Original training data changed")

    future = pd.read_csv(future_path, dtype=str, keep_default_na=False)
    start, end = config["periods"]["final_evaluation"]
    final = future[future["date_received"].between(start, end)].copy()
    earlier = future[future["date_received"] < start].copy()
    original = pd.read_csv(train_path, dtype=str, keep_default_na=False)
    development = pd.concat([original, earlier], ignore_index=True)

    if final.empty or set(final["label"]) != set(model.classes_):
        raise ValueError("Final period must contain all supported classes")
    if not final["complaint_id"].is_unique:
        raise ValueError("Repeated final-evaluation IDs")
    if development["date_received"].max() >= final["date_received"].min():
        raise ValueError("Development/final dates overlap")
    if set(final["complaint_id"]) & set(development["complaint_id"]):
        raise ValueError("Development/final IDs overlap")

    def normalized(series):
        return series.map(lambda value: " ".join(value.split()).lower())

    if set(normalized(final["text"])) & set(normalized(development["text"])):
        raise ValueError("Development/final normalized text overlaps")
    del future, earlier, original, development

    logging.info("Evaluating frozen selected model on %s December complaints",
                 len(final))
    metrics = evaluate(
        model, policy, final, out / "predictions.csv"
    )
    predictions = pd.read_csv(out / "predictions.csv")
    labels = list(model.classes_)
    matrix = confusion_matrix(
        predictions["actual"], predictions["predicted"], labels=labels
    )
    pd.DataFrame(matrix, index=labels, columns=labels).to_csv(
        out / "confusion_matrix.csv"
    )
    (out / "classification_report.json").write_text(json.dumps(
        classification_report(
            predictions["actual"], predictions["predicted"],
            labels=labels, output_dict=True, zero_division=0,
        ), indent=2, allow_nan=False
    ) + "\n")
    fig, ax = plt.subplots(figsize=(9, 7))
    ConfusionMatrixDisplay(matrix, display_labels=labels).plot(
        ax=ax, xticks_rotation=35, colorbar=False
    )
    fig.tight_layout()
    fig.savefig(out / "confusion_matrix.png", dpi=140)
    plt.close(fig)

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("complaint-routing-lifecycle")
    with mlflow.start_run(run_name="selected_model_december_final") as run:
        provenance = {
            "git_commit": commit,
            "config_sha256": file_hash(config_path),
            "acceptance_decision_sha256": file_hash(decision_path),
            "deployment_report_sha256": file_hash(deployment_path),
            "bundle_manifest_sha256": file_hash(bundle / "manifest.json"),
            "future_source_sha256": file_hash(future_path),
            "selected_training_run_id": version,
        }
        mlflow.set_tags(provenance)
        mlflow.log_params({
            "period_start": start,
            "period_end": end,
            "final_rows": len(final),
            "model_and_thresholds_frozen": True,
        })
        mlflow.log_metrics({
            key: value for key, value in metrics.items()
            if key != "recall" and value is not None
        })
        mlflow.log_metrics({
            f"recall_{label}": value
            for label, value in metrics["recall"].items()
        })
        report = {
            "status": "PASS",
            "period": [start, end],
            "final_rows": len(final),
            "selected_training_run_id": version,
            "evaluation_run_id": run.info.run_id,
            "thresholds": policy["thresholds"],
            "metrics": metrics,
            "provenance": provenance,
            "model_changed_using_final_data": False,
            "thresholds_changed_using_final_data": False,
            "note": (
                "PASS means evaluation completed and integrity checks passed; "
                "it does not mean a performance target was guaranteed."
            ),
        }
        summary_path.write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )
        mlflow.log_artifacts(str(out), artifact_path="december_final")
    logging.info("Final evaluation complete:\n%s", json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Final lifecycle evaluation FAILED")
        raise

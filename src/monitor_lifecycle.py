"""Monitor a historical incoming batch against a training-only reference.

Text-length and predicted-product distributions are limited drift proxies.
Labeled macro-F1 measures batch performance separately. Distribution shift
alone does not establish degraded accuracy. This script never trains or
replaces a model.
"""
import hashlib
import json
import logging
import subprocess
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from threadpoolctl import threadpool_limits

from backend.model_loader import load_bundle
from src.select_threshold import routing_mask

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def js_divergence(left, right):
    """Base-2 Jensen-Shannon divergence: zero means identical distributions."""
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    if (
        left.ndim != 1 or left.shape != right.shape
        or not np.isfinite(left).all() or not np.isfinite(right).all()
        or (left < 0).any() or (right < 0).any()
        or left.sum() <= 0 or right.sum() <= 0
    ):
        raise ValueError("Expected matching nonnegative, nonempty counts")
    left = left / left.sum()
    right = right / right.sum()
    midpoint = (left + right) / 2

    def relative_entropy(values):
        mask = values > 0
        return np.sum(values[mask] * np.log2(values[mask] / midpoint[mask]))

    return float(np.clip(
        (relative_entropy(left) + relative_entropy(right)) / 2, 0, 1
    ))


def trigger_reasons(length_jsd, product_jsd, macro_f1, settings):
    """Apply the committed trigger thresholds without adjusting them."""
    reasons = []
    limit = settings["js_divergence_threshold"]
    if length_jsd > limit:
        reasons.append("text_length_distribution_shift")
    if product_jsd > limit:
        reasons.append("predicted_product_distribution_shift")
    if macro_f1 < settings["labeled_macro_f1_floor"]:
        reasons.append("labeled_macro_f1_below_floor")
    return reasons


def score(model, frame):
    """Match serving whitespace normalization and validate probabilities."""
    texts = frame["text"].map(lambda value: " ".join(value.split()))
    with threadpool_limits(limits=2):
        features = model.named_steps["tfidf"].transform(texts)
        probabilities = model.named_steps["classifier"].predict_proba(features)
    if (
        probabilities.shape != (len(frame), len(model.classes_))
        or not np.isfinite(probabilities).all()
        or ((probabilities < 0) | (probabilities > 1)).any()
        or not np.allclose(probabilities.sum(axis=1), 1, atol=1e-5)
    ):
        raise ValueError("Invalid probability output")
    return (
        model.classes_[probabilities.argmax(axis=1)],
        probabilities.max(axis=1),
        np.asarray(features.getnnz(axis=1)) == 0,
    )


def distributions(frame, predictions, classes, bins):
    """Return aggregate counts without retaining complaint narratives."""
    lengths = frame["text"].map(lambda value: len(" ".join(value.split())))
    return {
        "text_length_counts": np.histogram(lengths, bins=bins)[0].tolist(),
        "predicted_product_counts": [
            int(np.sum(predictions == label)) for label in classes
        ],
    }


def main():
    report_dir = ROOT / "reports/lifecycle"
    artifact_dir = ROOT / "artifacts/lifecycle"
    for directory in (report_dir, artifact_dir, ROOT / "logs"):
        directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs/lifecycle_monitoring.log", mode="w"),
        ],
    )
    config_path = ROOT / "config/lifecycle.json"
    config = json.loads(config_path.read_text())
    settings = config["monitoring"]
    if settings["js_divergence_base"] != 2:
        raise ValueError("This implementation requires base-2 divergence")

    model, policy = load_bundle(ROOT / "artifacts/serving")
    if policy["training_run_id"] != config["champion_training_run_id"]:
        raise ValueError("Serving model differs from the frozen champion")

    reference_path = ROOT / settings["reference_source"]
    future_path = ROOT / "data/processed/future.csv"
    reference = pd.read_csv(
        reference_path, dtype=str, keep_default_na=False
    )
    future = pd.read_csv(future_path, dtype=str, keep_default_na=False)
    start, end = config["periods"]["monitor_and_candidate_train"]
    batch = future[future["date_received"].between(start, end)].copy()
    del future

    classes = [str(label) for label in model.classes_]
    if len(batch) < settings["minimum_batch_rows"]:
        raise ValueError("Insufficient monitoring batch")
    if set(batch["label"]) != set(classes):
        raise ValueError("Monitoring batch must contain all supported classes")
    if not batch["complaint_id"].is_unique:
        raise ValueError("Duplicate monitoring complaint IDs")
    if set(reference["complaint_id"]) & set(batch["complaint_id"]):
        raise ValueError("Training and monitoring complaint IDs overlap")

    reference = reference.sample(
        n=min(len(reference), settings["reference_sample_limit"]),
        random_state=config["seed"],
    ).reset_index(drop=True)
    batch = batch.reset_index(drop=True)
    logging.info("Scoring %s reference and %s November monitoring rows",
                 len(reference), len(batch))

    reference_predictions, _, _ = score(model, reference)
    predicted, confidence, unrecognized = score(model, batch)
    sampled_indices = batch.sample(
        n=min(len(batch), settings["batch_sample_limit"]),
        random_state=config["seed"],
    ).index.to_numpy()

    edges = settings["text_length_bins"]
    if not edges or edges[0] != 0 or any(
        left >= right for left, right in zip(edges, edges[1:])
    ):
        raise ValueError("Text-length bins must increase from zero")
    bins = np.asarray([*edges, np.inf], dtype=float)
    reference_distribution = distributions(
        reference, reference_predictions, classes, bins
    )
    batch_distribution = distributions(
        batch.iloc[sampled_indices], predicted[sampled_indices], classes, bins
    )

    length_jsd = js_divergence(
        reference_distribution["text_length_counts"],
        batch_distribution["text_length_counts"],
    )
    product_jsd = js_divergence(
        reference_distribution["predicted_product_counts"],
        batch_distribution["predicted_product_counts"],
    )
    actual = batch["label"].to_numpy()
    macro_f1 = float(f1_score(
        actual, predicted, labels=classes, average="macro", zero_division=0
    ))
    accepted = routing_mask(predicted, confidence, policy["thresholds"])
    accepted &= ~unrecognized
    automatic_count = int(accepted.sum())
    metrics = {
        "text_length_jsd": length_jsd,
        "predicted_product_jsd": product_jsd,
        "labeled_macro_f1": macro_f1,
        "labeled_accuracy": float(accuracy_score(actual, predicted)),
        "automatic_coverage": float(accepted.mean()),
        "automatic_count": automatic_count,
        "unrecognized_fraction": float(unrecognized.mean()),
    }
    if automatic_count:
        metrics["automatic_accuracy"] = float(
            accuracy_score(actual[accepted], predicted[accepted])
        )
    reasons = trigger_reasons(length_jsd, product_jsd, macro_f1, settings)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    provenance = {
        "git_commit": commit,
        "config_sha256": file_hash(config_path),
        "reference_source_sha256": file_hash(reference_path),
        "future_source_sha256": file_hash(future_path),
        "serving_manifest_sha256": file_hash(
            ROOT / "artifacts/serving/manifest.json"
        ),
        "champion_training_run_id": policy["training_run_id"],
    }
    reference_record = {
        "classes": classes,
        "text_length_bin_lower_edges": edges,
        "last_bin_upper_edge": "infinity",
        "rows": len(reference),
        "seed": config["seed"],
        "counts": reference_distribution,
        "provenance": provenance,
    }
    reference_output = artifact_dir / "drift_reference.json"
    reference_output.write_text(
        json.dumps(reference_record, indent=2, allow_nan=False) + "\n"
    )

    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("complaint-routing-lifecycle")
    with mlflow.start_run(run_name="champion_november_monitoring") as run:
        mlflow.set_tags(provenance)
        mlflow.log_params({
            "period_start": start,
            "period_end": end,
            "reference_rows": len(reference),
            "monitoring_rows": len(batch),
            "drift_batch_sample_rows": len(sampled_indices),
            "js_divergence_threshold": settings["js_divergence_threshold"],
            "macro_f1_floor": settings["labeled_macro_f1_floor"],
        })
        mlflow.log_metrics(metrics)
        mlflow.log_metric("retraining_required", int(bool(reasons)))
        report = {
            "status": "PASS",
            "period": [start, end],
            "monitoring_rows": len(batch),
            "reference_rows": len(reference),
            "drift_batch_sample_rows": len(sampled_indices),
            "metrics": metrics,
            "batch_distribution": batch_distribution,
            "retraining_required": bool(reasons),
            "trigger_reasons": reasons,
            "monitoring_run_id": run.info.run_id,
            "provenance": provenance,
            "model_replaced": False,
            "december_evaluated": False,
            "limitations": (
                "Distribution proxies do not detect every semantic shift. "
                "Performance uses historical labels assumed available after arrival. "
                "Thresholds are demonstration settings, not production calibration."
            ),
        }
        output = report_dir / "monitoring.json"
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        mlflow.log_artifact(str(reference_output), artifact_path="reference")
        mlflow.log_artifact(str(output), artifact_path="monitoring")
    logging.info("Monitoring complete:\n%s", json.dumps(report, indent=2))
    logging.info("Saved report: %s", output)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Lifecycle monitoring FAILED")
        raise

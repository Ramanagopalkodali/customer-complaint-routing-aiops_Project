"""Compare two text classifiers using training and validation data only.

Save models, validation predictions, reports and MLflow records.
The October test set and future batches are never read by this script.
"""
import hashlib
import json
import logging
import subprocess
import time
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.calibration import CalibratedClassifierCV
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay, accuracy_score, classification_report,
    confusion_matrix, f1_score, log_loss,
)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
SEED = 42


def file_hash(path):
    """Hash data bytes to connect an experiment to its exact inputs."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    """Train sequentially, save validation evidence and select by macro-F1."""
    out = ROOT / "reports" / "training"
    models_dir = ROOT / "artifacts" / "training"
    for directory in (out, models_dir, ROOT / "logs"):
        directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs" / "training.log", mode="w"),
        ],
    )
    warnings.filterwarnings("error", category=ConvergenceWarning)

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    changes = subprocess.check_output(
        ["git", "diff", "HEAD", "--", "src/train.py",
         "requirements.txt", "requirements.lock.txt", "dvc.yaml"],
        cwd=ROOT, text=True,
    )
    if changes:
        raise RuntimeError("Commit the training code and configuration first.")

    train_path = ROOT / "data" / "processed" / "train.csv"
    val_path = ROOT / "data" / "processed" / "validation.csv"
    train = pd.read_csv(train_path, dtype=str, keep_default_na=False)
    val = pd.read_csv(val_path, dtype=str, keep_default_na=False)
    logging.info("Loaded %s training and %s validation rows",
                 f"{len(train):,}", f"{len(val):,}")

    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("complaint-routing")
    mlflow.sklearn.autolog(
        log_models=False, log_datasets=False,
        log_post_training_metrics=False,
    )
    provenance = {
        "git_commit": commit,
        "train_sha256": file_hash(train_path),
        "validation_sha256": file_hash(val_path),
    }
    estimators = {
        "logistic_regression": LogisticRegression(
            C=1.0, class_weight="balanced", max_iter=1000,
            solver="lbfgs", random_state=SEED,
        ),
        "linear_svc_calibrated": CalibratedClassifierCV(
            estimator=LinearSVC(
                C=1.0, class_weight="balanced", dual="auto",
                max_iter=5000, random_state=SEED,
            ),
            method="sigmoid", cv=3, ensemble=False, n_jobs=1,
        ),
    }
    majority = train["label"].mode().iloc[0]
    baseline = np.repeat(majority, len(val))
    results = {}

    for name, estimator in estimators.items():
        logging.info("START training: %s", name)
        model_dir = out / name
        model_dir.mkdir(exist_ok=True)
        model = Pipeline([
            ("tfidf", TfidfVectorizer(
                max_features=40000, ngram_range=(1, 2),
                min_df=3, sublinear_tf=True, dtype=np.float32,
            )),
            ("classifier", estimator),
        ])

        with mlflow.start_run(run_name=name) as run:
            mlflow.set_tags(provenance)
            mlflow.log_params({
                "model_name": name,
                "seed": SEED,
                "training_rows": len(train),
                "validation_rows": len(val),
                "selection_metric": "validation_macro_f1",
                "calibration_data": "training folds only; SVC only",
            })
            started = time.perf_counter()
            with threadpool_limits(limits=2):
                model.fit(train["text"], train["label"])
                probabilities = model.predict_proba(val["text"])
            elapsed = time.perf_counter() - started

            if not np.isfinite(probabilities).all():
                raise ValueError("Non-finite predicted probabilities")
            if not np.allclose(probabilities.sum(axis=1), 1, atol=1e-5):
                raise ValueError("Predicted probabilities do not sum to one")
            predicted = model.classes_[probabilities.argmax(axis=1)]
            scores = {
                "validation_macro_f1": float(f1_score(
                    val["label"], predicted, average="macro"
                )),
                "validation_accuracy": float(accuracy_score(
                    val["label"], predicted
                )),
                "validation_log_loss": float(log_loss(
                    val["label"], probabilities, labels=model.classes_
                )),
                "majority_baseline_macro_f1": float(f1_score(
                    val["label"], baseline, average="macro", zero_division=0
                )),
                "majority_baseline_accuracy": float(accuracy_score(
                    val["label"], baseline
                )),
                "fit_and_validation_seconds": elapsed,
            }
            mlflow.log_metrics(scores)

            report = classification_report(
                val["label"], predicted, output_dict=True, zero_division=0
            )
            (model_dir / "classification_report.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            pd.DataFrame({
                "complaint_id": val["complaint_id"],
                "actual": val["label"],
                "predicted": predicted,
                "confidence": probabilities.max(axis=1),
            }).to_csv(model_dir / "validation_predictions.csv", index=False)

            matrix = confusion_matrix(
                val["label"], predicted, labels=model.classes_
            )
            pd.DataFrame(
                matrix, index=model.classes_, columns=model.classes_
            ).to_csv(model_dir / "confusion_matrix.csv")
            fig, ax = plt.subplots(figsize=(9, 7))
            ConfusionMatrixDisplay(
                matrix, display_labels=model.classes_
            ).plot(ax=ax, xticks_rotation=35, colorbar=False)
            fig.tight_layout()
            fig.savefig(model_dir / "confusion_matrix.png", dpi=140)
            plt.close(fig)
            mlflow.log_artifacts(str(model_dir), artifact_path="validation")

            joblib.dump(model, models_dir / f"{name}.joblib")
            example = np.array(["My credit card was charged twice."])
            signature = infer_signature(example, model.predict(example))
            info = mlflow.sklearn.log_model(
                model, name="model", signature=signature,
                input_example=example,
                pip_requirements=str(ROOT / "requirements.lock.txt"),
            )
            restored = mlflow.sklearn.load_model(info.model_uri)
            if not np.array_equal(
                restored.predict(example), model.predict(example)
            ):
                raise ValueError("MLflow model reload check failed")
            del restored

            results[name] = {
                **scores,
                "run_id": run.info.run_id,
                "model_uri": info.model_uri,
                "model_reload_check": "PASS",
            }
            logging.info("COMPLETE %s: macro-F1=%.4f accuracy=%.4f run=%s",
                         name, scores["validation_macro_f1"],
                         scores["validation_accuracy"], run.info.run_id)
        del model

    selected = max(
        results,
        key=lambda name: (
            results[name]["validation_macro_f1"],
            results[name]["validation_accuracy"],
            name,
        ),
    )
    summary = {
        "provenance": provenance,
        "results": results,
        "selected_model": selected,
        "selection_rule": "highest validation macro-F1; accuracy then name on ties",
        "test_set_used": False,
    }
    (out / "comparison.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    logging.info("PASS: selected %s using validation macro-F1", selected)
    logging.info("Results saved in %s", out)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Training FAILED")
        raise

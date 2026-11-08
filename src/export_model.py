"""Create a portable MLflow model and routing-policy bundle without retraining."""
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

import joblib
import mlflow.sklearn
import numpy as np
from mlflow.models import infer_signature

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    """Verify source identity, package it, and check prediction equivalence."""
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs/export_model.log", mode="w"),
        ],
    )
    policy_path = ROOT / "artifacts/policy.json"
    policy = json.loads(policy_path.read_text())
    source = ROOT / "artifacts/training" / f"{policy['model_name']}.joblib"
    if sha256(source) != policy["model_sha256"]:
        raise ValueError("Source model does not match the frozen policy")

    model = joblib.load(source)
    probes = np.array([
        "My credit card was charged twice for the same purchase.",
        "My mortgage payment was not credited to my loan account.",
        "The credit reporting company has not corrected my report.",
        "A debt collector is contacting me about a debt that is not mine.",
        "My bank has not returned money missing from my checking account.",
    ])
    destination = ROOT / "artifacts/serving"
    if destination.exists():
        raise FileExistsError(
            "Serving bundle already exists. Rebuild it through its DVC stage."
        )

    temporary = Path(tempfile.mkdtemp(
        prefix="serving_build_", dir=ROOT / "artifacts"
    ))
    try:
        logging.info("Packaging selected model: %s", policy["model_name"])
        mlflow.sklearn.save_model(
            model,
            path=str(temporary / "model"),
            signature=infer_signature(probes, model.predict(probes)),
            input_example=probes,
            pip_requirements=str(ROOT / "requirements.lock.txt"),
            metadata={"training_run_id": policy["training_run_id"]},
        )
        shutil.copy2(policy_path, temporary / "policy.json")
        restored = mlflow.sklearn.load_model(str(temporary / "model"))

        if not np.array_equal(model.classes_, restored.classes_):
            raise ValueError("Exported model classes changed")
        if not np.array_equal(model.predict(probes), restored.predict(probes)):
            raise ValueError("Exported model predictions changed")
        if not np.allclose(
            model.predict_proba(probes), restored.predict_proba(probes),
            rtol=1e-10, atol=1e-12,
        ):
            raise ValueError("Exported model probabilities changed")

        files = {
            str(path.relative_to(temporary)): sha256(path)
            for path in sorted(temporary.rglob("*")) if path.is_file()
        }
        manifest = {
            "training_run_id": policy["training_run_id"],
            "model_name": policy["model_name"],
            "source_model_sha256": policy["model_sha256"],
            "files": files,
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        temporary.replace(destination)
        report = {
            "status": "PASS",
            "bundle": "artifacts/serving",
            "model_name": policy["model_name"],
            "training_run_id": policy["training_run_id"],
            "source_model_sha256": policy["model_sha256"],
            "policy_sha256": sha256(policy_path),
            "class_check": "PASS",
            "prediction_equivalence": "PASS",
            "probability_equivalence": "PASS",
            "smoke_examples": len(probes),
            "retraining_performed": False,
        }
        (ROOT / "reports/export_model.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
        logging.info("Export successful:\n%s", json.dumps(report, indent=2))
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Model export FAILED")
        raise

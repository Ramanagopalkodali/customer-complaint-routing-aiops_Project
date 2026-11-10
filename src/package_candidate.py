"""Package an accepted candidate without changing the active serving model."""
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import joblib
import mlflow.sklearn
import numpy as np
from mlflow.models import infer_signature

from backend.model_loader import load_bundle
from src.accept_candidate import acceptance_checks
from src.monitor_lifecycle import file_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    report_dir = ROOT / "reports/lifecycle"
    report_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs/candidate_packaging.log", mode="w"),
        ],
    )
    config_path = ROOT / "config/lifecycle.json"
    decision_path = report_dir / "acceptance/decision.json"
    summary_path = report_dir / "candidate/training_summary.json"
    config = json.loads(config_path.read_text())
    decision = json.loads(decision_path.read_text())
    summary = json.loads(summary_path.read_text())

    if decision["status"] != "PASS" or summary["status"] != "PASS":
        raise ValueError("Successful training and acceptance reports required")
    if decision["config_sha256"] != file_hash(config_path):
        raise ValueError("Configuration changed since acceptance")
    if decision["candidate_training_summary_sha256"] != file_hash(summary_path):
        raise ValueError("Candidate training summary changed since acceptance")
    checks = acceptance_checks(
        decision["champion"], decision["candidate"], config["acceptance"]
    )
    if (
        decision["decision"] != "candidate_accepted"
        or checks != decision["checks"]
        or not all(checks.values())
    ):
        raise ValueError("Candidate does not pass the frozen acceptance gate")

    candidate_dir = ROOT / "artifacts/lifecycle/candidate"
    source = candidate_dir / "model.joblib"
    policy_path = candidate_dir / "policy.json"
    policy = json.loads(policy_path.read_text())
    run_id = policy["training_run_id"]
    if not (
        run_id == decision["selected_run_id"]
        == decision["candidate_run_id"] == summary["candidate_run_id"]
    ):
        raise ValueError("Selected candidate identity mismatch")
    if file_hash(source) != summary["candidate_model_sha256"]:
        raise ValueError("Candidate model changed")
    if file_hash(source) != policy["model_sha256"]:
        raise ValueError("Candidate policy/model mismatch")
    if file_hash(policy_path) != summary["candidate_policy_sha256"]:
        raise ValueError("Candidate policy changed")

    champion_manifest = ROOT / "artifacts/serving/manifest.json"
    champion_hash = file_hash(champion_manifest)
    if champion_hash != summary["provenance"]["parent_serving_manifest_sha256"]:
        raise ValueError("Original serving bundle changed")
    _, champion_policy = load_bundle(ROOT / "artifacts/serving")
    if champion_policy["training_run_id"] != decision["champion_run_id"]:
        raise ValueError("Original serving identity mismatch")

    destination = candidate_dir / "serving"
    if destination.exists():
        raise FileExistsError(
            "Candidate serving bundle already exists; do not overwrite it manually."
        )
    model = joblib.load(source)
    probes = np.array([
        "My credit card was charged twice for the same purchase.",
        "My mortgage payment was not credited to my loan account.",
        "The credit reporting company has not corrected my report.",
        "A debt collector is contacting me about a debt that is not mine.",
        "My bank has not returned money missing from my checking account.",
        "zzzzqxv zzzzqxv zzzzqxv",
    ])
    temporary = Path(tempfile.mkdtemp(
        prefix="serving_build_", dir=candidate_dir
    ))
    try:
        mlflow.sklearn.save_model(
            model,
            path=str(temporary / "model"),
            signature=infer_signature(probes, model.predict(probes)),
            input_example=probes,
            pip_requirements=str(ROOT / "requirements.lock.txt"),
            metadata={"training_run_id": run_id},
        )
        shutil.copy2(policy_path, temporary / "policy.json")
        manifest = {
            "training_run_id": run_id,
            "model_name": policy["model_name"],
            "source_model_sha256": policy["model_sha256"],
            "files": {
                str(path.relative_to(temporary)): file_hash(path)
                for path in sorted(temporary.rglob("*")) if path.is_file()
            },
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        restored, restored_policy = load_bundle(temporary)
        if restored_policy != policy:
            raise ValueError("Packaged policy changed")
        if not np.array_equal(model.classes_, restored.classes_):
            raise ValueError("Packaged classes changed")
        if not np.array_equal(model.predict(probes), restored.predict(probes)):
            raise ValueError("Packaged predictions changed")
        if not np.allclose(
            model.predict_proba(probes), restored.predict_proba(probes),
            rtol=1e-10, atol=1e-12,
        ):
            raise ValueError("Packaged probabilities changed")
        if file_hash(champion_manifest) != champion_hash:
            raise RuntimeError("Original serving manifest unexpectedly changed")

        temporary.replace(destination)
        report = {
            "status": "PASS",
            "candidate_run_id": run_id,
            "bundle": str(destination.relative_to(ROOT)),
            "bundle_manifest_sha256": file_hash(destination / "manifest.json"),
            "acceptance_decision_sha256": file_hash(decision_path),
            "candidate_model_sha256": file_hash(source),
            "candidate_policy_sha256": file_hash(policy_path),
            "config_sha256": file_hash(config_path),
            "original_serving_manifest_sha256": champion_hash,
            "portable_loader_check": "PASS",
            "prediction_equivalence": "PASS",
            "probability_equivalence": "PASS",
            "smoke_examples": len(probes),
            "serving_model_replaced": False,
            "git_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
        }
        (report_dir / "candidate_packaging.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        logging.info("Candidate packaging complete:\n%s",
                     json.dumps(report, indent=2))
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Candidate packaging FAILED")
        raise

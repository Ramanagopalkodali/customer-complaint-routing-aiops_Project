"""Load a portable MLflow bundle after verifying its recorded file hashes."""
import hashlib
import json
from pathlib import Path

import mlflow.sklearn


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_bundle(directory):
    """Load from local files; no tracking database or original artifact URI."""
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text())
    for relative, expected in manifest["files"].items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory):
            raise ValueError("Invalid bundle file path")
        if not path.is_file() or file_hash(path) != expected:
            raise ValueError(f"Bundle integrity check failed: {relative}")

    policy = json.loads((directory / "policy.json").read_text())
    if policy["training_run_id"] != manifest["training_run_id"]:
        raise ValueError("Bundle model and policy run IDs differ")
    if policy["model_sha256"] != manifest["source_model_sha256"]:
        raise ValueError("Bundle source model identity differs")
    if policy["mode"] != "per_predicted_category":
        raise ValueError("Unsupported routing policy")

    model = mlflow.sklearn.load_model(str(directory / "model"))
    for threshold in policy["thresholds"].values():
        if threshold is not None and not 0 <= threshold <= 1:
            raise ValueError("Invalid policy threshold")
    return model, policy

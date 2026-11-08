"""Check portable loading and rejection of changed bundle files."""
import shutil
from pathlib import Path

import pytest

from backend.model_loader import load_bundle

ROOT = Path(__file__).resolve().parents[1]


def test_rejects_modified_policy(tmp_path):
    destination = tmp_path / "bundle"
    shutil.copytree(ROOT / "artifacts/serving", destination)
    policy = destination / "policy.json"
    policy.write_text(policy.read_text() + " ")

    with pytest.raises(ValueError, match="integrity check failed"):
        load_bundle(destination)


def test_loads_without_tracking_database(tmp_path, monkeypatch):
    database = tmp_path / "unused_tracking.db"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{database}")
    model, policy = load_bundle(ROOT / "artifacts/serving")

    assert len(model.classes_) == 5
    assert policy["training_run_id"]
    assert not database.exists()

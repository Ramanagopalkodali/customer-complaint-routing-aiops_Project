"""Verify live model identity is distinguished from saved evaluation evidence."""
import json
from types import SimpleNamespace

import pytest

from backend import pipeline


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="{}"),
    )
    (tmp_path / "dvc.yaml").write_text("stages: {}\n")
    folder = tmp_path / "reports/lifecycle/final"
    folder.mkdir(parents=True)
    (folder / "summary.json").write_text(json.dumps({
        "status": "PASS",
        "selected_training_run_id": "evaluated-model",
        "metrics": {"macro_f1": 0.83},
    }))
    return tmp_path


def test_evaluation_is_linked_to_matching_live_model(workspace):
    result = pipeline.pipeline_snapshot("evaluated-model")
    assert result["active_model_version"] == "evaluated-model"
    assert result["final_evaluation_matches_active_model"] is True
    assert result["lifecycle"]["final"]["metrics"]["macro_f1"] == 0.83


def test_different_live_model_does_not_inherit_historical_evaluation(workspace):
    result = pipeline.pipeline_snapshot("different-model")
    assert result["active_model_version"] == "different-model"
    assert result["final_evaluation_matches_active_model"] is False


def test_malformed_optional_evidence_does_not_break_console(workspace):
    path = workspace / "reports/lifecycle/final/summary.json"
    path.write_text("{broken")
    result = pipeline.pipeline_snapshot("evaluated-model")
    assert result["lifecycle"]["final"] is None
    assert result["final_evaluation_matches_active_model"] is False

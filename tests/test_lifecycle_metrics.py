"""Verify saved lifecycle metrics and malformed-report handling."""
import json

from backend.lifecycle_metrics import LifecycleCollector


def samples():
    return [
        sample for family in LifecycleCollector().collect()
        for sample in family.samples
    ]


def test_missing_reports_are_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_ROOT", str(tmp_path))
    availability = [
        sample for sample in samples()
        if sample.name == "complaint_lifecycle_report_available"
    ]
    assert len(availability) == 3
    assert all(sample.value == 0 for sample in availability)


def write_monitor(root, value):
    path = root / "reports/lifecycle/monitoring.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "status": "PASS",
        "provenance": {"champion_training_run_id": "original-model"},
        "metrics": {
            "text_length_jsd": value,
            "predicted_product_jsd": 0.01,
            "labeled_macro_f1": 0.83,
        },
        "retraining_required": False,
    }))


def test_valid_report_preserves_zero_trigger_and_model_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_ROOT", str(tmp_path))
    write_monitor(tmp_path, 0.02)
    result = samples()
    trigger = next(
        item for item in result
        if item.name == "complaint_lifecycle_retraining_required"
    )
    assert trigger.value == 0
    assert trigger.labels["training_run_id"] == "original-model"


def test_invalid_metric_does_not_publish_partial_report(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_ROOT", str(tmp_path))
    write_monitor(tmp_path, float("nan"))
    result = samples()
    assert not any(
        item.name == "complaint_lifecycle_text_length_jsd"
        for item in result
    )
    availability = next(
        item for item in result
        if item.name == "complaint_lifecycle_report_available"
        and item.labels["report"] == "monitoring"
    )
    assert availability.value == 0

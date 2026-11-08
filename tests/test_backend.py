"""Verify the real model's HTTP interface and validation behaviour."""
import pytest
from fastapi.testclient import TestClient

from backend.main import TEAMS, app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as instance:
        yield instance


def test_health(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model_version"]


def test_single_prediction_contract(client):
    response = client.post("/predict", json={
        "text": "My credit card was charged twice for the same purchase."
    })
    assert response.status_code == 200
    result = response.json()
    assert result["product"] in TEAMS
    assert 0 <= result["confidence"] <= 1
    assert result["recommended_team"] == TEAMS[result["product"]]
    expected_team = (
        "Human review" if result["human_review"]
        else result["recommended_team"]
    )
    assert result["assigned_team"] == expected_team
    assert result["human_review"] == (result["review_reason"] is not None)


@pytest.mark.parametrize("payload", [
    {},
    {"text": ""},
    {"text": "          "},
    {"text": "short"},
    {"text": 12345},
    {"text": None},
    {"text": "x" * 10001},
    {"text": "A sufficiently long complaint", "extra": True},
])
def test_rejects_invalid_single_input(client, payload):
    assert client.post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize("payload", [
    {"texts": []},
    {"texts": ["A sufficiently long complaint"] * 101},
    {"texts": ["A valid complaint narrative", ""]},
])
def test_rejects_invalid_batch(client, payload):
    assert client.post("/predict-batch", json=payload).status_code == 422


def test_batch_matches_single_predictions_in_order(client):
    texts = [
        "My mortgage payment was not credited to my loan account.",
        "My credit card was charged twice for the same purchase.",
    ]
    batch = client.post("/predict-batch", json={"texts": texts})
    assert batch.status_code == 200
    results = batch.json()["results"]
    assert len(results) == len(texts)
    for text, result in zip(texts, results):
        single = client.post("/predict", json={"text": text}).json()
        assert result["product"] == single["product"]
        assert result["confidence"] == pytest.approx(single["confidence"])
        assert result["human_review"] == single["human_review"]


def test_unrecognized_text_requires_review(client):
    response = client.post("/predict", json={
        "text": "zzzzqxv zzzzqxv zzzzqxv"
    })
    assert response.status_code == 200
    result = response.json()
    assert result["human_review"] is True
    assert result["review_reason"] == "unrecognized_text"
    assert result["assigned_team"] == "Human review"


def test_pipeline_snapshot(client):
    import base64

    response = client.get("/pipeline")
    assert response.status_code == 200
    snapshot = response.json()
    assert "ingest" in snapshot["stages"]
    assert "train" in snapshot["stages"]
    assert snapshot["workspace_status"] in {
        "up_to_date", "changes_detected", "unavailable"
    }
    image = base64.b64decode(snapshot["diagram_png_base64"])
    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    assert snapshot["ingestion"]["status"] == "PASS"
    assert snapshot["models"]


def metric_samples(client):
    from prometheus_client.parser import text_string_to_metric_families

    response = client.get("/metrics")
    assert response.status_code == 200
    return [
        sample
        for family in text_string_to_metric_families(response.text)
        for sample in family.samples
    ]


def sample_value(samples, name, labels):
    return sum(
        sample.value for sample in samples
        if sample.name == name
        and all(sample.labels.get(key) == value for key, value in labels.items())
    )


def test_metrics_count_success_and_validation_failure(client):
    before = metric_samples(client)
    response = client.post("/predict", json={
        "text": "My credit card was charged twice for the same purchase."
    })
    assert response.status_code == 200
    result = response.json()
    assert client.post("/predict", json={"text": ""}).status_code == 422
    after = metric_samples(client)

    for status in ("200", "422"):
        labels = {"method": "POST", "route": "/predict", "status": status}
        assert sample_value(after, "complaint_http_requests_total", labels) == (
            sample_value(before, "complaint_http_requests_total", labels) + 1
        )

    labels = {
        "product": result["product"],
        "decision": "human_review" if result["human_review"] else "automatic",
    }
    assert sample_value(after, "complaint_predictions_total", labels) == (
        sample_value(before, "complaint_predictions_total", labels) + 1
    )
    assert sample_value(
        after, "complaint_http_duration_seconds_count", {"route": "/predict"}
    ) == sample_value(
        before, "complaint_http_duration_seconds_count", {"route": "/predict"}
    ) + 2


def test_metrics_expose_process_and_saved_evidence(client):
    samples = metric_samples(client)
    names = {sample.name for sample in samples}
    assert "process_resident_memory_bytes" in names
    assert "complaint_reference_test_macro_f1" in names
    assert sample_value(
        samples, "complaint_saved_report_available", {"report": "ingestion"}
    ) == 1
    assert sample_value(
        samples, "complaint_ingestion_rows_per_second", {}
    ) > 0

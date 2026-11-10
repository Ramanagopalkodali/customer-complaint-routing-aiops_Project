"""Prometheus instrumentation without complaint text or request-ID labels."""
import json
import os
from pathlib import Path

from prometheus_client import Counter, Gauge, Histogram, REGISTRY
from prometheus_client.core import GaugeMetricFamily

REQUESTS = Counter(
    "complaint_http_requests_total",
    "Completed HTTP requests, excluding metrics scrapes",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "complaint_http_duration_seconds",
    "Time to prepare HTTP response headers, excluding metrics scrapes",
    ["route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 15, 30),
)
PREDICTIONS = Counter(
    "complaint_predictions_total",
    "Complaints successfully processed and their routing decisions",
    ["product", "decision"],
)
CONFIDENCE = Histogram(
    "complaint_prediction_confidence",
    "Estimated confidence for successfully processed complaints",
    ["product"],
    buckets=(0, 0.25, 0.5, 0.67, 0.75, 0.85, 0.9, 0.95, 0.98, 1),
)
BATCH_SIZE = Histogram(
    "complaint_request_items",
    "Number of complaints per successful prediction request",
    buckets=(1, 2, 5, 10, 25, 50, 100),
)
MODEL = Gauge(
    "complaint_model_loaded",
    "Loaded model identity",
    ["training_run_id"],
)


def record_predictions(results):
    """Count successful responses without storing their input text."""
    BATCH_SIZE.observe(len(results))
    for result in results:
        decision = "human_review" if result.human_review else "automatic"
        PREDICTIONS.labels(result.product, decision).inc()
        CONFIDENCE.labels(result.product).observe(result.confidence)


class SavedEvidenceCollector:
    """Expose last saved pipeline results and their availability/freshness."""

    def describe(self):
        return []

    def collect(self):
        root = Path(os.environ.get(
            "PIPELINE_ROOT", str(Path(__file__).resolve().parents[1])
        ))
        available = GaugeMetricFamily(
            "complaint_saved_report_available",
            "Whether a saved report can currently be read", labels=["report"]
        )
        timestamp = GaugeMetricFamily(
            "complaint_saved_report_timestamp_seconds",
            "Modification time of the saved report", labels=["report"]
        )
        reports = {}
        for name, relative in {
            "ingestion": "reports/ingestion_summary.json",
            "test": "reports/test/summary.json",
        }.items():
            path = root / relative
            try:
                reports[name] = json.loads(path.read_text())
                timestamp.add_metric([name], path.stat().st_mtime)
                available.add_metric([name], 1)
            except (OSError, ValueError):
                available.add_metric([name], 0)
        yield available
        yield timestamp

        ingestion = reports.get("ingestion")
        if ingestion:
            yield GaugeMetricFamily(
                "complaint_ingestion_rows_per_second",
                "Throughput of the last saved ingestion run",
                value=ingestion["input_rows_per_second"],
            )
            yield GaugeMetricFamily(
                "complaint_ingestion_duration_seconds",
                "Duration of the last saved ingestion run",
                value=ingestion["duration_seconds"],
            )
            rows = GaugeMetricFamily(
                "complaint_dataset_rows",
                "Rows in the last saved processed datasets", labels=["split"]
            )
            for split, details in ingestion["splits"].items():
                rows.add_metric([split], details["output_rows"])
            yield rows

        test = reports.get("test")
        if test:
            metric = GaugeMetricFamily(
                "complaint_reference_test_macro_f1",
                "Historical held-out macro-F1; not live online accuracy",
                labels=["training_run_id"],
            )
            metric.add_metric(
                [test["training_run_id"]],
                test["metrics"]["test_macro_f1"],
            )
            yield metric


REGISTRY.register(SavedEvidenceCollector())

# Saved lifecycle evidence is separate from live request instrumentation.
from backend.lifecycle_metrics import LifecycleCollector
REGISTRY.register(LifecycleCollector())

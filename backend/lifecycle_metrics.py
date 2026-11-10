"""Expose saved lifecycle evidence as explicitly historical batch metrics."""
import json
import math
import os
from pathlib import Path

from prometheus_client.core import GaugeMetricFamily


class LifecycleCollector:
    """Treat missing, malformed or unsuccessful reports as unavailable."""

    def describe(self):
        return []

    def collect(self):
        root = Path(os.environ.get(
            "PIPELINE_ROOT", str(Path(__file__).resolve().parents[1])
        ))
        available = GaugeMetricFamily(
            "complaint_lifecycle_report_available",
            "Whether a complete successful lifecycle report can be read",
            labels=["report"],
        )
        age = GaugeMetricFamily(
            "complaint_lifecycle_report_timestamp_seconds",
            "Modification time of saved lifecycle evidence",
            labels=["report"],
        )
        specs = {
            "monitoring": (
                "reports/lifecycle/monitoring.json",
                [
                    ("complaint_lifecycle_text_length_jsd",
                     "Historical November monitoring text-length divergence",
                     ["metrics", "text_length_jsd"]),
                    ("complaint_lifecycle_product_jsd",
                     "Historical November monitoring predicted-product divergence",
                     ["metrics", "predicted_product_jsd"]),
                    ("complaint_lifecycle_monitor_macro_f1",
                     "Historical November monitoring macro-F1",
                     ["metrics", "labeled_macro_f1"]),
                    ("complaint_lifecycle_retraining_required",
                     "Retraining trigger recorded for the historical monitoring batch",
                     ["retraining_required"]),
                ],
            ),
            "acceptance": (
                "reports/lifecycle/acceptance/decision.json",
                [
                    ("complaint_lifecycle_candidate_accepted",
                     "Whether the historical candidate passed the acceptance gate",
                     ["candidate_accepted"]),
                ],
            ),
            "final": (
                "reports/lifecycle/final/summary.json",
                [
                    ("complaint_lifecycle_final_macro_f1",
                     "Historical December selected-model macro-F1; not online accuracy",
                     ["metrics", "macro_f1"]),
                    ("complaint_lifecycle_final_automatic_accuracy",
                     "Historical December automatic-routing accuracy",
                     ["metrics", "automatic_accuracy"]),
                    ("complaint_lifecycle_final_automatic_coverage",
                     "Historical December automatic-routing coverage",
                     ["metrics", "automatic_coverage"]),
                ],
            ),
        }
        families = []
        for report, (relative, fields) in specs.items():
            path = root / relative
            try:
                data = json.loads(path.read_text())
                if data["status"] != "PASS":
                    raise ValueError("Report is not successful")
                if report == "monitoring":
                    version = data["provenance"]["champion_training_run_id"]
                elif report == "acceptance":
                    if data["decision"] not in {
                        "candidate_accepted", "champion_retained"
                    }:
                        raise ValueError("Unknown acceptance decision")
                    data["candidate_accepted"] = (
                        data["decision"] == "candidate_accepted"
                    )
                    version = data["candidate_run_id"]
                else:
                    version = data["selected_training_run_id"]
                if not isinstance(version, str) or not version:
                    raise ValueError("Missing model identity")

                pending = []
                for name, description, keys in fields:
                    value = data
                    for key in keys:
                        value = value[key]
                    if not isinstance(value, (int, float)):
                        raise ValueError("Metric must be numeric")
                    value = float(value)
                    if not math.isfinite(value) or not 0 <= value <= 1:
                        raise ValueError("Metric must be finite and within [0, 1]")
                    family = GaugeMetricFamily(
                        name, description, labels=["training_run_id"]
                    )
                    family.add_metric([version], value)
                    pending.append(family)
                modified = path.stat().st_mtime
            except (OSError, ValueError, KeyError, TypeError):
                available.add_metric([report], 0)
            else:
                available.add_metric([report], 1)
                age.add_metric([report], modified)
                families.extend(pending)
        yield available
        yield age
        yield from families

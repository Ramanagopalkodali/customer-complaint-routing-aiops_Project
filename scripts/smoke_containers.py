"""Check deployed container endpoints and save actual results."""
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
checks = []


def check(name, condition):
    checks.append({"check": name, "passed": bool(condition)})
    if not condition:
        raise AssertionError(name)


try:
    base = "http://127.0.0.1:8000"
    response = requests.get(base + "/healthz", timeout=15)
    check("backend_health", response.status_code == 200)

    text = "My credit card was charged twice for the same purchase."
    response = requests.post(
        base + "/predict", json={"text": text}, timeout=30
    )
    check("single_prediction", response.status_code == 200)
    result = response.json()
    check("confidence_range", 0 <= result["confidence"] <= 1)

    batch = requests.post(
        base + "/predict-batch", json={"texts": [text, text]}, timeout=30
    )
    check("batch_prediction", batch.status_code == 200)
    check("batch_count", len(batch.json()["results"]) == 2)

    invalid = requests.post(
        base + "/predict", json={"text": ""}, timeout=15
    )
    check("invalid_input_rejected", invalid.status_code == 422)

    review = requests.post(
        base + "/predict",
        json={"text": "zzzzqxv zzzzqxv zzzzqxv"}, timeout=30,
    )
    check("unrecognized_text_requires_review",
          review.status_code == 200 and review.json()["human_review"])

    pipeline = requests.get(base + "/pipeline", timeout=30)
    check("pipeline_endpoint", pipeline.status_code == 200)
    check("pipeline_has_training", "train" in pipeline.json()["stages"])

    frontend = requests.get(
        "http://127.0.0.1:8501/_stcore/health", timeout=15
    )
    check("frontend_health", frontend.status_code == 200)
except Exception as exc:
    checks.append({"check": "execution_error", "passed": False,
                   "error": str(exc)})
finally:
    report = {
        "status": "PASS" if checks and all(c["passed"] for c in checks)
                  else "FAIL",
        "checks": checks,
    }
    destination = ROOT / "reports/container_smoke.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if report["status"] != "PASS":
    raise SystemExit(1)

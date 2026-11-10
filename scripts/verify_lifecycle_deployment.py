"""Verify candidate deployment, rollback and redeployment over real HTTP.

Persist the final bundle choice in .env only after successful verification.
Reports contain prediction results but no submitted complaint narratives.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests

from backend.main import RoutingService
from src.monitor_lifecycle import file_hash

REPORT = ROOT / "reports/lifecycle/deployment_verification.json"
LOG = ROOT / "logs/lifecycle_deployment.log"
ORIGINAL = ROOT / "artifacts/serving"
CANDIDATE = ROOT / "artifacts/lifecycle/candidate/serving"
TEXTS = [
    "My credit card was charged twice for the same purchase.",
    "My mortgage payment was not credited to my loan account.",
    "The credit reporting company has not corrected my report.",
    "A debt collector is contacting me about a debt that is not mine.",
    "My bank has not returned money missing from my checking account.",
    "zzzzqxv zzzzqxv zzzzqxv",
]


def persist_choice(bundle):
    """Update only the bundle setting; never print other .env settings."""
    path = ROOT / ".env"
    lines = path.read_text().splitlines() if path.exists() else []
    lines = [
        line for line in lines
        if not line.strip().startswith(("SERVING_BUNDLE_PATH=", "export SERVING_BUNDLE_PATH="))
    ]
    relative = "./" + str(bundle.relative_to(ROOT))
    lines.append(f"SERVING_BUNDLE_PATH={relative}")
    temporary = ROOT / ".env.lifecycle.tmp"
    temporary.write_text("\n".join(lines) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def expected_predictions(bundle):
    previous = os.environ.get("SERVING_DIR")
    os.environ["SERVING_DIR"] = str(bundle)
    try:
        service = RoutingService()
        version = service.version
        results = [item.model_dump() for item in service.predict(TEXTS)]
        return version, results
    finally:
        if previous is None:
            os.environ.pop("SERVING_DIR", None)
        else:
            os.environ["SERVING_DIR"] = previous


def switch(bundle):
    environment = os.environ.copy()
    environment["SERVING_BUNDLE_PATH"] = str(bundle)
    command = [
        "docker", "compose",
        "-f", "compose.yaml", "-f", "compose.override.yaml",
        "up", "-d", "--no-deps", "--force-recreate",
        "--wait", "--wait-timeout", "90", "backend",
    ]
    with LOG.open("a") as stream:
        subprocess.run(
            command, cwd=ROOT, env=environment,
            stdout=stream, stderr=subprocess.STDOUT,
            check=True, timeout=120,
        )


def compare(actual, expected):
    if actual.keys() != expected.keys():
        raise ValueError("HTTP prediction fields differ from local contract")
    for key, value in expected.items():
        if key in {"confidence", "threshold"} and value is not None:
            if not math.isclose(actual[key], value, rel_tol=1e-7, abs_tol=1e-9):
                raise ValueError(f"HTTP/local mismatch: {key}")
        elif actual[key] != value:
            raise ValueError(f"HTTP/local mismatch: {key}")


def verify(name, bundle, version, expected):
    print(f"{name}: switching backend...", flush=True)
    switch(bundle)
    with requests.Session() as session:
        response = session.get("http://127.0.0.1:8000/healthz", timeout=15)
        response.raise_for_status()
        health = response.json()
        if health.get("model_version") != version or health.get("status") != "ok":
            raise ValueError("Unexpected live model identity")

        response = session.post(
            "http://127.0.0.1:8000/predict-batch",
            json={"texts": TEXTS}, timeout=30,
        )
        response.raise_for_status()
        actual = response.json()["results"]
        if len(actual) != len(expected):
            raise ValueError("Unexpected batch result count")
        for result, reference in zip(actual, expected):
            compare(result, reference)

        single = session.post(
            "http://127.0.0.1:8000/predict",
            json={"text": TEXTS[0]}, timeout=15,
        )
        single.raise_for_status()
        compare(single.json(), expected[0])

        invalid = session.post(
            "http://127.0.0.1:8000/predict",
            json={"text": ""}, timeout=15,
        )
        if invalid.status_code != 422:
            raise ValueError("Invalid input was not rejected")
        frontend = session.get(
            "http://127.0.0.1:8501/_stcore/health", timeout=15
        )
        frontend.raise_for_status()
    print(f"{name}: PASS; model_version={version}", flush=True)
    return {
        "phase": name,
        "status": "PASS",
        "model_version": version,
        "batch_predictions_checked": len(actual),
        "single_prediction_matches": True,
        "invalid_input_status": invalid.status_code,
        "frontend_health_status": frontend.status_code,
        "predictions": actual,
    }


def main():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(exist_ok=True)
    packaging_path = ROOT / "reports/lifecycle/candidate_packaging.json"
    packaging = json.loads(packaging_path.read_text())
    decision_path = ROOT / "reports/lifecycle/acceptance/decision.json"
    decision = json.loads(decision_path.read_text())
    if packaging["status"] != "PASS" or decision["decision"] != "candidate_accepted":
        raise ValueError("Successful candidate packaging and acceptance required")
    if file_hash(decision_path) != packaging["acceptance_decision_sha256"]:
        raise ValueError("Acceptance report changed since packaging")
    if file_hash(ROOT / "config/lifecycle.json") != packaging["config_sha256"]:
        raise ValueError("Frozen policy changed since packaging")
    original_hash = file_hash(ORIGINAL / "manifest.json")
    candidate_hash = file_hash(CANDIDATE / "manifest.json")
    if original_hash != packaging["original_serving_manifest_sha256"]:
        raise ValueError("Original bundle identity changed")
    if candidate_hash != packaging["bundle_manifest_sha256"]:
        raise ValueError("Candidate bundle identity changed")

    original_version, original_expected = expected_predictions(ORIGINAL)
    candidate_version, candidate_expected = expected_predictions(CANDIDATE)
    if candidate_version != decision["selected_run_id"]:
        raise ValueError("Candidate differs from selected model")
    if original_version != decision["champion_run_id"]:
        raise ValueError("Rollback model differs from original champion")
    if original_version == candidate_version:
        raise ValueError("Deployment and rollback identities must differ")

    record = {
        "status": "RUNNING",
        "scope": "Local sequential deployment and rollback drill; no traffic split",
        "phases": [],
        "packaging_report_sha256": file_hash(packaging_path),
        "original_manifest_sha256": original_hash,
        "candidate_manifest_sha256": candidate_hash,
    }
    try:
        for name, bundle, version, expected in (
            ("candidate_deployment", CANDIDATE, candidate_version, candidate_expected),
            ("original_model_rollback", ORIGINAL, original_version, original_expected),
            ("candidate_redeployment", CANDIDATE, candidate_version, candidate_expected),
        ):
            record["phases"].append(verify(name, bundle, version, expected))
            REPORT.write_text(json.dumps(record, indent=2) + "\n")

        if file_hash(ORIGINAL / "manifest.json") != original_hash:
            raise ValueError("Original manifest changed during deployment")
        if file_hash(CANDIDATE / "manifest.json") != candidate_hash:
            raise ValueError("Candidate manifest changed during deployment")
        persist_choice(CANDIDATE)
        record.update({
            "status": "PASS",
            "active_model_version": candidate_version,
            "persistent_bundle": str(CANDIDATE.relative_to(ROOT)),
            "rollback_verified": True,
            "december_evaluated": False,
        })
    except Exception as error:
        record["status"] = "FAIL"
        record["error"] = str(error)
        try:
            persist_choice(ORIGINAL)
            record["recovery"] = verify(
                "failure_recovery", ORIGINAL, original_version, original_expected
            )
        except Exception as recovery_error:
            record["recovery_error"] = str(recovery_error)
        REPORT.write_text(json.dumps(record, indent=2) + "\n")
        raise

    REPORT.write_text(json.dumps(record, indent=2) + "\n")
    print("\nPASS: candidate deployment, original rollback and candidate redeployment.")
    print("Active model:", candidate_version)
    print("Saved evidence:", REPORT.relative_to(ROOT))
    print("Default Docker Compose startup now selects the candidate through .env.")


if __name__ == "__main__":
    main()

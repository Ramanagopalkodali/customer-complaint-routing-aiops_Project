"""Conditional controller for the frozen historical lifecycle experiment.

Reuse matching saved monitoring evidence without rewriting completed results.
Triggered execution requires the original champion to be active and fresh
candidate output locations. This is a fixed historical workflow, not an
unrestricted production retraining service.
"""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

import requests

from src.monitor_lifecycle import file_hash

ROOT = Path(__file__).resolve().parents[1]


def run_workflow(monitor, train, accept, package, deploy):
    """Execute only the steps justified by monitoring and acceptance."""
    monitoring = monitor()
    if monitoring.get("status") != "PASS":
        raise ValueError("Monitoring must pass")
    trigger = monitoring.get("retraining_required")
    if not isinstance(trigger, bool):
        raise ValueError("Monitoring trigger must be a boolean")
    if not trigger:
        return {"outcome": "no_trigger", "deployment_requested": False}

    train()
    decision = accept()
    if decision.get("status") != "PASS":
        raise ValueError("Acceptance evaluation must complete successfully")
    checks = decision.get("checks")
    if not isinstance(checks, dict) or not checks:
        raise ValueError("Acceptance checks are missing")
    if any(not isinstance(value, bool) for value in checks.values()):
        raise ValueError("Acceptance checks must be booleans")
    approved = all(checks.values())
    expected = "candidate_accepted" if approved else "champion_retained"
    if decision.get("decision") != expected:
        raise ValueError("Acceptance decision contradicts its checks")
    if not approved:
        return {"outcome": "candidate_rejected", "deployment_requested": False}

    package()
    deploy()
    return {"outcome": "candidate_deployed", "deployment_requested": True}


def read_json(relative):
    return json.loads((ROOT / relative).read_text())


def live_version():
    response = requests.get("http://127.0.0.1:8000/healthz", timeout=15)
    response.raise_for_status()
    result = response.json()
    if result.get("status") != "ok" or not result.get("model_version"):
        raise ValueError("Backend health or model identity is invalid")
    return result["model_version"]


def save_report(path, record):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def main():
    report_path = ROOT / "reports/lifecycle/runner.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    lock_path = ROOT / ".dvc/tmp/lifecycle_runner.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record = {
            "status": "RUNNING",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Frozen historical November lifecycle",
            "steps": [],
            "december_evaluation_requested": False,
        }

        def execute(name, arguments):
            record["steps"].append(name)
            save_report(report_path, record)
            print(f"Running {name}...", flush=True)
            with (log_dir / f"lifecycle_runner_{name}.log").open("w") as stream:
                subprocess.run(
                    [sys.executable, *arguments], cwd=ROOT,
                    stdout=stream, stderr=subprocess.STDOUT, check=True,
                )

        try:
            config_path = ROOT / "config/lifecycle.json"
            config = read_json("config/lifecycle.json")
            initial_version = live_version()
            record["initial_active_model_version"] = initial_version
            record["config_sha256"] = file_hash(config_path)
            record["git_commit"] = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip()

            def monitor():
                path = ROOT / "reports/lifecycle/monitoring.json"
                if path.exists():
                    record["monitoring_evidence"] = "reused_verified_saved_report"
                else:
                    execute("monitor", ["-m", "src.monitor_lifecycle"])
                    record["monitoring_evidence"] = "new_monitoring_run"

                result = read_json("reports/lifecycle/monitoring.json")
                expected = {
                    "config_sha256": config_path,
                    "reference_source_sha256":
                        ROOT / config["monitoring"]["reference_source"],
                    "future_source_sha256":
                        ROOT / "data/processed/future.csv",
                    "serving_manifest_sha256":
                        ROOT / "artifacts/serving/manifest.json",
                }
                for key, path in expected.items():
                    if file_hash(path) != result["provenance"][key]:
                        raise ValueError(
                            f"Saved monitoring evidence is stale: {key}. "
                            "Preserve the completed experiment; do not overwrite it."
                        )
                if (
                    result["provenance"]["champion_training_run_id"]
                    != config["champion_training_run_id"]
                ):
                    raise ValueError("Monitoring champion differs from configuration")
                if result["period"] != config["periods"]["monitor_and_candidate_train"]:
                    raise ValueError("Monitoring period differs from configuration")
                record["monitoring_report_sha256"] = file_hash(
                    ROOT / "reports/lifecycle/monitoring.json"
                )
                return result

            def train():
                if initial_version != config["champion_training_run_id"]:
                    raise ValueError(
                        "Triggered replay requires the configured original champion "
                        "to be active. Refusing to compare/deploy against an old baseline."
                    )
                existing = [
                    ROOT / "artifacts/lifecycle/candidate/model.joblib",
                    ROOT / "artifacts/lifecycle/candidate/policy.json",
                    ROOT / "artifacts/lifecycle/candidate/serving",
                    ROOT / "reports/lifecycle/candidate/training_summary.json",
                    ROOT / "reports/lifecycle/acceptance/decision.json",
                    ROOT / "reports/lifecycle/candidate_packaging.json",
                ]
                if any(path.exists() for path in existing):
                    raise FileExistsError(
                        "Candidate outputs already exist. Refusing to overwrite "
                        "the completed historical experiment."
                    )
                execute("train", ["-m", "src.retrain_candidate"])
                summary = read_json(
                    "reports/lifecycle/candidate/training_summary.json"
                )
                if (
                    summary.get("status") != "PASS"
                    or summary.get("automatic_trigger_occurred") is not True
                    or summary.get("training_reason") != "monitoring_trigger"
                ):
                    raise ValueError("Candidate did not train from a real trigger")

            def accept():
                execute("accept", ["-m", "src.accept_candidate"])
                return read_json("reports/lifecycle/acceptance/decision.json")

            def package():
                execute("package", ["-m", "src.package_candidate"])
                if read_json("reports/lifecycle/candidate_packaging.json")["status"] != "PASS":
                    raise ValueError("Candidate packaging failed")

            def deploy():
                execute("deploy", ["scripts/verify_lifecycle_deployment.py"])
                result = read_json("reports/lifecycle/deployment_verification.json")
                selected = read_json(
                    "reports/lifecycle/acceptance/decision.json"
                )["selected_run_id"]
                if result["status"] != "PASS" or live_version() != selected:
                    raise ValueError("Selected model deployment was not verified")

            outcome = run_workflow(monitor, train, accept, package, deploy)
            final_version = live_version()
            if not outcome["deployment_requested"] and final_version != initial_version:
                raise RuntimeError("Active model changed despite no deployment request")
            record.update(outcome)
            record.update({
                "status": "PASS",
                "final_active_model_version": final_version,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as error:
            record.update({
                "status": "FAIL",
                "error": str(error),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            save_report(report_path, record)
            raise

        save_report(report_path, record)
        print(json.dumps(record, indent=2))
        print("Saved:", report_path.relative_to(ROOT))


if __name__ == "__main__":
    main()

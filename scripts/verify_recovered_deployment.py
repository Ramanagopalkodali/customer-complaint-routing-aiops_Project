"""Build and smoke-test the recovered checkout on separate localhost ports."""
import json
import os
from pathlib import Path
import secrets
import subprocess

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    report_path = ROOT / "reports/final/recovered_deployment.json"
    log_path = ROOT / "logs/recovered_deployment.log"
    log_path.parent.mkdir(exist_ok=True)
    recovery = json.loads(
        (ROOT / "reports/final/artifact_recovery.json").read_text()
    )
    if recovery["status"] != "PASS":
        raise ValueError("Artifact recovery must pass first")
    checkout = Path(recovery["checkout"]).resolve()
    if checkout == ROOT or not (checkout / ".git").is_dir():
        raise ValueError("Expected the separate recovery checkout")

    expected_version = recovery["model_checks"]["candidate"]["training_run_id"]
    report = {
        "status": "RUNNING",
        "checkout": str(checkout),
        "scope": "Recovered-checkout Docker build and HTTP smoke verification",
        "expected_model_version": expected_version,
        "ports": {"backend": 8002, "frontend": 8502},
    }
    command_prefix = [
        "docker", "compose", "-p", "complaint-routing-recovery-check",
        "-f", "compose.yaml", "-f", "compose.override.yaml",
    ]

    def compose(arguments):
        result = subprocess.run(
            command_prefix + arguments, cwd=checkout,
            capture_output=True, text=True,
        )
        with log_path.open("a") as stream:
            stream.write(
                "\nCOMMAND: " + repr(arguments) + "\n"
                + result.stdout + result.stderr
            )
        if result.returncode:
            raise RuntimeError(
                f"Recovery Compose command failed: {arguments}\n"
                f"{result.stdout}\n{result.stderr}"
            )
        return result.stdout

    # These edits affect only the disposable recovery checkout.
    path = checkout / "compose.yaml"
    config = yaml.safe_load(path.read_text())
    config["services"]["backend"]["ports"] = ["127.0.0.1:8002:8000"]
    config["services"]["frontend"]["ports"] = ["127.0.0.1:8502:8501"]
    config["services"]["backend"]["image"] = "complaint-routing-recovery-backend:local"
    config["services"]["frontend"]["image"] = "complaint-routing-recovery-frontend:local"
    path.write_text(yaml.safe_dump(config, sort_keys=False))

    template = (checkout / ".env.example").read_text().splitlines()
    replaced = {
        "LOCAL_UID", "LOCAL_GID", "GRAFANA_ADMIN_PASSWORD", "SERVING_BUNDLE_PATH"
    }
    lines = [
        line for line in template
        if line.split("=", 1)[0].strip() not in replaced
    ]
    lines.extend([
        f"LOCAL_UID={os.getuid()}",
        f"LOCAL_GID={os.getgid()}",
        f"GRAFANA_ADMIN_PASSWORD={secrets.token_urlsafe(24)}",
        "SERVING_BUNDLE_PATH=./artifacts/lifecycle/candidate/serving",
    ])
    env_path = checkout / ".env"
    env_path.write_text("\n".join(lines) + "\n")
    env_path.chmod(0o600)

    try:
        print("Building both application images from the recovered checkout...",
              flush=True)
        compose(["build", "backend", "frontend"])
        print("Starting the recovery application on ports 8002/8502...", flush=True)
        compose([
            "up", "-d", "--wait", "--wait-timeout", "90",
            "backend", "frontend",
        ])

        with requests.Session() as session:
            health = session.get("http://127.0.0.1:8002/healthz", timeout=15)
            health.raise_for_status()
            assert health.json()["status"] == "ok"
            assert health.json()["model_version"] == expected_version

            prediction = session.post(
                "http://127.0.0.1:8002/predict",
                json={"text": "My credit card was charged twice for the same purchase."},
                timeout=30,
            )
            prediction.raise_for_status()
            result = prediction.json()
            assert result["model_version"] == expected_version
            assert 0 <= result["confidence"] <= 1
            assert result["assigned_team"] == (
                "Human review" if result["human_review"]
                else result["recommended_team"]
            )

            invalid = session.post(
                "http://127.0.0.1:8002/predict",
                json={"text": ""}, timeout=15,
            )
            assert invalid.status_code == 422

            frontend = session.get(
                "http://127.0.0.1:8502/_stcore/health", timeout=15
            )
            frontend.raise_for_status()

            pipeline = session.get(
                "http://127.0.0.1:8002/pipeline", timeout=45
            )
            pipeline.raise_for_status()
            assert pipeline.json()["active_model_version"] == expected_version
            assert pipeline.json()["final_evaluation_matches_active_model"] is True

        report.update({
            "status": "PASS",
            "images_built_from_recovered_checkout": True,
            "backend_health": health.json(),
            "single_prediction": "PASS",
            "invalid_input_status": invalid.status_code,
            "frontend_health": "PASS",
            "pipeline_model_identity": "PASS",
            "tracking_database_present": (checkout / "mlflow.db").exists(),
        })
    except Exception as error:
        report.update({"status": "FAIL", "error": str(error)})
        raise
    finally:
        try:
            compose(["down"])
            report["recovery_containers_removed"] = True
        except Exception as cleanup_error:
            report["cleanup_error"] = str(cleanup_error)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))

    print("Original application was not restarted.")


if __name__ == "__main__":
    main()

"""Replay the frozen lifecycle, deploy, evaluate and verify evidence.

Requires a successful baseline and committed champion binding.
Replaces generated lifecycle outputs; retains the pre-rebuild snapshot.
December evaluation follows acceptance without tuning against its results.
"""
import base64
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import time

import requests

from reproduce_baseline import (
    ROOT, SOURCE_PATHS, STAGES, file_hash, read_json, save, timestamp,
)

COMPOSE = [
    "docker", "compose",
    "-f", "compose.yaml", "-f", "compose.override.yaml",
]
LIVE_MIN_SECONDS = 20
LIVE_TIMEOUT_SECONDS = 90


def original_choice():
    """Select the rebuilt baseline while preserving Compose settings."""
    path = ROOT / ".env"
    lines = path.read_text().splitlines()
    lines = [
        line for line in lines
        if not line.strip().startswith((
            "SERVING_BUNDLE_PATH=",
            "export SERVING_BUNDLE_PATH=",
        ))
    ]
    temporary = ROOT / ".dvc/tmp/reproduction.env"
    temporary.write_text("\n".join(lines + [
        "SERVING_BUNDLE_PATH=./artifacts/serving"
    ]) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def live_checks(version, reports):
    """Verify HTTP identity and wait for fresh Prometheus samples."""
    def get(url, **kwargs):
        response = requests.get(url, timeout=10, **kwargs)
        response.raise_for_status()
        return response

    health = get("http://127.0.0.1:8000/healthz").json()
    if (
        health.get("status") != "ok"
        or health.get("model_version") != version
    ):
        raise ValueError("Live backend differs from evaluated model.")

    snapshot = get("http://127.0.0.1:8000/pipeline").json()
    if (
        snapshot.get("active_model_version") != version
        or not snapshot.get("final_evaluation_matches_active_model")
    ):
        raise ValueError("Pipeline/evaluation identity mismatch.")
    if any(value is None for value in snapshot["lifecycle"].values()):
        raise ValueError("Pipeline console is missing lifecycle reports.")

    diagram = base64.b64decode(
        snapshot["diagram_png_base64"], validate=True
    )
    if not diagram.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Pipeline diagram is not a PNG.")
    (reports / "pipeline_dag.png").write_bytes(diagram)

    get("http://127.0.0.1:8501/_stcore/health")
    grafana = get("http://127.0.0.1:3000/api/health").json()
    if grafana.get("database") != "ok":
        raise ValueError("Grafana is not ready.")

    started = time.monotonic()
    last_error = "No fresh monitoring samples yet."
    while time.monotonic() - started < LIVE_TIMEOUT_SECONDS:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/predict-batch",
                json={"texts": [
                    "My credit card was charged twice for the same purchase.",
                    "My mortgage payment was not credited to my loan account.",
                    "The credit reporting company has not corrected my report.",
                    "A debt collector is contacting me about a debt that is not mine.",
                    "My bank has not returned money missing from my checking account.",
                    "zzzzqxv zzzzqxv zzzzqxv",
                ]},
                timeout=30,
            )
            response.raise_for_status()
            predictions = response.json()["results"]
            if len(predictions) != 6 or any(
                item.get("model_version") != version
                for item in predictions
            ):
                raise ValueError("Synthetic traffic used an unexpected model.")

            targets = get(
                "http://127.0.0.1:9090/api/v1/targets"
            ).json()["data"]["activeTargets"]
            query = get(
                "http://127.0.0.1:9090/api/v1/query",
                params={
                    "query":
                        'complaint_lifecycle_final_macro_f1'
                        '{training_run_id="' + version + '"}'
                },
            ).json()
            samples = query.get("data", {}).get("result", [])

            probes = get(
                "http://127.0.0.1:9090/api/v1/query",
                params={"query": 'probe_success{job="service_probes"}'},
            ).json().get("data", {}).get("result", [])
            probes_ok = (
                len(probes) == 2
                and {
                    p["metric"].get("component") for p in probes
                } == {"backend", "frontend"}
                and all(float(p["value"][1]) == 1 for p in probes)
            )
            ready = (
                len(targets) == 6
                and all(t["health"] == "up" for t in targets)
            )
            enough_time = (
                time.monotonic() - started >= LIVE_MIN_SECONDS
            )
            if ready and probes_ok and len(samples) == 1 and enough_time:
                expected = read_json(
                    "reports/lifecycle/final/summary.json"
                )["metrics"]["macro_f1"]
                observed = float(samples[0]["value"][1])
                if abs(observed - expected) > 1e-10:
                    raise ValueError(
                        "Prometheus score differs from saved report."
                    )
                metrics = get("http://127.0.0.1:8000/metrics")
                (reports / "backend_metrics.prom").write_text(metrics.text)

                result = {
                    "status": "PASS",
                    "active_model_version": version,
                    "december_evaluation_matches_active_model": True,
                    "lifecycle_reports_present": {
                        name: value is not None
                        for name, value in snapshot["lifecycle"].items()
                    },
                    "frontend_health": "PASS",
                    "grafana_health": "PASS",
                    "prometheus_targets": [
                        {
                            "job": t["labels"].get("job"),
                            "health": t["health"],
                        }
                        for t in targets
                    ],
                    "fresh_final_score_in_prometheus": observed,
                    "application_probes": {
                        p["metric"]["component"]: 1 for p in probes
                    },
                    "traffic": "Synthetic smoke requests; not a load test",
                }
                save(
                    ROOT / "reports/final/pipeline_live_check.json",
                    result,
                )
                return result
            last_error = (
                "Waiting for six healthy targets and fresh final-model metrics."
            )
        except (
            requests.RequestException, KeyError, ValueError, TypeError
        ) as error:
            last_error = str(error)
        time.sleep(5)
    raise RuntimeError(last_error)


def main():
    """Run the replay and record every executed command and outcome."""
    os.chdir(ROOT)
    reports = ROOT / "reports/reproduction"
    logs = ROOT / "logs/reproduction"
    for path in (reports, logs, ROOT / ".dvc/tmp"):
        path.mkdir(parents=True, exist_ok=True)

    with (ROOT / ".dvc/tmp/reproduction.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = reports / "lifecycle.json"
        record = {
            "status": "RUNNING",
            "started_at": timestamp(),
            "steps": [],
            "scope": (
                "Historical lifecycle replay, live deployment and final tests"
            ),
            "artifact_recovery_and_tracking_backup_refreshed": False,
        }
        save(report, record)

        with (logs / "lifecycle.log").open("w") as log:
            def execute(name, arguments, pure_stdout=False):
                step = {
                    "name": name,
                    "command": arguments,
                    "status": "RUNNING",
                }
                record["steps"].append(step)
                save(report, record)
                print(f"\nRunning {name}...", flush=True)
                log.write(f"\n{name}: {arguments!r}\n")
                log.flush()

                environment = os.environ.copy()
                environment.pop("SERVING_BUNDLE_PATH", None)
                environment["PYTHONUNBUFFERED"] = "1"
                started = time.monotonic()
                output = []

                with subprocess.Popen(
                    arguments,
                    cwd=ROOT,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=log if pure_stdout else subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    start_new_session=True,
                ) as process:
                    try:
                        for line in process.stdout:
                            print(line, end="", flush=True)
                            log.write(line)
                            log.flush()
                            output.append(line)
                        code = process.wait()
                    except BaseException:
                        if process.poll() is None:
                            os.killpg(process.pid, signal.SIGINT)
                            try:
                                process.wait(timeout=15)
                            except subprocess.TimeoutExpired:
                                os.killpg(process.pid, signal.SIGKILL)
                                process.wait()
                        raise

                step.update(
                    status="PASS" if code == 0 else "FAIL",
                    exit_code=code,
                    duration_seconds=round(
                        time.monotonic() - started, 3
                    ),
                )
                save(report, record)
                if code:
                    raise subprocess.CalledProcessError(code, arguments)
                return "".join(output)

            def stage(name):
                execute(name, [
                    "dvc", "repro", "--single-item",
                    "--force", "--no-run-cache", name,
                ])

            def register(name):
                execute("record_" + name, [
                    "dvc", "commit", "--force", name,
                ])

            try:
                record["git_commit"] = execute(
                    "source_commit", ["git", "rev-parse", "HEAD"]
                ).strip()
                source_paths = (*SOURCE_PATHS, ".dvcignore")
                for arguments in (
                    ["git", "diff", "HEAD", "--", *source_paths],
                    [
                        "git", "ls-files", "--others",
                        "--exclude-standard", "--", *source_paths,
                    ],
                ):
                    if subprocess.check_output(
                        arguments, cwd=ROOT, text=True
                    ):
                        raise RuntimeError(
                            "Commit source/configuration before replay."
                        )

                baseline = read_json(
                    "reports/reproduction/baseline.json"
                )
                manifest_path = ROOT / "artifacts/serving/manifest.json"
                manifest = read_json("artifacts/serving/manifest.json")
                config = read_json("config/lifecycle.json")

                if (
                    baseline["status"] != "PASS"
                    or file_hash(manifest_path)
                    != baseline["serving_manifest_sha256"]
                ):
                    raise ValueError(
                        "A matching successful baseline is required."
                    )
                version = manifest["training_run_id"]
                if (
                    version != baseline["original_model_version"]
                    or version != config["champion_training_run_id"]
                ):
                    raise ValueError(
                        "Commit the correct champion binding first."
                    )
                if (
                    manifest["model_name"]
                    != config["candidate"]["model_type"]
                ):
                    raise ValueError(
                        "Candidate algorithm must match the cloned baseline."
                    )

                snapshot = (
                    ROOT.parent / "complaint-routing-before-rebuild.tar.gz"
                )
                if (
                    not snapshot.is_file()
                    or not tarfile.is_tarfile(snapshot)
                ):
                    raise ValueError(
                        "Pre-rebuild snapshot missing or unreadable."
                    )
                sources = read_json(
                    "config/raw_sources.json"
                )["archives"]
                if sources != baseline["raw_archives_sha256"]:
                    raise ValueError(
                        "Pinned inputs differ from the successful baseline."
                    )
                for name, expected in sources.items():
                    if file_hash(ROOT / "data/raw" / name) != expected:
                        raise ValueError(
                            f"Pinned raw archive changed: {name}"
                        )

                state = json.loads(execute(
                    "baseline_freshness",
                    ["dvc", "status", "--json", *STAGES],
                    True,
                ))
                if state:
                    raise ValueError(
                        "Baseline changed; inspect DVC status before replay."
                    )

                execute(
                    "compose_configuration",
                    COMPOSE + ["config", "--quiet"],
                )
                execute("stop_services", COMPOSE + ["down"])
                original_choice()

                generated = [
                    "reports/lifecycle",
                    "artifacts/lifecycle",
                    "reports/final/full_tests.xml",
                    "reports/final/tests_summary.json",
                    "reports/final/pipeline_live_check.json",
                ]
                if any(
                    (ROOT / name).is_symlink() for name in generated
                ):
                    raise ValueError(
                        "Generated output locations must not be symlinks."
                    )
                for name in generated:
                    path = ROOT / name
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink(missing_ok=True)

                for name in ("backend.log", "lifecycle_deployment.log"):
                    (ROOT / "logs" / name).write_text("")
                (ROOT / "reports/final").mkdir(
                    parents=True, exist_ok=True
                )
                record.update(
                    champion_run_id=version,
                    config_sha256=file_hash(
                        ROOT / "config/lifecycle.json"
                    ),
                    replaced_generated_paths=generated,
                )

                execute(
                    "build_applications",
                    COMPOSE + ["build", "backend", "frontend"],
                )
                execute(
                    "start_services",
                    COMPOSE + [
                        "up", "-d", "--wait",
                        "--wait-timeout", "180",
                    ],
                )

                stage("lifecycle_tests")
                execute("runner_tests", [
                    sys.executable, "-m", "pytest",
                    "tests/test_lifecycle_runner.py", "-q",
                    "--junitxml=reports/lifecycle/runner_tests.xml",
                ])
                stage("lifecycle_monitor")
                execute("conditional_controller", [
                    sys.executable, "-m", "src.run_lifecycle",
                ])

                monitoring = read_json(
                    "reports/lifecycle/monitoring.json"
                )
                triggered = monitoring["retraining_required"]
                record["automatic_trigger_occurred"] = triggered

                if triggered:
                    register("lifecycle_candidate_demo")
                    register("lifecycle_accept")
                else:
                    stage("lifecycle_candidate_demo")
                    stage("lifecycle_accept")

                decision = read_json(
                    "reports/lifecycle/acceptance/decision.json"
                )
                record["acceptance_decision"] = decision["decision"]
                record["training_reason"] = read_json(
                    "reports/lifecycle/candidate/training_summary.json"
                )["training_reason"]

                if decision["decision"] != "candidate_accepted":
                    record.update(
                        status="CHAMPION_RETAINED",
                        active_model_version=version,
                        december_evaluated=False,
                        reason=(
                            "Candidate did not pass every acceptance check."
                        ),
                    )
                    return 2

                if triggered:
                    register("lifecycle_package")
                else:
                    stage("lifecycle_package")
                    execute("deployment_rollback", [
                        sys.executable,
                        "scripts/verify_lifecycle_deployment.py",
                    ])

                register("lifecycle_deployment_record")
                execute("december_evaluation", [
                    sys.executable, "-m",
                    "src.evaluate_lifecycle_final",
                ])
                register("lifecycle_final_record")
                stage("final_checks")
                execute("http_smoke", [
                    sys.executable, "scripts/smoke_containers.py",
                ])

                selected = decision["selected_run_id"]
                record["live_checks"] = live_checks(
                    selected, reports
                )
                state = json.loads(execute(
                    "dvc_status", ["dvc", "status", "--json"], True
                ))
                save(
                    ROOT / "reports/lifecycle/dvc_status.json",
                    state,
                )
                diagram = execute(
                    "dvc_diagram",
                    ["dvc", "dag", "--mermaid"],
                    True,
                )
                (reports / "pipeline_dag.mmd").write_text(diagram)
                if state:
                    raise ValueError(
                        "DVC reports outstanding changes; inspect "
                        "reports/lifecycle/dvc_status.json."
                    )

                record.update(
                    status="PASS",
                    active_model_version=selected,
                    december_evaluated=True,
                    tests=read_json(
                        "reports/final/tests_summary.json"
                    )["counts"],
                )
            except BaseException as error:
                record.update(
                    status="FAIL",
                    error=f"{type(error).__name__}: {error}",
                )
                for step in record["steps"]:
                    if step["status"] == "RUNNING":
                        step["status"] = "FAIL"
                log.write(record["error"] + "\n")
                raise
            finally:
                record["completed_at"] = timestamp()
                save(report, record)
                print(json.dumps(record, indent=2), flush=True)
                print("Saved:", report, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

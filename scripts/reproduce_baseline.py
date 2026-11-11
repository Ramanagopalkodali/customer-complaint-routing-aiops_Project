"""Rebuild the seven baseline DVC stages and replace current evidence.

Stops Compose services while retaining volumes and MLflow history.
Historical lifecycle execution and its thresholds remain separate.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
STAGES = (
    "ingest", "validate_data", "train", "select_threshold",
    "validate_threshold", "evaluate", "export_model",
)
SOURCE_PATHS = (
    "src", "backend", "frontend", "scripts", "tests", "config",
    "requirements.txt", "requirements.lock.txt", "dvc.yaml",
    "Dockerfile", "compose.yaml", "compose.override.yaml",
)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def read_json(relative):
    return json.loads((ROOT / relative).read_text())


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save(path, record):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(record, indent=2, allow_nan=False) + "\n"
    )
    temporary.replace(path)


def main():
    os.chdir(ROOT)
    reports = ROOT / "reports/reproduction"
    logs = ROOT / "logs/reproduction"
    for path in (reports, logs, ROOT / ".dvc/tmp"):
        path.mkdir(parents=True, exist_ok=True)

    with (ROOT / ".dvc/tmp/reproduction.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record = {
            "status": "RUNNING",
            "started_at": timestamp(),
            "scope": (
                "Baseline ingestion, training, October evaluation and export"
            ),
            "steps": [],
            "lifecycle_replayed": False,
        }
        report = reports / "baseline.json"
        save(report, record)

        with (logs / "baseline.log").open("w") as log:
            def execute(name, arguments):
                step = {
                    "name": name,
                    "command": arguments,
                    "started_at": timestamp(),
                    "status": "RUNNING",
                }
                record["steps"].append(step)
                save(report, record)
                print(f"\nRunning {name}...", flush=True)
                log.write(f"\nRunning {name}: {arguments!r}\n")
                log.flush()
                started = time.monotonic()
                environment = os.environ.copy()
                environment.update(
                    PYTHONUNBUFFERED="1",
                    RAY_USAGE_STATS_ENABLED="0",
                )

                with subprocess.Popen(
                    arguments,
                    cwd=ROOT,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    start_new_session=True,
                ) as process:
                    try:
                        for line in process.stdout:
                            print(line, end="", flush=True)
                            log.write(line)
                            log.flush()
                        code = process.wait()
                    except BaseException:
                        if process.poll() is None:
                            os.killpg(process.pid, signal.SIGINT)
                            try:
                                process.wait(timeout=15)
                            except subprocess.TimeoutExpired:
                                os.killpg(process.pid, signal.SIGKILL)
                                process.wait()
                        step["status"] = "INTERRUPTED"
                        save(report, record)
                        raise

                step.update(
                    exit_code=code,
                    completed_at=timestamp(),
                    duration_seconds=round(
                        time.monotonic() - started, 3
                    ),
                    status="PASS" if code == 0 else "FAIL",
                )
                save(report, record)
                if code:
                    raise subprocess.CalledProcessError(code, arguments)

            try:
                record["git_commit"] = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    text=True, cwd=ROOT,
                ).strip()

                changed = subprocess.check_output(
                    ["git", "diff", "HEAD", "--", *SOURCE_PATHS],
                    text=True, cwd=ROOT,
                )
                untracked = subprocess.check_output(
                    [
                        "git", "ls-files", "--others",
                        "--exclude-standard", "--", *SOURCE_PATHS,
                    ],
                    text=True, cwd=ROOT,
                )
                if changed or untracked:
                    raise RuntimeError(
                        "Commit source/configuration changes before rebuilding."
                    )

                snapshot = (
                    ROOT.parent / "complaint-routing-before-rebuild.tar.gz"
                )
                if not snapshot.is_file() or not tarfile.is_tarfile(snapshot):
                    raise RuntimeError(
                        "The pre-rebuild snapshot is missing or unreadable."
                    )

                sources = read_json("config/raw_sources.json")["archives"]
                expected_names = {
                    "cfpb_2024_04_07.zip",
                    "cfpb_2024_08_10.zip",
                    "cfpb_2024_11_12.zip",
                }
                if set(sources) != expected_names:
                    raise ValueError(
                        "Expected the three pinned CFPB archives."
                    )

                for name, expected in sources.items():
                    if file_hash(ROOT / "data/raw" / name) != expected:
                        raise ValueError(
                            f"Raw archive differs from pinned input: {name}"
                        )
                record["raw_archives_sha256"] = sources

                execute(
                    "dependencies",
                    [sys.executable, "-m", "pip", "check"],
                )
                execute(
                    "compose_configuration",
                    ["docker", "compose", "config", "--quiet"],
                )
                execute(
                    "stop_services",
                    ["docker", "compose", "down"],
                )

                for stage in STAGES:
                    execute(
                        stage,
                        [
                            "dvc", "repro", "--single-item",
                            "--force", "--no-run-cache", stage,
                        ],
                    )

                policy = read_json("artifacts/policy.json")
                manifest = read_json("artifacts/serving/manifest.json")
                if manifest["training_run_id"] != policy["training_run_id"]:
                    raise ValueError(
                        "Exported bundle and selected policy differ."
                    )

                for name, expected in sources.items():
                    if file_hash(ROOT / "data/raw" / name) != expected:
                        raise ValueError(
                            f"Raw archive changed during rebuilding: {name}"
                        )

                record.update(
                    status="PASS",
                    original_model_version=policy["training_run_id"],
                    selected_model=policy["model_name"],
                    serving_manifest_sha256=file_hash(
                        ROOT / "artifacts/serving/manifest.json"
                    ),
                    lifecycle_binding_required=(
                        read_json("config/lifecycle.json")[
                            "champion_training_run_id"
                        ] != policy["training_run_id"]
                    ),
                    next_step=(
                        "Bind and commit the new champion identity "
                        "before lifecycle replay."
                    ),
                )
            except BaseException as error:
                record.update(
                    status="FAIL",
                    error=f"{type(error).__name__}: {error}",
                )
                for step in record["steps"]:
                    if step["status"] == "RUNNING":
                        step.update(
                            status="FAIL", completed_at=timestamp()
                        )
                log.write(record["error"] + "\n")
                raise
            finally:
                record["completed_at"] = timestamp()
                save(report, record)
                print(json.dumps(record, indent=2), flush=True)
                print("Saved:", report, flush=True)


if __name__ == "__main__":
    main()

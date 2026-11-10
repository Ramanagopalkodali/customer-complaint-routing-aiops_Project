"""Verify local DVC recovery into a separate Git checkout and empty cache."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    report_path = ROOT / "reports/final/artifact_recovery.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "logs/artifact_recovery.log"
    log_path.parent.mkdir(exist_ok=True)

    parent = Path.home() / "complaint-routing-recovery-checks"
    parent.mkdir(exist_ok=True)
    checkout = Path(tempfile.mkdtemp(prefix="checkout_", dir=parent))
    remote = Path.home() / "complaint-routing-dvc-store"
    record = {
        "status": "RUNNING",
        "checkout": str(checkout),
        "remote": str(remote),
        "scope": "Same-VM artifact recovery and portable inference verification",
        "docker_deployment_tested": False,
        "off_machine_backup": False,
    }

    def command(arguments, cwd):
        result = subprocess.run(
            arguments, cwd=cwd, capture_output=True, text=True
        )
        with log_path.open("a") as log:
            log.write(
                "\nCOMMAND: " + repr(arguments) + "\n"
                + result.stdout + result.stderr
            )
        if result.returncode:
            raise RuntimeError(
                f"Command failed: {arguments}\n{result.stdout}\n{result.stderr}"
            )
        return result.stdout.strip()

    try:
        source_commit = command(["git", "rev-parse", "HEAD"], ROOT)
        print("Creating separate checkout...", flush=True)
        command(
            ["git", "clone", "--no-hardlinks", str(ROOT), str(checkout)], ROOT
        )
        assert command(["git", "rev-parse", "HEAD"], checkout) == source_commit

        cache = checkout / ".dvc/cache"
        command(
            ["dvc", "config", "--local", "cache.dir", str(cache)], checkout
        )
        actual_cache = Path(command(["dvc", "cache", "dir"], checkout)).resolve()
        assert actual_cache == cache.resolve(), "Cache is not isolated"
        assert not cache.exists() or not any(cache.rglob("*")), "Cache is not empty"

        command(
            ["dvc", "remote", "add", "--local", "-d", "localstore", str(remote)],
            checkout,
        )
        print("Pulling artifacts into the empty cache...", flush=True)
        command(["dvc", "pull"], checkout)

        for relative in (
            "data/raw",
            "data/processed/train.csv",
            "data/processed/validation.csv",
            "data/processed/test.csv",
            "data/processed/future.csv",
            "artifacts/serving/manifest.json",
            "artifacts/lifecycle/candidate/serving/manifest.json",
        ):
            assert (checkout / relative).exists(), f"Missing restored path: {relative}"

        print("Checking restored model integrity and prediction equivalence...",
              flush=True)
        check_code = r'''
import json
from pathlib import Path
import sys
import numpy as np
from backend.model_loader import load_bundle

original_root = Path(sys.argv[1])
checkout = Path.cwd()
probes = np.array([
    "My credit card was charged twice for the same purchase.",
    "My mortgage payment was not credited to my loan account.",
    "The credit reporting company has not corrected my report.",
    "A debt collector is contacting me about a debt that is not mine.",
    "My bank has not returned money missing from my checking account.",
    "zzzzqxv zzzzqxv zzzzqxv",
])
results = {}
for name, relative in {
    "original": "artifacts/serving",
    "candidate": "artifacts/lifecycle/candidate/serving",
}.items():
    reference, reference_policy = load_bundle(original_root / relative)
    restored, restored_policy = load_bundle(checkout / relative)
    assert reference_policy == restored_policy
    assert np.array_equal(reference.classes_, restored.classes_)
    assert np.array_equal(reference.predict(probes), restored.predict(probes))
    assert np.allclose(
        reference.predict_proba(probes), restored.predict_proba(probes),
        rtol=1e-10, atol=1e-12,
    )
    results[name] = {
        "status": "PASS",
        "training_run_id": restored_policy["training_run_id"],
        "integrity_and_equivalence": "PASS",
        "smoke_examples": len(probes),
    }
assert not (checkout / "mlflow.db").exists(), "Unexpected tracking DB dependency"
print(json.dumps(results))
'''
        checks = json.loads(command(
            [sys.executable, "-c", check_code, str(ROOT)], checkout
        ))
        record.update({
            "status": "PASS",
            "source_commit": source_commit,
            "isolated_cache": str(actual_cache),
            "cache_started_empty": True,
            "dvc_pull_succeeded": True,
            "model_checks": checks,
            "inference_without_tracking_database": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        store_path = ROOT / "reports/final/artifact_store.json"
        store = json.loads(store_path.read_text())
        store["fresh_checkout_recovery_verified"] = True
        store_path.write_text(json.dumps(store, indent=2) + "\n")
    except Exception as error:
        record.update({"status": "FAIL", "error": str(error)})
        report_path.write_text(json.dumps(record, indent=2) + "\n")
        raise

    report_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    print("Saved:", report_path.relative_to(ROOT))


if __name__ == "__main__":
    main()

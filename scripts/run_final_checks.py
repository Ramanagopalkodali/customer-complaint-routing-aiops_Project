"""Run the complete test suite against the selected candidate serving bundle."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "reports/final"
    folder.mkdir(parents=True, exist_ok=True)
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)

    bundle = ROOT / "artifacts/lifecycle/candidate/serving"
    manifest = json.loads((bundle / "manifest.json").read_text())
    final = json.loads(
        (ROOT / "reports/lifecycle/final/summary.json").read_text()
    )
    version = manifest["training_run_id"]
    if version != final["selected_training_run_id"]:
        raise ValueError("Test bundle differs from the final evaluated model")

    environment = os.environ.copy()
    environment["SERVING_DIR"] = str(bundle)
    environment["PIPELINE_ROOT"] = str(ROOT)
    xml_path = folder / "full_tests.xml"

    print(f"Testing selected model: {version}", flush=True)
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "tests", "-q",
            f"--junitxml={xml_path}",
        ],
        cwd=ROOT, env=environment, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    (logs / "final_tests.log").write_text(output)
    print(output)

    counts = {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    if xml_path.exists():
        cases = list(ElementTree.parse(xml_path).getroot().iter("testcase"))
        counts["total"] = len(cases)
        for case in cases:
            if case.find("failure") is not None:
                counts["failed"] += 1
            elif case.find("error") is not None:
                counts["errors"] += 1
            elif case.find("skipped") is not None:
                counts["skipped"] += 1
            else:
                counts["passed"] += 1

    success = (
        result.returncode == 0 and counts["total"] > 0
        and counts["failed"] == 0 and counts["errors"] == 0
        and counts["skipped"] == 0
    )
    summary = {
        "status": "PASS" if success else "FAIL",
        "selected_training_run_id": version,
        "serving_bundle": str(bundle.relative_to(ROOT)),
        "counts": counts,
        "pytest_exit_code": result.returncode,
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Complete automated test suite with candidate HTTP tests and "
            "original-bundle integrity tests. No retraining or December "
            "reevaluation; this is not a load test."
        ),
    }
    (folder / "tests_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

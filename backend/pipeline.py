"""Read-only pipeline snapshot assembled from DVC and saved run evidence."""
import base64
import io
import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import yaml
from matplotlib.figure import Figure

ROOT = Path(os.environ.get("PIPELINE_ROOT", str(Path(__file__).resolve().parents[1])))


def read_json(relative):
    path = ROOT / relative
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def output_paths(stage):
    paths = []
    for section in ("outs", "metrics", "plots"):
        for entry in stage.get(section, []):
            paths.append(entry if isinstance(entry, str) else next(iter(entry)))
    return paths


def diagram(stages):
    """Draw dependencies from the real DVC configuration."""
    edges = set()
    for target, stage in stages.items():
        for dependency in stage.get("deps", []):
            for source, other in stages.items():
                if source == target:
                    continue
                if any(
                    dependency == output or dependency.startswith(output + "/")
                    for output in output_paths(other)
                ):
                    edges.add((source, target))
    levels = {}
    remaining = set(stages)
    while remaining:
        ready = sorted(
            node for node in remaining
            if all(parent in levels for parent, child in edges if child == node)
        )
        if not ready:
            raise ValueError("Pipeline dependency cycle")
        for node in ready:
            parents = [levels[p] for p, child in edges if child == node]
            levels[node] = max(parents, default=-1) + 1
            remaining.remove(node)

    positions = {}
    for level in sorted(set(levels.values())):
        nodes = sorted(n for n in levels if levels[n] == level)
        for index, node in enumerate(nodes):
            positions[node] = (index - (len(nodes) - 1) / 2, -level)

    fig = Figure(figsize=(10, max(4, len(set(levels.values())) * 1.1)))
    ax = fig.subplots()
    for source, target in sorted(edges):
        ax.annotate(
            "", xy=positions[target], xytext=positions[source],
            arrowprops={"arrowstyle": "->", "color": "#64748b",
                        "shrinkA": 25, "shrinkB": 25},
        )
    for node, position in positions.items():
        ax.text(
            *position, node.replace("_", " "), ha="center", va="center",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#e0f2fe",
                  "edgecolor": "#0369a1"},
        )
    xs, ys = zip(*positions.values())
    ax.set_xlim(min(xs) - 1, max(xs) + 1)
    ax.set_ylim(min(ys) - 0.6, max(ys) + 0.6)
    ax.axis("off")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120, bbox_inches="tight")
    return base64.b64encode(buffer.getvalue()).decode()


def test_summary(relative):
    path = ROOT / relative
    if not path.exists():
        return {"report": relative, "status": "not_available"}
    cases = list(ElementTree.parse(path).getroot().iter("testcase"))
    failed = sum(
        case.find("failure") is not None or case.find("error") is not None
        for case in cases
    )
    skipped = sum(case.find("skipped") is not None for case in cases)
    return {
        "report": relative,
        "status": "FAIL" if failed else "PASS",
        "total": len(cases),
        "passed": len(cases) - failed - skipped,
        "failed": failed,
        "skipped": skipped,
    }


def pipeline_snapshot(active_model_version=None):
    """Report saved evidence and DVC freshness; never execute pipeline stages."""
    config = yaml.safe_load((ROOT / "dvc.yaml").read_text())
    stages = {"source_data": {"outs": ["data/raw"]}, **config["stages"]}
    try:
        result = subprocess.run(
            ["dvc", "status", "--json"], cwd=ROOT,
            capture_output=True, text=True, timeout=15, check=True,
        )
        changes = json.loads(result.stdout)
        workspace_status = "changes_detected" if changes else "up_to_date"
    except (OSError, subprocess.SubprocessError, ValueError):
        workspace_status, changes = "unavailable", None

    failures = []
    missing_logs = []
    for filename in ("ingestion.log", "training.log",
                     "threshold.log", "evaluation.log"):
        path = ROOT / "logs" / filename
        if not path.exists():
            missing_logs.append(filename)
            continue
        for line in path.read_text(errors="replace").splitlines():
            if " ERROR " in line or " FAILED" in line:
                failures.append({"log": filename, "message": line[:500]})

    comparison = read_json("reports/training/comparison.json")
    lifecycle = {
        "monitoring": read_json("reports/lifecycle/monitoring.json"),
        "acceptance": read_json("reports/lifecycle/acceptance/decision.json"),
        "deployment": read_json("reports/lifecycle/deployment_verification.json"),
        "final": read_json("reports/lifecycle/final/summary.json"),
        "runner": read_json("reports/lifecycle/runner.json"),
    }
    final = lifecycle["final"]
    final_matches_active = bool(
        active_model_version and isinstance(final, dict)
        and final.get("selected_training_run_id") == active_model_version
    )
    return {
        "active_model_version": active_model_version,
        "lifecycle": lifecycle,
        "final_evaluation_matches_active_model": final_matches_active,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_status": workspace_status,
        "workspace_changes": changes,
        "stages": list(stages),
        "diagram_png_base64": diagram(stages),
        "ingestion": read_json("reports/ingestion_summary.json"),
        "models": comparison["results"] if comparison else {},
        "selected_model": comparison["selected_model"] if comparison else None,
        "test": read_json("reports/test/summary.json"),
        "tests": [
            test_summary(path) for path in (
                "reports/ingestion_tests.xml",
                "reports/threshold_tests.xml",
                "reports/monitoring_instrumentation_tests.xml",
                "reports/portable_backend_tests.xml",
                "reports/mlproject_backend_tests.xml",
                "reports/lifecycle/ci_tests.xml",
                "reports/lifecycle/runner_tests.xml",
            )
        ],
        "recorded_failures": failures[-20:],
        "missing_logs": missing_logs,
        "note": "Saved run evidence and current DVC freshness; not live task progress.",
    }

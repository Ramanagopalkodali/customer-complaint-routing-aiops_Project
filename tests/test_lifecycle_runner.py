"""Exercise orchestration branches without training or touching Docker."""
import pytest

from src.run_lifecycle import run_workflow


def scenario(trigger=True, approved=True, fail=None):
    calls = []

    def step(name, result=None):
        def invoke():
            calls.append(name)
            if name == fail:
                raise RuntimeError(f"{name} failed")
            return result
        return invoke

    callbacks = {
        "monitor": step("monitor", {
            "status": "PASS", "retraining_required": trigger,
        }),
        "train": step("train"),
        "accept": step("accept", {
            "status": "PASS",
            "checks": {"quality": approved, "coverage": True},
            "decision": "candidate_accepted" if approved else "champion_retained",
        }),
        "package": step("package"),
        "deploy": step("deploy"),
    }
    return calls, callbacks


def test_no_trigger_skips_training_and_deployment():
    calls, callbacks = scenario(trigger=False)
    result = run_workflow(**callbacks)
    assert calls == ["monitor"]
    assert result["outcome"] == "no_trigger"
    assert result["deployment_requested"] is False


def test_rejected_candidate_is_not_packaged_or_deployed():
    calls, callbacks = scenario(approved=False)
    result = run_workflow(**callbacks)
    assert calls == ["monitor", "train", "accept"]
    assert result["outcome"] == "candidate_rejected"
    assert result["deployment_requested"] is False


def test_accepted_candidate_runs_steps_in_order():
    calls, callbacks = scenario()
    result = run_workflow(**callbacks)
    assert calls == ["monitor", "train", "accept", "package", "deploy"]
    assert result["outcome"] == "candidate_deployed"


@pytest.mark.parametrize("failed_step", ["monitor", "train", "accept", "package", "deploy"])
def test_step_failure_stops_following_steps(failed_step):
    calls, callbacks = scenario(fail=failed_step)
    with pytest.raises(RuntimeError):
        run_workflow(**callbacks)
    order = ["monitor", "train", "accept", "package", "deploy"]
    assert calls == order[:order.index(failed_step) + 1]


@pytest.mark.parametrize("monitoring", [
    {"status": "FAIL", "retraining_required": True},
    {"status": "PASS", "retraining_required": "false"},
])
def test_invalid_monitoring_never_starts_training(monitoring):
    calls, callbacks = scenario()
    callbacks["monitor"] = lambda: monitoring
    with pytest.raises(ValueError):
        run_workflow(**callbacks)
    assert calls == []


def test_inconsistent_acceptance_never_deploys():
    calls, callbacks = scenario()
    callbacks["accept"] = lambda: {
        "status": "PASS",
        "checks": {"quality": False},
        "decision": "candidate_accepted",
    }
    with pytest.raises(ValueError):
        run_workflow(**callbacks)
    assert calls == ["monitor", "train"]

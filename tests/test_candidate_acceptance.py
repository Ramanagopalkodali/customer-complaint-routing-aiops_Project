"""Verify candidate acceptance and fail-closed routing checks."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.accept_candidate import acceptance_checks

ROOT = Path(__file__).resolve().parents[1]


def fixtures():
    settings = json.loads(
        (ROOT / "config/lifecycle.json").read_text()
    )["acceptance"]
    champion = {
        "macro_f1": 0.82,
        "recall": {"a": 0.8, "b": 0.8},
        "automatic_count": 1000,
        "automatic_accuracy": 0.95,
        "automatic_coverage": 0.80,
    }
    candidate = deepcopy(champion)
    candidate["macro_f1"] = 0.83
    return champion, candidate, settings


def test_qualifying_candidate_passes():
    champion, candidate, settings = fixtures()
    assert all(acceptance_checks(champion, candidate, settings).values())


@pytest.mark.parametrize("field,value,failed_check", [
    ("macro_f1", 0.824, "macro_f1_improves"),
    ("recall", {"a": 0.74, "b": 0.8}, "per_class_recall_preserved"),
    ("automatic_count", 499, "sufficient_automatic_predictions"),
    ("automatic_accuracy", 0.93, "automatic_accuracy_floor"),
    ("automatic_accuracy", 0.944, "automatic_accuracy_preserved"),
    ("automatic_coverage", 0.77, "automatic_coverage_preserved"),
    ("automatic_accuracy", None, "automatic_accuracy_floor"),
])
def test_candidate_failing_a_guardrail_is_rejected(field, value, failed_check):
    champion, candidate, settings = fixtures()
    candidate[field] = value
    checks = acceptance_checks(champion, candidate, settings)
    assert checks[failed_check] is False
    assert not all(checks.values())

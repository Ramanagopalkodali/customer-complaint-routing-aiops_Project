"""Check coverage selection, boundary handling and human-review fallback."""
import numpy as np
import pytest

from src.select_threshold import choose_threshold


def test_selects_maximum_eligible_coverage():
    policy, _ = choose_threshold(
        ["a", "a", "a", "a"], ["a", "a", "a", "b"],
        [0.90, 0.85, 0.80, 0.60],
        target_accuracy=1.0, min_auto=2,
    )
    assert policy["threshold"] == 0.61
    assert policy["automatic_count"] == 3
    assert policy["coverage"] == 0.75


def test_includes_confidence_equal_to_threshold():
    policy, _ = choose_threshold(
        ["a", "a"], ["a", "a"], [0.50, 0.50], min_auto=2
    )
    assert policy["threshold"] == 0.50
    assert policy["automatic_count"] == 2


def test_reviews_all_when_quality_target_unmet():
    policy, _ = choose_threshold(
        ["a", "a"], ["b", "b"], [0.99, 0.99], min_auto=1
    )
    assert policy["threshold"] is None
    assert policy["mode"] == "review_all"


def test_requires_minimum_automatic_count():
    policy, _ = choose_threshold(
        ["a"], ["a"], [0.99], min_auto=2
    )
    assert policy["mode"] == "review_all"


@pytest.mark.parametrize("bad", [np.nan, np.inf, -0.1, 1.1])
def test_rejects_invalid_confidence(bad):
    with pytest.raises(ValueError, match="Confidence"):
        choose_threshold(["a"], ["a"], [bad], min_auto=1)


def test_thresholds_use_predicted_categories():
    import pandas as pd
    from src.select_threshold import team_thresholds

    data = pd.DataFrame({
        "actual": ["a", "a", "b", "b"],
        "predicted": ["a", "a", "a", "b"],
        "confidence": [0.90, 0.80, 0.60, 0.90],
    })
    thresholds, _ = team_thresholds(
        data, target_accuracy=1.0, min_auto=2
    )
    assert thresholds["a"] == 0.61
    assert thresholds["b"] is None


def test_disabled_and_unknown_categories_require_review():
    from src.select_threshold import routing_mask

    result = routing_mask(
        ["a", "b", "unknown"], [0.99, 0.99, 0.99],
        {"a": 0.80, "b": None},
    )
    assert result.tolist() == [True, False, False]


def test_routing_applies_each_category_boundary():
    from src.select_threshold import routing_mask

    result = routing_mask(
        ["a", "a", "b", "b"], [0.79, 0.80, 0.89, 0.90],
        {"a": 0.80, "b": 0.90},
    )
    assert result.tolist() == [False, True, False, True]

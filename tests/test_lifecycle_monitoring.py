"""Check divergence semantics and the frozen trigger boundaries."""
import pytest

from src.monitor_lifecycle import js_divergence, trigger_reasons


def test_identical_distributions_have_zero_divergence():
    assert js_divergence([2, 8], [20, 80]) == pytest.approx(0)


def test_disjoint_distributions_have_unit_divergence():
    assert js_divergence([1, 0], [0, 1]) == pytest.approx(1)


@pytest.mark.parametrize("left,right", [
    ([0, 0], [1, 1]),
    ([-1, 2], [1, 1]),
    ([1], [1, 2]),
    ([float("nan"), 1], [1, 1]),
])
def test_invalid_distributions_are_rejected(left, right):
    with pytest.raises(ValueError):
        js_divergence(left, right)


def test_trigger_boundaries_and_independent_conditions():
    settings = {
        "js_divergence_threshold": 0.10,
        "labeled_macro_f1_floor": 0.80,
    }
    assert trigger_reasons(0.10, 0.10, 0.80, settings) == []
    assert trigger_reasons(0.11, 0, 0.9, settings) == [
        "text_length_distribution_shift"
    ]
    assert trigger_reasons(0, 0.11, 0.9, settings) == [
        "predicted_product_distribution_shift"
    ]
    assert trigger_reasons(0, 0, 0.79, settings) == [
        "labeled_macro_f1_below_floor"
    ]

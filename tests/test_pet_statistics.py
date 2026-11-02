"""Behavioral checks for annual PET series and descriptive shape statistics."""

from copy import deepcopy
from itertools import combinations
from math import fsum

import pytest

from src.core.pet_statistics import analyze_series

pytestmark = pytest.mark.unit


def series_from_changes(changes, start=2000, initial=0.0):
    points = [(start, initial)]
    for change in changes:
        points.append((points[-1][0] + 1, points[-1][1] + change))
    return points


def test_difference_sorts_without_mutating_input_and_keeps_audit_rows():
    points = [(2002, 4.0), (2000, 1.0), (2001, 2.5)]
    original = deepcopy(points)
    result = analyze_series(points)
    assert points == original
    assert result["levels"] == [
        {"year": 2000, "value": 1.0},
        {"year": 2001, "value": 2.5},
        {"year": 2002, "value": 4.0},
    ]
    assert result["changes"][0] == {
        "year": 2001, "previous_year": 2000,
        "previous_value": 1.0, "value": 2.5, "change": 1.5,
    }
    assert result["method"] == "difference"
    assert (result["n_levels"], result["n_changes"]) == (3, 2)


def test_gap_is_not_a_one_year_change_and_zero_is_valid_difference():
    result = analyze_series([(2000, 0), (2001, 2), (2003, 6), (2004, 0)])
    assert [row["change"] for row in result["changes"]] == [2.0, None, -6.0]
    assert result["n_changes"] == 2
    assert any("Lacuna" in warning for warning in result["warnings"])


def test_relative_changes_exclude_zero_baseline_without_imputation():
    result = analyze_series([(2000, 0), (2001, 2), (2002, 4), (2003, 0)], "relative")
    assert [row["change"] for row in result["changes"]] == [None, 100.0, -100.0]
    assert result["n_changes"] == 2
    assert any("zero" in warning for warning in result["warnings"])


def test_excess_kurtosis_matches_published_excel_kurt_example():
    result = analyze_series(series_from_changes([3, 4, 5, 2, 3, 4, 5, 6, 4, 7]))
    assert result["excess_kurtosis"] == pytest.approx(-0.151799637, abs=1e-9)
    assert result["pearson_kurtosis"] == pytest.approx(3 - 0.151799637, abs=1e-9)
    assert any("heurístico" in warning for warning in result["warnings"])


@pytest.mark.parametrize("changes, expected_l, expected_excess", [
    ([1, 2, 3, 4], 0.0, -1.2),
    ([0, 0, 0, 1], 1.0, 4.0),
])
def test_known_sample_shape(changes, expected_l, expected_excess):
    result = analyze_series(series_from_changes(changes))
    assert result["l_kurtosis"] == pytest.approx(expected_l, abs=1e-12)
    assert result["excess_kurtosis"] == pytest.approx(expected_excess, abs=1e-12)


def test_l_kurtosis_matches_independent_all_subsamples_definition():
    changes = [-3, -1, 0, 2, 2, 8, 16]
    ordered = sorted(changes)
    l2 = fsum((b - a) / 2 for a, b in combinations(ordered, 2)) / 21
    l4 = fsum((d - 3 * c + 3 * b - a) / 4
              for a, b, c, d in combinations(ordered, 4)) / 35
    result = analyze_series(series_from_changes(changes, initial=10))
    assert result["l_kurtosis"] == pytest.approx(l4 / l2, abs=1e-12)


@pytest.mark.parametrize("points", [[], [(2000, 1)], [(2000, 1), (2001, 2)]])
def test_fewer_than_four_changes_has_no_shape_estimates(points):
    result = analyze_series(points)
    assert result["pearson_kurtosis"] is None
    assert result["excess_kurtosis"] is None
    assert result["l_kurtosis"] is None
    assert any("4 variações" in warning for warning in result["warnings"])


def test_constant_changes_have_undefined_kurtosis():
    result = analyze_series(series_from_changes([2] * 25))
    assert result["n_changes"] == 25
    assert result["excess_kurtosis"] is None
    assert result["l_kurtosis"] is None
    assert any("constantes" in warning for warning in result["warnings"])


def test_all_zero_changes_have_undefined_kurtosis():
    result = analyze_series(series_from_changes([0] * 4))
    assert result["pearson_kurtosis"] is None
    assert result["l_kurtosis"] is None
    assert any("constantes" in warning for warning in result["warnings"])


def test_large_finite_levels_do_not_overflow_fourth_powers():
    small = analyze_series([(2000, 1), (2001, 4), (2002, 2), (2003, 8), (2004, 3)])
    large = analyze_series([(2000, 1e307), (2001, 4e307), (2002, 2e307),
                            (2003, 8e307), (2004, 3e307)])
    assert large["excess_kurtosis"] == pytest.approx(small["excess_kurtosis"])
    assert large["l_kurtosis"] == pytest.approx(small["l_kurtosis"])


def test_relative_change_avoids_intermediate_overflow():
    result = analyze_series([(2000, 5e307), (2001, 1e308)], "relative")
    assert result["changes"][0]["change"] == pytest.approx(100)


def test_unrepresentable_relative_change_is_excluded_with_warning():
    result = analyze_series([(2000, 1e-308), (2001, 1e308)], "relative")
    assert result["changes"][0]["change"] is None
    assert result["n_changes"] == 0
    assert any("finita" in warning for warning in result["warnings"])


@pytest.mark.parametrize("points", [
    [(2000, 1), (2000, 2)], [(0, 1)], [(10000, 1)], [(2000.0, 1)],
    [(True, 1)], [(2000, -1)], [(2000, float("nan"))],
    [(2000, float("inf"))], [(2000, "1")], [(2000, True)],
    [(2000,)], None, 42, [(2000, 10 ** 400)],
])
def test_invalid_levels_are_rejected(points):
    with pytest.raises(ValueError):
        analyze_series(points)


def test_unknown_change_method_is_rejected():
    with pytest.raises(ValueError, match="Método"):
        analyze_series([(2000, 1)], "log")

import numpy as np
import pytest
from scipy.stats import t

from change_ci.estimation import confidence_interval, effective_sample_size, find_range


def test_effective_sample_size_matches_equation():
    n = 100
    moran = np.array([0.6, 0.3, 0.1])
    counts = n * np.array([8, 16, 24])
    assert effective_sample_size(moran, counts, n, 4) == pytest.approx(n / 13)


@pytest.mark.parametrize(
    ("values", "tau", "expected"),
    [([0.01, 0.2], 0.05, 1), ([0.2, 0.1], 0.05, None), ([0.05, 0.01], 0.05, 2)],
)
def test_find_range_edge_cases(values, tau, expected):
    assert find_range(np.array(values), tau) == expected


def test_confidence_interval_matches_scipy():
    result = confidence_interval(2.0, 3.0, 25.0, 0.05)
    critical = t.ppf(0.975, 24)
    se = 3 / 5
    assert result.se == pytest.approx(se)
    assert result.lower == pytest.approx(2 - critical * se)
    assert result.upper == pytest.approx(2 + critical * se)

import numpy as np
import pytest

from change_ci.engines import BruteForceEngine, FFTEngine, PySALEngine


@pytest.mark.parametrize("with_nan", [False, True])
def test_fft_and_brute_force_agree(with_nan):
    rng = np.random.default_rng(42)
    values = rng.normal(size=(11, 13))
    if with_nan:
        values[2:5, 4:7] = np.nan
        values[8, 1] = np.nan
    fft = FFTEngine().compute(values, 4)
    brute = BruteForceEngine().compute(values, 4)
    np.testing.assert_array_equal(fft.pair_counts, brute.pair_counts)
    np.testing.assert_allclose(fft.moran_i, brute.moran_i, rtol=1e-12, atol=1e-12)


def test_lag_one_pair_count_is_queen_count():
    values = np.ones((4, 5))
    values[0, 0] = 2
    result = BruteForceEngine().compute(values, 1)
    expected = 2 * (4 * (5 - 1) + (4 - 1) * 5 + 2 * (4 - 1) * (5 - 1))
    assert result.pair_counts[0] == expected


def test_pysal_is_optional():
    pytest.importorskip("libpysal")
    pytest.importorskip("esda")
    values = np.arange(49, dtype=float).reshape(7, 7)
    result = PySALEngine().compute(values, 2)
    assert result.pair_counts.shape == (2,)

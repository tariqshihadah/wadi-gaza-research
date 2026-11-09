import numpy as np
import pytest

from change_ci.engines import FFTEngine as ChangeFFTEngine
from change_ci.estimation import confidence_interval as change_confidence_interval
from spatial_ci import FFTEngine, MoranCorrelogram, confidence_interval


def test_change_api_reexports_shared_spatial_core():
    values = np.random.default_rng(42).normal(size=(9, 11))
    shared = FFTEngine().compute(values, 3)
    legacy = ChangeFFTEngine().compute(values, 3)
    np.testing.assert_array_equal(shared.pair_counts, legacy.pair_counts)
    np.testing.assert_allclose(shared.moran_i, legacy.moran_i)
    assert confidence_interval(2, 1, 25, 0.05) == change_confidence_interval(
        2, 1, 25, 0.05
    )


def test_shared_correlogram_carries_metadata_rows():
    values = np.random.default_rng(7).normal(size=(9, 9))
    correlogram = MoranCorrelogram.from_values(values, FFTEngine(), 3)
    frame = correlogram.to_frame({"study_area": "Area", "year": 2024})
    assert correlogram.n == values.size
    assert list(frame.columns) == [
        "study_area", "year", "lag", "moran_i", "pair_count"
    ]
    assert frame["year"].eq(2024).all()


def test_shared_engine_rejects_constant_raster():
    with pytest.raises(ValueError, match="constant raster"):
        FFTEngine().compute(np.ones((4, 4)), 1)

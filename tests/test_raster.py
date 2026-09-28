import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from change_ci.discovery import PairSpec
from change_ci.raster import RasterPair


def _write(path, data, *, transform=None, descriptions=("NDVI",)):
    with rasterio.open(
        path, "w", driver="GTiff", height=data.shape[1], width=data.shape[2],
        count=data.shape[0], dtype="float32", crs="EPSG:32636",
        transform=transform or from_origin(0, 40, 10, 10), nodata=-9999,
    ) as dst:
        dst.write(data.astype("float32"))
        for index, description in enumerate(descriptions, 1):
            dst.set_band_description(index, description)


def test_ndvi_difference_and_intersection_mask(tmp_path):
    earlier = np.array([[[1, 2], [3, -9999]]], dtype=float)
    later = np.array([[[2, 4], [-9999, 8]]], dtype=float)
    earlier_path = tmp_path / "earlier.tif"
    later_path = tmp_path / "later.tif"
    _write(earlier_path, earlier)
    _write(later_path, later)
    spec = PairSpec("Area", "09", 2023, 2024, earlier_path, later_path)
    pair = RasterPair(spec)
    np.testing.assert_allclose(pair.values, [[1, 2]], equal_nan=True)
    assert pair.n == 2
    assert pair.mean == pytest.approx(1.5)


def test_mismatched_grids_raise(tmp_path):
    data = np.ones((1, 2, 2))
    earlier_path = tmp_path / "earlier.tif"
    later_path = tmp_path / "later.tif"
    _write(earlier_path, data)
    _write(later_path, data, transform=from_origin(1, 40, 10, 10))
    spec = PairSpec("Area", "09", 2023, 2024, earlier_path, later_path)
    with pytest.raises(ValueError, match="mismatched"):
        RasterPair(spec)

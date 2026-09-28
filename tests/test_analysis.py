import numpy as np
import rasterio

from change_ci.analysis import ChangeCIAnalysis
from change_ci.config import AnalysisConfig
from change_ci.discovery import PairSpec


def _write(path, data):
    with rasterio.open(
        path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
        count=1, dtype="float32", crs="EPSG:32636", nodata=-9999,
        transform=rasterio.transform.from_origin(0, 80, 10, 10),
    ) as dst:
        dst.write(data.astype("float32"), 1)
        dst.set_band_description(1, "NDVI")


def test_analysis_returns_sensitivity_and_correlogram_rows(tmp_path):
    rng = np.random.default_rng(4)
    earlier = rng.normal(size=(8, 8))
    later = earlier + 0.2 + rng.normal(scale=0.05, size=(8, 8))
    earlier_path = tmp_path / "earlier.tif"
    later_path = tmp_path / "later.tif"
    _write(earlier_path, earlier)
    _write(later_path, later)
    spec = PairSpec("Area", "09", 2023, 2024, earlier_path, later_path)
    config = AnalysisConfig(
        tmp_path, tmp_path / "out", months=("09",), year_range=(2023, 2024),
        tau_sensitivity=(0.02, 0.05),
    )
    results, correlograms = ChangeCIAnalysis(config).run([spec])
    assert len(results) == 2
    assert set(results["tau"]) == {0.02, 0.05}
    assert len(correlograms) == 2
    assert results["error"].eq("").all()

import json

import numpy as np
import pandas as pd
import rasterio

from change_ci.analysis import ChangeCIAnalysis
from change_ci.discovery import PairSpec


def _write(path, data, band_names=("NDVI",)):
    data = np.asarray(data)
    if data.ndim == 2:
        data = data[np.newaxis, ...]
    with rasterio.open(
        path, "w", driver="GTiff", height=data.shape[1], width=data.shape[2],
        count=data.shape[0], dtype="float32", crs="EPSG:32636", nodata=-9999,
        transform=rasterio.transform.from_origin(0, 80, 10, 10),
    ) as dst:
        dst.write(data.astype("float32"))
        for index, band_name in enumerate(band_names, start=1):
            dst.set_band_description(index, band_name)


def test_analysis_returns_sensitivity_and_correlogram_rows(
    tmp_path, analysis_config_factory
):
    rng = np.random.default_rng(4)
    earlier = rng.normal(size=(8, 8))
    later = earlier + 0.2 + rng.normal(scale=0.05, size=(8, 8))
    earlier_path = tmp_path / "earlier.tif"
    later_path = tmp_path / "later.tif"
    _write(earlier_path, earlier)
    _write(later_path, later)
    spec = PairSpec("Area", "09", 2023, 2024, earlier_path, later_path)
    config = analysis_config_factory(
        tmp_path,
        tmp_path / "out",
        months=("09",),
        year_range=(2023, 2024),
        index_bands=("NDVI",),
        tau_sensitivity=(0.02, 0.05),
    )
    results, correlograms = ChangeCIAnalysis(config).run([spec])
    assert len(results) == 2
    assert set(results["tau"]) == {0.02, 0.05}
    assert len(correlograms) == 2
    assert results["error"].eq("").all()
    assert results["index"].eq("NDVI").all()
    assert correlograms["index"].eq("NDVI").all()


def test_analysis_runs_and_saves_each_configured_index(tmp_path, analysis_config_factory):
    rng = np.random.default_rng(9)
    earlier = np.stack((rng.normal(size=(8, 8)), rng.normal(size=(8, 8))))
    later = earlier + np.stack((
        0.2 + rng.normal(scale=0.05, size=(8, 8)),
        -0.1 + rng.normal(scale=0.05, size=(8, 8)),
    ))
    earlier_path = tmp_path / "earlier.tif"
    later_path = tmp_path / "later.tif"
    _write(earlier_path, earlier, ("NDVI", "GNDVI"))
    _write(later_path, later, ("NDVI", "GNDVI"))
    spec = PairSpec("Area", "09", 2023, 2024, earlier_path, later_path)
    config = analysis_config_factory(
        tmp_path,
        tmp_path / "out",
        months=("09",),
        year_range=(2023, 2024),
        index_bands=("NDVI", "GNDVI"),
        tau_sensitivity=(0.05,),
    )

    analysis = ChangeCIAnalysis(config)
    results, correlograms = analysis.run([spec])
    analysis.save(results, correlograms)

    assert set(results["index"]) == {"NDVI", "GNDVI"}
    assert set(correlograms["index"]) == {"NDVI", "GNDVI"}
    for index in ("NDVI", "GNDVI"):
        output_dir = config.output_dir / index
        saved_results = pd.read_csv(output_dir / "results.csv")
        saved_correlograms = pd.read_csv(output_dir / "correlograms.csv")
        snapshot = json.loads((output_dir / "config.json").read_text())
        assert saved_results["index"].eq(index).all()
        assert saved_correlograms["index"].eq(index).all()
        assert snapshot["index_band"] == index

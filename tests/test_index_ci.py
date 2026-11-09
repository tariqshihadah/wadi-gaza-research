import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from index_ci import IndexCIAnalysis, RasterObservation, discover_observations
from index_ci.discovery import IndexObservationSpec


def _write(path: Path, data: np.ndarray, *, transform=None) -> None:
    with rasterio.open(
        path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
        count=1, dtype="float32", crs="EPSG:32636", nodata=-9999,
        transform=transform or from_origin(0, 80, 10, 10),
    ) as dst:
        dst.write(data.astype("float32"), 1)
        dst.set_band_description(1, "NDVI")


def test_index_config_loads_separate_canonical_yaml():
    root = Path(__file__).resolve().parents[1]
    from index_ci import IndexAnalysisConfig

    config = IndexAnalysisConfig.from_yaml(
        root / "configs" / "index_ci.yaml", project_root=root
    )
    assert config.data_root == root / "outputs" / "composites"
    assert config.output_dir == root / "outputs" / "index_ci"
    assert config.year_range == (2019, 2025)
    assert config.index_bands == ("NDVI", "GNDVI", "SAVI", "NDRE")


def test_discovery_returns_observations_not_year_pairs(
    tmp_path, caplog, index_config_factory
):
    area = tmp_path / "Area"
    area.mkdir()
    for year in (2023, 2024):
        (area / f"Area_{year}-09.tif").touch()
    (area / "not_a_raster_name.tif").touch()
    config = index_config_factory(
        tmp_path, tmp_path / "out", months=("09",), year_range=(2023, 2024)
    )
    with caplog.at_level(logging.WARNING):
        observations = discover_observations(config)
    assert [observation.year for observation in observations] == [2023, 2024]
    assert all(observation.month == "09" for observation in observations)
    assert "unexpected name" in caplog.text


def test_analysis_uses_common_support_and_saves_observation_results(
    tmp_path, index_config_factory
):
    rng = np.random.default_rng(11)
    first = rng.normal(0.35, 0.08, size=(12, 12))
    second = rng.normal(0.42, 0.08, size=(12, 12))
    first[0, 0] = -9999
    second[0, 1] = -9999
    first_path = tmp_path / "Area_2023-09.tif"
    second_path = tmp_path / "Area_2024-09.tif"
    _write(first_path, first)
    _write(second_path, second)
    config = index_config_factory(
        tmp_path,
        tmp_path / "out",
        months=("09",),
        year_range=(2023, 2024),
        index_bands=("NDVI",),
        tau_sensitivity=(0.05,),
        max_lag_fraction=0.25,
    )
    specs = discover_observations(config)
    results, correlograms = IndexCIAnalysis(config).run(specs)

    assert len(results) == 2
    assert results["year"].tolist() == [2023, 2024]
    assert results["n"].tolist() == [142, 142]
    common = (
        np.isfinite(first) & np.isfinite(second)
        & (first != -9999) & (second != -9999)
    )
    assert results["mean_index"].iloc[0] == pytest.approx(
        np.mean(first[common])
    )
    assert "year_start" not in results
    assert "mean_change" not in results
    assert results["error"].eq("").all()
    assert set(correlograms["year"]) == {2023, 2024}
    assert set(correlograms["index"]) == {"NDVI"}

    analysis = IndexCIAnalysis(config)
    analysis.save(results, correlograms)
    output = config.output_dir / "NDVI"
    assert (output / "results.csv").exists()
    saved_results = pd.read_csv(output / "results.csv")
    saved_config = json.loads((output / "config.json").read_text())
    assert saved_results["year"].tolist() == [2023, 2024]
    assert saved_config["index_band"] == "NDVI"


def test_raster_observation_reads_named_band_and_mask(tmp_path):
    values = np.arange(64, dtype=float).reshape(8, 8)
    values[0, 0] = -9999
    path = tmp_path / "Area_2023-09.tif"
    _write(path, values)
    observation = RasterObservation(
        IndexObservationSpec("Area", 2023, "09", path), "NDVI"
    )
    assert observation.n == 63
    assert observation.mean == pytest.approx(np.mean(values[values != -9999]))
    assert observation.grid_signature[2] == (8, 8)


def test_analysis_records_grid_mismatch(tmp_path, index_config_factory):
    values = np.random.default_rng(12).normal(size=(8, 8))
    first = tmp_path / "Area_2023-09.tif"
    second = tmp_path / "Area_2024-09.tif"
    _write(first, values)
    _write(second, values, transform=from_origin(1, 80, 10, 10))
    config = index_config_factory(
        tmp_path, tmp_path / "out", months=("09",),
        year_range=(2023, 2024), index_bands=("NDVI",),
        tau_sensitivity=(0.05,),
    )
    results, _ = IndexCIAnalysis(config).run(discover_observations(config))
    assert len(results) == 2
    assert results["error"].str.contains("mismatched grids").all()

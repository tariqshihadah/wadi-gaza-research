import json
import zipfile
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from cds_pull.cells import assign_cells, grid_cells
from cds_pull.checks import check_region_grid, check_site_cells, missing_days, run_checks
from cds_pull.config import ClimateConfig
from cds_pull.download import ClimateDownloader, build_request
from cds_pull.io import cell_table, load_daily, open_region

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ClimateConfig.from_yaml(ROOT / "configs" / "climate.yaml", project_root=ROOT)
SMALL = replace(CONFIG, region_lat=(31.4, 31.5), region_lon=(34.4, 34.5))


def _write_region_zip(path: Path, lats, lons, start: str, hours: int, sea=()):
    """Write a zip laid out like the CDS time-series NetCDF response.

    Coordinates carry float noise, as in real files. Points in ``sea`` hold only NaN.
    """
    times = pd.date_range(start, periods=hours, freq="h")
    shape = (hours, len(lats), len(lons))
    t2m = np.full(shape, 293.15, dtype="float32")
    tp = np.full(shape, 0.0001, dtype="float32")
    tp[2] = -1.49e-08
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            if (lat, lon) in sea:
                t2m[:, i, j] = np.nan
                tp[:, i, j] = np.nan
    coords = {"valid_time": times, "latitude": np.array(lats) + 1e-12, "longitude": np.array(lons) + 2e-13}
    dims = ("valid_time", "latitude", "longitude")
    folder = path.parent / "_build"
    folder.mkdir(exist_ok=True)
    xr.Dataset({"t2m": (dims, t2m)}, coords=coords).to_netcdf(folder / "t.nc")
    xr.Dataset({"tp": (dims, tp)}, coords=coords).to_netcdf(folder / "p.nc")
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.write(folder / "t.nc", "reanalysis-era5-land-timeseries-sfc-2m-temperatureabc.nc")
        bundle.write(folder / "p.nc", "reanalysis-era5-land-timeseries-sfc-pressure-precipitationxyz.nc")


class _FakeResult:
    def __init__(self, source: Path):
        self.source = source

    def download(self, target: str) -> None:
        Path(target).write_bytes(self.source.read_bytes())


class _FakeClient:
    def __init__(self, source: Path):
        self.source = source
        self.calls = []

    def retrieve(self, dataset, request):
        self.calls.append((dataset, request))
        return _FakeResult(self.source)


def test_build_request_pads_region_by_half_a_cell():
    assert build_request(CONFIG) == {
        "variable": ["2m_temperature", "total_precipitation"],
        "area": [32.05, 34.15, 31.15, 34.85],
        "date": ["1990-10-01/2026-01-01"],
        "data_format": "netcdf",
    }


def test_downloader_caches_and_records_manifest(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    _write_region_zip(source_dir / "region.zip", [31.4, 31.5], [34.4, 34.5], "2020-01-01", 49,
                      sea={(31.5, 34.4)})
    config = replace(SMALL, output_dir=tmp_path / "climate")
    client = _FakeClient(source_dir / "region.zip")
    downloader = ClimateDownloader(config, client=client)

    record = downloader.download()
    downloader.download()

    assert len(client.calls) == 1
    assert (record["n_cells"], record["n_cells_with_data"]) == (4, 3)
    assert record["raw_path"] == "raw/region/region.zip"
    assert len(record["sha256"]) == 64
    assert json.loads(record["request"])["area"] == [31.55, 34.35, 31.35, 34.55]
    manifest = pd.read_csv(config.output_dir / "download_manifest.csv")
    assert manifest.loc[0, "sha256"] == record["sha256"]


def test_downloader_rejects_grid_that_does_not_match_region(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    _write_region_zip(source_dir / "region.zip", [31.4], [34.4, 34.5], "2020-01-01", 25)
    config = replace(SMALL, output_dir=tmp_path / "climate")

    with pytest.raises(ValueError, match="missing"):
        ClimateDownloader(config, client=_FakeClient(source_dir / "region.zip")).download()


def test_region_cells_daily_and_checks(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_region_zip(raw / "region.zip", [31.4, 31.5], [34.4, 34.5], "2020-01-01", 49, sea={(31.5, 34.4)})
    zipfile.ZipFile(raw / "region.zip").extractall(raw)

    region = open_region(raw)
    cells = cell_table(region)

    assert list(cells["cell_id"]) == ["N31.4_E34.4", "N31.4_E34.5", "N31.5_E34.4", "N31.5_E34.5"]
    assert list(cells["has_data"]) == [True, True, False, True]

    data_cells = cells.loc[cells["has_data"]]
    daily = load_daily(region, data_cells, date(2020, 1, 1), date(2020, 1, 3))

    assert len(daily) == 9
    first = daily.loc[(daily["cell_id"] == "N31.4_E34.4") & (daily["date"] == date(2020, 1, 1))].iloc[0]
    assert first["precip_mm"] == pytest.approx(2.3, abs=1e-6)
    assert first["precip_clamped"] == 1
    assert first["t2m_mean_24h_c"] == pytest.approx(20.0, abs=1e-4)
    gaps = missing_days(daily)
    assert set(gaps["date"]) == {date(2020, 1, 3)}

    site_cells = pd.DataFrame({
        "site": ["A", "B"], "centroid_cell_id": ["N31.4_E34.4", "N31.5_E34.4"],
        "cell_id": ["N31.4_E34.4", "N31.5_E34.4"], "assignment": ["centroid", "centroid"],
    })
    grid = check_region_grid(cells, SMALL)[0]
    assert grid["passed"] and grid["detail"] == "4 grid points, 3 with data"
    site_checks = {row["scope"]: row["passed"] for row in check_site_cells(site_cells, cells)}
    assert site_checks == {"A": True, "B": False}

    normals = pd.DataFrame({"incomplete_flag": [False]})
    summary = pd.DataFrame({"month_incomplete": [False] * 56})
    checks = run_checks(daily, normals, summary, site_cells, cells, SMALL).set_index(["check", "scope"])
    assert not checks.loc[("days_complete", "N31.4_E34.4"), "passed"]
    assert checks.loc[("summary_row_count", "all"), "passed"]


def test_manual_assignment_is_reported_in_site_check():
    cells = grid_cells((31.9, 31.9), (34.7, 34.8)).assign(has_data=[False, True])
    site_cells = pd.DataFrame({
        "site": ["HolotPalmahim"], "centroid_cell_id": ["N31.9_E34.7"],
        "cell_id": ["N31.9_E34.8"], "assignment": ["manual"],
    })

    row = check_site_cells(site_cells, cells)[0]

    assert row["passed"]
    assert row["detail"] == "N31.9_E34.8 (manual, centroid cell N31.9_E34.7)"

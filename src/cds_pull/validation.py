"""Validate the time-series product against the standard ERA5-Land dataset.

The standard ``reanalysis-era5-land`` dataset stores precipitation accumulated
from 00 UTC, so the value stamped ``D+1 00:00`` is the full total for day
``D``. Comparing it with daily totals derived from the period-ending hourly
time series checks the day boundary. The monthly total and mean temperature
for the same month form the spot-check guarding against the time-series
entry's experimental status.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import xarray as xr

from .checks import CHECK_COLUMNS
from .config import ClimateConfig
from .daily import KELVIN_OFFSET, M_TO_MM
from .download import sha256

logger = logging.getLogger(__name__)

STANDARD_DATASET = "reanalysis-era5-land"
RAINY_DAY_MM = 1.0


def standard_request(cell_lat: float, cell_lon: float, year: int, month: int) -> dict[str, Any]:
    """Return a standard-dataset request for one grid point, a month and the next.

    The following month is included so that the 00:00 value closing the last
    day of ``month`` is available. December is not supported because the
    request form takes a single list of years.
    """
    if not 1 <= month <= 11:
        raise ValueError("month must be January through November")
    return {
        "variable": ["2m_temperature", "total_precipitation"],
        "year": str(year),
        "month": [f"{month:02d}", f"{month + 1:02d}"],
        "day": [f"{d:02d}" for d in range(1, 32)],
        "time": [f"{h:02d}:00" for h in range(24)],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [cell_lat, cell_lon, cell_lat, cell_lon],
    }


def fetch_standard(
    config: ClimateConfig,
    cell_id: str,
    cell_lat: float,
    cell_lon: float,
    year: int,
    month: int,
    *,
    client: Any | None = None,
    force: bool = False,
) -> Path:
    """Download (or reuse) the standard-dataset file for one cell and month."""
    folder = config.output_dir / "raw" / "validation"
    path = folder / f"{cell_id}_{year}-{month:02d}.nc"
    if path.exists() and not force:
        return path
    folder.mkdir(parents=True, exist_ok=True)
    if client is None:
        import cdsapi

        client = cdsapi.Client()
    request = standard_request(cell_lat, cell_lon, year, month)
    client.retrieve(STANDARD_DATASET, request).download(str(path))
    sidecar = {
        "cell_id": cell_id,
        "dataset": STANDARD_DATASET,
        "request": request,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }
    path.with_suffix(".json").write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return path


def read_standard(path: Path) -> pd.DataFrame:
    """Return ``time``, ``tp_accum_m`` and ``t2m_k`` from a single-point NetCDF file."""
    with xr.open_dataset(path) as ds:
        point = ds[["tp", "t2m"]].isel(latitude=0, longitude=0)
        frame = point.to_dataframe()[["tp", "t2m"]].reset_index()
    return frame.rename(columns={"valid_time": "time", "tp": "tp_accum_m", "t2m": "t2m_k"})


def standard_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """Return daily precipitation (from the 00:00 D+1 value) and temperature by date."""
    times = pd.to_datetime(hourly["time"])
    closing = hourly.loc[times.dt.hour == 0]
    precip = pd.Series(
        closing["tp_accum_m"].to_numpy() * M_TO_MM,
        index=(pd.to_datetime(closing["time"]) - pd.Timedelta(days=1)).dt.date,
    )
    celsius = (hourly["t2m_k"] - KELVIN_OFFSET).groupby(times.dt.date)
    counts = celsius.count()
    result = pd.DataFrame(
        {
            "std_precip_mm": precip,
            "std_t2m_mean_24h_c": celsius.mean().where(counts == 24),
            "std_t2m_midrange_c": ((celsius.max() + celsius.min()) / 2).where(counts == 24),
        }
    )
    result.index.name = "date"
    return result


def compare_daily(daily: pd.DataFrame, standard: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """Join time-series daily values for one cell with standard daily values for a month."""
    dates = pd.to_datetime(daily["date"])
    ts = daily.loc[(dates.dt.year == year) & (dates.dt.month == month)].copy()
    ts["date"] = pd.to_datetime(ts["date"]).dt.date
    merged = ts.set_index("date")[["precip_mm", "t2m_mean_24h_c", "t2m_midrange_c"]].join(
        standard, how="left"
    )
    merged["precip_diff_mm"] = merged["precip_mm"] - merged["std_precip_mm"]
    merged["t2m_mean_24h_diff_c"] = merged["t2m_mean_24h_c"] - merged["std_t2m_mean_24h_c"]
    merged["t2m_midrange_diff_c"] = merged["t2m_midrange_c"] - merged["std_t2m_midrange_c"]
    return merged.reset_index()


def validation_checks(
    comparison: pd.DataFrame,
    cell_id: str,
    *,
    precip_tol_mm: float = 0.01,
    temp_tol_c: float = 0.01,
) -> pd.DataFrame:
    """Return day-boundary and monthly spot-check rows in the ``checks.csv`` layout."""
    scope = f"{cell_id} {pd.to_datetime(comparison['date']).min():%Y-%m}"
    rainy = comparison.loc[comparison["std_precip_mm"] >= RAINY_DAY_MM]
    max_day = rainy["precip_diff_mm"].abs().max() if len(rainy) else float("nan")
    month_ts = comparison["precip_mm"].sum(min_count=len(comparison))
    month_std = comparison["std_precip_mm"].sum(min_count=len(comparison))
    t_ts = comparison["t2m_mean_24h_c"].mean()
    t_std = comparison["std_t2m_mean_24h_c"].mean()
    rows = [
        {
            "check": "validation_day_boundary",
            "scope": scope,
            "passed": bool(len(rainy) > 0 and max_day <= precip_tol_mm),
            "detail": f"{len(rainy)} rainy days; max |diff| {max_day:.5f} mm",
        },
        {
            "check": "validation_monthly_precip",
            "scope": scope,
            "passed": bool(abs(month_ts - month_std) <= precip_tol_mm * len(comparison)),
            "detail": f"time series {month_ts:.2f} mm; standard {month_std:.2f} mm",
        },
        {
            "check": "validation_monthly_t2m",
            "scope": scope,
            "passed": bool(abs(t_ts - t_std) <= temp_tol_c),
            "detail": f"time series {t_ts:.3f} C; standard {t_std:.3f} C",
        },
    ]
    return pd.DataFrame(rows, columns=CHECK_COLUMNS)

"""Read the raw ERA5-Land regional download.

The CDS returns a zip holding one NetCDF file per parameter group, for example
``...-sfc-2m-temperature<suffix>.nc`` (variable ``t2m``, kelvin) and
``...-sfc-pressure-precipitation<suffix>.nc`` (variable ``tp``, metres per
hour, period-ending). Both have dimensions ``valid_time`` (UTC),
``latitude`` and ``longitude``. Grid points that ERA5-Land treats as sea are
present but hold only missing values.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from .cells import cell_id
from .daily import DAILY_COLUMNS, derive_daily

VALUE_VARIABLES = {"tp": "precip_m", "t2m": "t2m_k"}
COORD_TOLERANCE_DEG = 1e-3


def open_region(raw_dir: Path) -> xr.Dataset:
    """Return one dataset holding ``precip_m`` and ``t2m_k`` from the raw NetCDF files."""
    found: dict[str, xr.DataArray] = {}
    for path in sorted(raw_dir.glob("*.nc")):
        with xr.open_dataset(path) as ds:
            for name, label in VALUE_VARIABLES.items():
                if name in ds.data_vars:
                    if label in found:
                        raise ValueError(f"More than one file holds '{name}' in {raw_dir}")
                    found[label] = ds[name].load()
    missing = set(VALUE_VARIABLES.values()) - found.keys()
    if missing:
        raise ValueError(f"Missing variable(s) {sorted(missing)} in {raw_dir}")
    region = xr.Dataset(found)
    return region.assign_coords(
        latitude=np.round(region["latitude"].values, 1),
        longitude=np.round(region["longitude"].values, 1),
    )


def cell_table(region: xr.Dataset) -> pd.DataFrame:
    """Return one row per grid point with ``has_data`` (any value in both variables)."""
    has_data = (
        region["precip_m"].notnull().any("valid_time") & region["t2m_k"].notnull().any("valid_time")
    )
    rows = [
        (cell_id(float(lat), float(lon)), float(lat), float(lon),
         bool(has_data.sel(latitude=lat, longitude=lon)))
        for lat in region["latitude"].values
        for lon in region["longitude"].values
    ]
    table = pd.DataFrame(rows, columns=["cell_id", "cell_lat", "cell_lon", "has_data"])
    return table.sort_values(["cell_lat", "cell_lon"]).reset_index(drop=True)


def hourly_for_cell(region: xr.Dataset, cell_lat: float, cell_lon: float) -> pd.DataFrame:
    """Return ``time``, ``precip_m`` and ``t2m_k`` for one grid point."""
    point = region.sel(latitude=cell_lat, longitude=cell_lon, method="nearest",
                       tolerance=COORD_TOLERANCE_DEG)
    return pd.DataFrame(
        {
            "time": point["valid_time"].values,
            "precip_m": point["precip_m"].values.astype("float64"),
            "t2m_k": point["t2m_k"].values.astype("float64"),
        }
    )


def load_daily(region: xr.Dataset, cells: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Return the daily table for every cell in ``cells``.

    Parameters
    ----------
    region : xarray.Dataset
        Output of :func:`open_region`.
    cells : pandas.DataFrame
        Columns ``cell_id``, ``cell_lat`` and ``cell_lon``; duplicates are dropped.
    start, end : datetime.date
        Inclusive range of UTC days to return.
    """
    frames = []
    unique = cells[["cell_id", "cell_lat", "cell_lon"]].drop_duplicates("cell_id")
    for cid, cell_lat, cell_lon in unique.itertuples(index=False):
        daily = derive_daily(hourly_for_cell(region, cell_lat, cell_lon), start, end)
        daily.insert(0, "cell_id", cid)
        frames.append(daily)
    return pd.concat(frames, ignore_index=True)[["cell_id", *DAILY_COLUMNS]]

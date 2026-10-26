"""Derive daily UTC values from ERA5-Land hourly time series.

Hourly inputs are period-ending: the value stamped ``D+1 00:00`` covers the
last hour of day ``D``. Daily precipitation therefore sums the 24 values
stamped ``D 01:00`` through ``D+1 00:00``. Daily temperature uses the 24
instantaneous values stamped ``D 00:00`` through ``D 23:00``.

A day is complete for a variable only when all 24 hourly values are present.
Incomplete days keep their row and hour count, but their daily value is left
blank so that partial sums or means never reach the monthly summaries.
"""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

HOURS_PER_DAY = 24
KELVIN_OFFSET = 273.15
M_TO_MM = 1000.0

DAILY_COLUMNS = [
    "date",
    "precip_mm",
    "t2m_mean_24h_c",
    "t2m_midrange_c",
    "precip_hours",
    "t2m_hours",
    "precip_clamped",
    "day_complete",
]


def daily_precip(hourly: pd.DataFrame) -> pd.DataFrame:
    """Return daily precipitation in mm, indexed by UTC date.

    Parameters
    ----------
    hourly : pandas.DataFrame
        Columns ``time`` (naive UTC timestamps) and ``precip_m`` (hourly
        precipitation in metres, period-ending).

    Returns
    -------
    pandas.DataFrame
        Columns ``precip_mm``, ``precip_hours`` and ``precip_clamped`` (number
        of negative hourly values set to zero).
    """
    _check_times(hourly)
    values = hourly["precip_m"].astype(float)
    negative = values < 0
    clamped = values.where(~negative, 0.0)
    day = (pd.to_datetime(hourly["time"]) - pd.Timedelta(hours=1)).dt.date
    frame = pd.DataFrame({"date": day, "precip_m": clamped, "negative": negative})
    grouped = frame.groupby("date")
    result = pd.DataFrame(
        {
            "precip_mm": grouped["precip_m"].sum(min_count=1) * M_TO_MM,
            "precip_hours": grouped["precip_m"].count(),
            "precip_clamped": grouped["negative"].sum(),
        }
    )
    result.loc[result["precip_hours"] < HOURS_PER_DAY, "precip_mm"] = np.nan
    return result


def daily_temperature(hourly: pd.DataFrame) -> pd.DataFrame:
    """Return daily 24-hour mean and midrange temperature in degrees Celsius.

    Parameters
    ----------
    hourly : pandas.DataFrame
        Columns ``time`` (naive UTC timestamps) and ``t2m_k`` (2 m temperature
        in kelvin, instantaneous).

    Returns
    -------
    pandas.DataFrame
        Columns ``t2m_mean_24h_c``, ``t2m_midrange_c`` ((max + min) / 2) and
        ``t2m_hours``, indexed by UTC date.
    """
    _check_times(hourly)
    celsius = hourly["t2m_k"].astype(float) - KELVIN_OFFSET
    frame = pd.DataFrame({"date": pd.to_datetime(hourly["time"]).dt.date, "t2m_c": celsius})
    grouped = frame.groupby("date")["t2m_c"]
    result = pd.DataFrame(
        {
            "t2m_mean_24h_c": grouped.mean(),
            "t2m_midrange_c": (grouped.max() + grouped.min()) / 2,
            "t2m_hours": grouped.count(),
        }
    )
    result.loc[result["t2m_hours"] < HOURS_PER_DAY, ["t2m_mean_24h_c", "t2m_midrange_c"]] = np.nan
    return result


def derive_daily(hourly: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Return one row per UTC day from ``start`` to ``end`` inclusive.

    Days absent from the hourly input appear with zero hours and blank values.
    The returned columns are ``DAILY_COLUMNS``.
    """
    dates = pd.date_range(start, end, freq="D").date
    precip = daily_precip(hourly).reindex(dates)
    temperature = daily_temperature(hourly).reindex(dates)
    daily = pd.concat([precip, temperature], axis=1)
    for column in ("precip_hours", "t2m_hours", "precip_clamped"):
        daily[column] = daily[column].fillna(0).astype(int)
    daily["day_complete"] = (daily["precip_hours"] == HOURS_PER_DAY) & (
        daily["t2m_hours"] == HOURS_PER_DAY
    )
    daily.index.name = "date"
    daily = daily.reset_index()
    n_incomplete = int((~daily["day_complete"]).sum())
    if n_incomplete:
        logger.warning("%d of %d days are incomplete", n_incomplete, len(daily))
    return daily[DAILY_COLUMNS]


def _check_times(hourly: pd.DataFrame) -> None:
    times = pd.to_datetime(hourly["time"])
    if getattr(times.dt, "tz", None) is not None:
        raise ValueError("Hourly times must be naive UTC timestamps")
    if times.duplicated().any():
        raise ValueError("Hourly times contain duplicates")

"""Monthly summaries, accumulation totals and reference normals.

All calculations run per ERA5-Land cell on the daily table produced by
:func:`cds_pull.daily.derive_daily` (with a ``cell_id`` column added), then
join to sites. Missing data is counted and flagged, never filled: a month or
window with any incomplete precipitation day has a blank precipitation total,
and temperature means use complete days only.
"""

from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

from .config import ClimateConfig
from .windows import Window, cumulative_window, season_window, wet_season_window

PRECIP = "precip_mm"
T2M_MEAN = "t2m_mean_24h_c"
T2M_MIDRANGE = "t2m_midrange_c"
WET_SEASON = "wet_season_precip_mm"
CUMULATIVE = "cum_since_oct1_precip_mm"
MONTHLY_MEASURES = (PRECIP, T2M_MEAN, T2M_MIDRANGE)
PRECIP_MEASURES = (PRECIP, WET_SEASON, CUMULATIVE)

NORMAL_COLUMNS = [
    "cell_id",
    "measure",
    "month",
    "mean",
    "sd",
    "n_periods",
    "period_first",
    "period_last",
    "incomplete_flag",
    "near_zero_flag",
]


def monthly_values(daily: pd.DataFrame) -> pd.DataFrame:
    """Return calendar-month totals and means per cell.

    Returns
    -------
    pandas.DataFrame
        Columns ``cell_id``, ``year``, ``month``, ``precip_mm``,
        ``t2m_mean_24h_c``, ``t2m_midrange_c``, ``precip_missing_days``,
        ``t2m_missing_days`` and ``month_incomplete``.
    """
    frame = daily.copy()
    dates = pd.to_datetime(frame["date"])
    frame["year"] = dates.dt.year
    frame["month"] = dates.dt.month
    frame["precip_ok"] = frame["precip_hours"] == 24
    frame["t2m_ok"] = frame["t2m_hours"] == 24
    grouped = frame.groupby(["cell_id", "year", "month"])
    result = pd.DataFrame(
        {
            PRECIP: grouped[PRECIP].sum(min_count=1),
            T2M_MEAN: grouped[T2M_MEAN].mean(),
            T2M_MIDRANGE: grouped[T2M_MIDRANGE].mean(),
            "precip_days": grouped["precip_ok"].sum(),
            "t2m_days": grouped["t2m_ok"].sum(),
        }
    ).reset_index()
    days_in_month = [
        calendar.monthrange(y, m)[1] for y, m in zip(result["year"], result["month"])
    ]
    result["precip_missing_days"] = days_in_month - result["precip_days"]
    result["t2m_missing_days"] = days_in_month - result["t2m_days"]
    result.loc[result["precip_missing_days"] > 0, PRECIP] = np.nan
    result["month_incomplete"] = (result["precip_missing_days"] > 0) | (
        result["t2m_missing_days"] > 0
    )
    return result.drop(columns=["precip_days", "t2m_days"])


def window_total(precip: pd.Series, window: Window) -> tuple[float, int]:
    """Return the precipitation total and missing-day count for a window.

    Parameters
    ----------
    precip : pandas.Series
        Daily precipitation in mm for one cell, indexed by a sorted
        ``DatetimeIndex``. Incomplete days are NaN.
    window : Window
        Inclusive date range.

    Returns
    -------
    tuple of (float, int)
        The total (NaN when any day is missing) and the number of missing days.
    """
    values = precip.loc[pd.Timestamp(window.start) : pd.Timestamp(window.end)]
    missing = window.n_days - int(values.notna().sum())
    total = float(values.sum()) if missing == 0 else np.nan
    return total, missing


def compute_normals(daily: pd.DataFrame, config: ClimateConfig) -> pd.DataFrame:
    """Return the ERA5-Land reference climatology per cell.

    Monthly measures are computed for all twelve calendar months. The
    wet-season normal uses the seasons ending in each reference year (``month``
    is blank). The cumulative normal uses each reference year as the
    observation year for each study month. ``period_first`` and
    ``period_last`` are years: the calendar year for monthly and cumulative
    measures and the ending year for wet seasons.
    """
    monthly = monthly_values(daily)
    ref_first, ref_last = config.reference_period
    reference = monthly[monthly["year"].between(ref_first, ref_last)]
    rows: list[dict] = []
    for (cell, month), group in reference.groupby(["cell_id", "month"]):
        for measure in MONTHLY_MEASURES:
            rows.append(_normal_row(cell, measure, month, group.set_index("year")[measure], config))

    season_start, season_end = config.wet_season_months
    for cell, precip in _precip_series(daily).items():
        seasons = {
            year: window_total(precip, season_window(year, season_start, season_end))[0]
            for year in config.reference_years
        }
        rows.append(_normal_row(cell, WET_SEASON, None, pd.Series(seasons), config))
        for month in config.study_months:
            totals = {
                year: window_total(precip, cumulative_window(year, month, season_start))[0]
                for year in config.reference_years
            }
            rows.append(_normal_row(cell, CUMULATIVE, month, pd.Series(totals), config))

    normals = pd.DataFrame(rows, columns=NORMAL_COLUMNS)
    normals["month"] = normals["month"].astype("Int64")
    return normals.sort_values(["cell_id", "measure", "month"], na_position="first").reset_index(
        drop=True
    )


def build_monthly_summary(
    daily: pd.DataFrame,
    normals: pd.DataFrame,
    site_cells: pd.DataFrame,
    config: ClimateConfig,
) -> pd.DataFrame:
    """Return one row per site, study year and study month.

    Each observation carries its monthly, wet-season and cumulative values,
    the matching normals, absolute anomalies, percent of normal (blank when
    the normal is below ``config.near_zero_normal_mm``) and completeness flags.
    """
    monthly = monthly_values(daily).set_index(["cell_id", "year", "month"])
    lookup = _normal_lookup(normals)
    season_start, season_end = config.wet_season_months
    threshold = config.near_zero_normal_mm
    precip_by_cell = _precip_series(daily)

    rows = []
    for cell, precip in precip_by_cell.items():
        for year in config.study_period_years:
            for month in config.study_months:
                key = (cell, year, month)
                obs = monthly.loc[key] if key in monthly.index else None
                row: dict = {"cell_id": cell, "year": year, "month": month}

                precip_mm = obs[PRECIP] if obs is not None else np.nan
                row.update(_precip_metrics("precip", precip_mm, _get(lookup, cell, PRECIP, month), threshold))
                for measure, prefix in ((T2M_MEAN, "t2m_mean_24h"), (T2M_MIDRANGE, "t2m_midrange")):
                    value = obs[measure] if obs is not None else np.nan
                    normal = _get(lookup, cell, measure, month)
                    row[f"{prefix}_c"] = value
                    row[f"{prefix}_normal_c"] = normal
                    row[f"{prefix}_anom_c"] = value - normal

                label, wet = wet_season_window(year, month, season_start, season_end)
                total, missing = window_total(precip, wet)
                row["wet_season_label"] = label
                row["wet_season_start"] = wet.start.isoformat()
                row["wet_season_end"] = wet.end.isoformat()
                row.update(
                    _precip_metrics(
                        "wet_season_precip", total, _get(lookup, cell, WET_SEASON, None), threshold
                    )
                )
                row["wet_season_missing_days"] = missing

                cum = cumulative_window(year, month, season_start)
                total, missing = window_total(precip, cum)
                row["cum_since_oct1_start"] = cum.start.isoformat()
                row["cum_since_oct1_end"] = cum.end.isoformat()
                row.update(
                    _precip_metrics(
                        "cum_since_oct1_precip", total, _get(lookup, cell, CUMULATIVE, month), threshold
                    )
                )
                row["cum_since_oct1_missing_days"] = missing

                month_days = calendar.monthrange(year, month)[1]
                row["precip_missing_days"] = obs["precip_missing_days"] if obs is not None else month_days
                row["t2m_missing_days"] = obs["t2m_missing_days"] if obs is not None else month_days
                row["month_incomplete"] = bool(obs["month_incomplete"]) if obs is not None else True
                rows.append(row)

    per_cell = pd.DataFrame(rows)
    summary = site_cells[["site", "cell_id"]].merge(per_cell, on="cell_id", how="left")
    return summary.sort_values(["site", "year", "month"]).reset_index(drop=True)


def percent_of_normal(value: float, normal: float, threshold: float) -> float:
    """Return 100 * value / normal, or NaN when the normal is below threshold."""
    if pd.isna(value) or pd.isna(normal) or normal < threshold:
        return np.nan
    return 100.0 * value / normal


def _precip_metrics(prefix: str, value: float, normal: float, threshold: float) -> dict:
    return {
        f"{prefix}_mm": value,
        f"{prefix}_normal_mm": normal,
        f"{prefix}_anom_mm": value - normal,
        f"{prefix}_pct_normal": percent_of_normal(value, normal, threshold),
        f"{prefix}_near_zero_normal": bool(pd.notna(normal) and normal < threshold),
    }


def _normal_row(
    cell: str, measure: str, month: int | None, values: pd.Series, config: ClimateConfig
) -> dict:
    valid = values.dropna()
    mean = float(valid.mean()) if len(valid) else np.nan
    return {
        "cell_id": cell,
        "measure": measure,
        "month": month,
        "mean": mean,
        "sd": float(valid.std(ddof=1)) if len(valid) > 1 else np.nan,
        "n_periods": len(valid),
        "period_first": int(valid.index.min()) if len(valid) else pd.NA,
        "period_last": int(valid.index.max()) if len(valid) else pd.NA,
        "incomplete_flag": len(valid) < config.min_reference_periods,
        "near_zero_flag": bool(
            measure in PRECIP_MEASURES and pd.notna(mean) and mean < config.near_zero_normal_mm
        ),
    }


def _precip_series(daily: pd.DataFrame) -> dict[str, pd.Series]:
    series = {}
    for cell, group in daily.groupby("cell_id"):
        group = group.assign(date=pd.to_datetime(group["date"])).sort_values("date")
        values = group[PRECIP].where(group["precip_hours"] == 24)
        series[cell] = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(group["date"]))
    return series


def _normal_lookup(normals: pd.DataFrame) -> dict[tuple, float]:
    return {
        (cell, measure, None if pd.isna(month) else int(month)): mean
        for cell, measure, month, mean in zip(
            normals["cell_id"], normals["measure"], normals["month"], normals["mean"]
        )
    }


def _get(lookup: dict[tuple, float], cell: str, measure: str, month: int | None) -> float:
    return float(lookup.get((cell, measure, month), np.nan))

"""Automated quality checks for the climate context pipeline.

Each check returns rows for a ``checks.csv`` table with the columns in
``CHECK_COLUMNS``. ``passed`` is False when a rule is broken; informational
checks (such as clamped values) always pass and report counts in ``detail``.
"""

from __future__ import annotations

import pandas as pd

from .cells import grid_cells
from .config import ClimateConfig

CHECK_COLUMNS = ["check", "scope", "passed", "detail"]
MISSING_DAY_COLUMNS = ["cell_id", "date", "precip_hours", "t2m_hours"]
GRID_TOLERANCE_DEG = 1e-3


def missing_days(daily: pd.DataFrame) -> pd.DataFrame:
    """Return every incomplete or absent day with its hourly counts."""
    incomplete = daily.loc[~daily["day_complete"], MISSING_DAY_COLUMNS]
    return incomplete.sort_values(["cell_id", "date"]).reset_index(drop=True)


def check_region_grid(cells: pd.DataFrame, config: ClimateConfig) -> list[dict]:
    """Check that the downloaded grid matches the configured region."""
    expected = set(grid_cells(config.region_lat, config.region_lon)["cell_id"])
    found = set(cells["cell_id"])
    detail = f"{len(found)} grid points, {int(cells['has_data'].sum())} with data"
    if found != expected:
        detail += f"; missing {sorted(expected - found)}, extra {sorted(found - expected)}"
    return [_row("region_grid", "all", found == expected, detail)]


def check_site_cells(site_cells: pd.DataFrame, cells: pd.DataFrame) -> list[dict]:
    """Check that every site's cell is in the region and has data."""
    has_data = cells.set_index("cell_id")["has_data"].astype(bool)
    rows = []
    for row in site_cells.itertuples(index=False):
        ok = bool(has_data.get(row.cell_id, False))
        detail = f"{row.cell_id} ({row.assignment}"
        detail += f", centroid cell {row.centroid_cell_id})" if row.assignment == "manual" else ")"
        if not ok:
            detail += "; cell missing or without data"
        rows.append(_row("site_cell_has_data", row.site, ok, detail))
    return rows


def check_completeness(daily: pd.DataFrame) -> list[dict]:
    """Check that every day has 24 hourly values per variable, per cell."""
    rows = []
    for cell, group in daily.groupby("cell_id"):
        bad = group.loc[~group["day_complete"], "date"]
        detail = f"{len(bad)} incomplete of {len(group)} days"
        if len(bad):
            detail += f" (first {min(bad)}, last {max(bad)})"
        rows.append(_row("days_complete", cell, bad.empty, detail))
    return rows


def check_plausible_ranges(daily: pd.DataFrame, config: ClimateConfig) -> list[dict]:
    """Check daily temperature and precipitation against configured limits."""
    low, high = config.daily_temp_range_c
    cap = config.daily_precip_cap_mm
    rows = []
    for cell, group in daily.groupby("cell_id"):
        temps = group[["t2m_mean_24h_c", "t2m_midrange_c"]].stack()
        out_of_range = int(((temps < low) | (temps > high)).sum())
        rows.append(
            _row(
                "daily_temperature_range",
                cell,
                out_of_range == 0,
                f"{out_of_range} values outside [{low}, {high}] C; observed "
                f"{temps.min():.1f} to {temps.max():.1f} C",
            )
        )
        precip = group["precip_mm"].dropna()
        bad = int(((precip < 0) | (precip > cap)).sum())
        rows.append(
            _row(
                "daily_precip_range",
                cell,
                bad == 0,
                f"{bad} values outside [0, {cap}] mm; max {precip.max():.1f} mm",
            )
        )
        rows.append(
            _row(
                "negative_hours_clamped",
                cell,
                True,
                f"{int(group['precip_clamped'].sum())} hourly values clamped to zero",
            )
        )
    return rows


def check_normals(normals: pd.DataFrame, config: ClimateConfig) -> list[dict]:
    """Check that every normal uses the full reference period."""
    short = normals.loc[normals["incomplete_flag"]]
    detail = f"{len(short)} of {len(normals)} normals below {config.min_reference_periods} periods"
    return [_row("normals_complete", "all", short.empty, detail)]


def check_summary(
    summary: pd.DataFrame, site_cells: pd.DataFrame, config: ClimateConfig
) -> list[dict]:
    """Check the summary row count and the one-cell-per-site mapping."""
    expected = len(site_cells) * len(config.study_period_years) * len(config.study_months)
    cells_per_site = site_cells.groupby("site")["cell_id"].nunique()
    incomplete = int(summary["month_incomplete"].sum())
    return [
        _row("summary_row_count", "all", len(summary) == expected, f"{len(summary)} of {expected} rows"),
        _row(
            "one_cell_per_site",
            "all",
            bool(cells_per_site.eq(1).all() and site_cells["site"].is_unique),
            f"{len(site_cells)} sites, {site_cells['cell_id'].nunique()} cells",
        ),
        _row("study_months_complete", "all", incomplete == 0, f"{incomplete} incomplete study months"),
    ]


def run_checks(
    daily: pd.DataFrame,
    normals: pd.DataFrame,
    summary: pd.DataFrame,
    site_cells: pd.DataFrame,
    cells: pd.DataFrame,
    config: ClimateConfig,
) -> pd.DataFrame:
    """Run every automated check and return the combined table.

    ``daily`` and ``normals`` cover every cell with data; ``summary`` covers
    the study sites; ``cells`` is the regional cell table with ``has_data``.
    """
    rows = [
        *check_region_grid(cells, config),
        *check_site_cells(site_cells, cells),
        *check_completeness(daily),
        *check_plausible_ranges(daily, config),
        *check_normals(normals, config),
        *check_summary(summary, site_cells, config),
    ]
    return pd.DataFrame(rows, columns=CHECK_COLUMNS)


def _row(check: str, scope: str, passed: bool, detail: str) -> dict:
    return {"check": check, "scope": scope, "passed": bool(passed), "detail": detail}

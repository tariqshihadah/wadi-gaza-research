"""ERA5-Land climate context: regional download, site-to-cell assignment, daily values and normals."""

from .cells import (
    assign_cells,
    cell_box,
    cell_id,
    cells_geodataframe,
    grid_cells,
    load_sites,
    parse_cell_id,
    predict_cell,
)
from .checks import missing_days, run_checks
from .config import ClimateConfig
from .daily import daily_precip, daily_temperature, derive_daily
from .download import ClimateDownloader, build_request, request_area, request_date_range
from .io import cell_table, load_daily, open_region
from .summaries import (
    build_monthly_summary,
    compute_normals,
    monthly_values,
    percent_of_normal,
    window_total,
)
from .windows import Window, cumulative_window, season_label, season_window, wet_season_window

__all__ = [
    "ClimateConfig",
    "ClimateDownloader",
    "Window",
    "assign_cells",
    "build_monthly_summary",
    "build_request",
    "cell_box",
    "cell_id",
    "cell_table",
    "cells_geodataframe",
    "compute_normals",
    "cumulative_window",
    "daily_precip",
    "daily_temperature",
    "derive_daily",
    "grid_cells",
    "load_daily",
    "load_sites",
    "missing_days",
    "monthly_values",
    "open_region",
    "parse_cell_id",
    "percent_of_normal",
    "predict_cell",
    "request_area",
    "request_date_range",
    "run_checks",
    "season_label",
    "season_window",
    "wet_season_window",
    "window_total",
]

"""ERA5-Land climate context: site-to-cell assignment, daily values and normals."""

from .cells import assign_cells, cell_box, cell_id, cells_geodataframe, load_sites, predict_cell
from .config import ClimateConfig
from .daily import daily_precip, daily_temperature, derive_daily
from .download import build_request, request_date_range
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
    "Window",
    "assign_cells",
    "build_monthly_summary",
    "build_request",
    "cell_box",
    "cell_id",
    "cells_geodataframe",
    "compute_normals",
    "cumulative_window",
    "daily_precip",
    "daily_temperature",
    "derive_daily",
    "load_sites",
    "monthly_values",
    "percent_of_normal",
    "predict_cell",
    "request_date_range",
    "season_label",
    "season_window",
    "wet_season_window",
    "window_total",
]

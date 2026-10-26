"""Build CDS API requests for the ERA5-Land hourly time-series dataset.

Only request construction lives here for now. The downloader (cache, unzip,
metadata sidecar and manifest) is added after the one-cell probe confirms the
returned file layout.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from .config import ClimateConfig


def request_date_range(config: ClimateConfig) -> str:
    """Return the CDS ``date`` value for the configured extraction range.

    Hourly precipitation is period-ending, so the last day's total needs the
    value stamped 00:00 on the following day. The request therefore ends one
    day after ``extraction_range[1]``.
    """
    start, end = config.extraction_range
    return f"{start.isoformat()}/{(end + timedelta(days=1)).isoformat()}"


def build_request(cell_lat: float, cell_lon: float, config: ClimateConfig) -> dict[str, Any]:
    """Return the request body for one grid cell, using the form's parameter names."""
    return {
        "variable": list(config.variables),
        "location": {"latitude": cell_lat, "longitude": cell_lon},
        "date": [request_date_range(config)],
        "data_format": config.data_format,
    }

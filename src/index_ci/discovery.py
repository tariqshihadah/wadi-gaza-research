"""Selection of individual dated index raster observations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from spatial_ci.discovery import RasterRecord, discover_rasters

from .config import IndexAnalysisConfig


@dataclass(frozen=True)
class IndexObservationSpec:
    """One site, index month, and observation year raster."""

    study_area: str
    year: int
    month: str
    path: Path


def discover_observations(config: IndexAnalysisConfig) -> list[IndexObservationSpec]:
    """Discover configured individual observations without forming year pairs."""
    records: list[RasterRecord] = discover_rasters(config.data_root)
    return [
        IndexObservationSpec(record.study_area, record.year, record.month, record.path)
        for record in records
        if (config.study_areas is None or record.study_area in config.study_areas)
        and record.month in config.months
        and config.year_range[0] <= record.year <= config.year_range[1]
    ]

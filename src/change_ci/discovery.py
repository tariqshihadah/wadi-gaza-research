"""GeoTIFF discovery and consecutive-year pair construction."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import AnalysisConfig
from spatial_ci.discovery import RasterRecord, discover_rasters

LOGGER = logging.getLogger(__name__)

__all__ = ["PairSpec", "RasterRecord", "build_pairs", "discover_rasters"]


@dataclass(frozen=True)
class PairSpec:
    """Two same-month rasters from consecutive years."""

    study_area: str
    month: str
    year_start: int
    year_end: int
    earlier_path: Path
    later_path: Path

def build_pairs(records: list[RasterRecord], config: AnalysisConfig) -> list[PairSpec]:
    """Build filtered same-month, consecutive-year pairs."""
    selected = {
        (record.study_area, record.year, record.month): record
        for record in records
        if (config.study_areas is None or record.study_area in config.study_areas)
        and record.month in config.months
        and config.year_range[0] <= record.year <= config.year_range[1]
    }
    pairs: list[PairSpec] = []
    areas = config.study_areas or sorted({key[0] for key in selected})
    for area in areas:
        for month in config.months:
            for year in range(config.year_range[0], config.year_range[1]):
                earlier = selected.get((area, year, month))
                later = selected.get((area, year + 1, month))
                if earlier is None or later is None:
                    LOGGER.warning(
                        "Skipping missing pair: %s %s %s-%s", area, month, year, year + 1
                    )
                    continue
                pairs.append(PairSpec(area, month, year, year + 1, earlier.path, later.path))
    return pairs
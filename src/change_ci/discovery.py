"""GeoTIFF discovery and consecutive-year pair construction."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .config import AnalysisConfig

LOGGER = logging.getLogger(__name__)
_FILENAME = re.compile(r"^(?P<study_area>.+)_(?P<year>\d{4})-(?P<month>\d{2})\.tif$", re.I)


@dataclass(frozen=True)
class RasterRecord:
    """A discovered raster and its temporal identifiers."""

    study_area: str
    year: int
    month: str
    path: Path


@dataclass(frozen=True)
class PairSpec:
    """Two same-month rasters from consecutive years."""

    study_area: str
    month: str
    year_start: int
    year_end: int
    earlier_path: Path
    later_path: Path


def discover_rasters(data_root: Path) -> list[RasterRecord]:
    """Discover and parse rasters under ``data_root``."""
    records: list[RasterRecord] = []
    for path in sorted(data_root.rglob("*.tif")):
        match = _FILENAME.match(path.name)
        if match is None:
            LOGGER.warning("Ignoring TIFF with unexpected name: %s", path)
            continue
        records.append(
            RasterRecord(
                study_area=match["study_area"],
                year=int(match["year"]),
                month=match["month"],
                path=path,
            )
        )
    return records


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
                    LOGGER.warning("Skipping missing pair: %s %s %s-%s", area, month, year, year + 1)
                    continue
                pairs.append(PairSpec(area, month, year, year + 1, earlier.path, later.path))
    return pairs
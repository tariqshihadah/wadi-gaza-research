"""Discovery of dated raster observations shared by CI analyses."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)
_FILENAME = re.compile(r"^(?P<study_area>.+)_(?P<year>\d{4})-(?P<month>\d{2})\.tif$", re.I)


@dataclass(frozen=True)
class RasterRecord:
    """A discovered raster and its temporal identifiers."""

    study_area: str
    year: int
    month: str
    path: Path


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

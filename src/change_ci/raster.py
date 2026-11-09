"""Loading and validation of one pair of index rasters."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import rasterio

from .discovery import PairSpec
from spatial_ci.raster import read_band

LOGGER = logging.getLogger(__name__)


class RasterPair:
    """Load, validate, and summarize one earlier/later raster pair."""

    def __init__(self, spec: PairSpec, band: str | int = "NDVI", max_lag_fraction: float = 0.25):
        self.spec = spec
        self.band = band
        self._values, self.cell_size = self._load_difference()
        valid_rows, valid_cols = np.where(np.isfinite(self._values))
        if len(valid_rows) < 2:
            raise ValueError(f"Fewer than two valid pixels in pair: {spec}")
        self._values = self._values[valid_rows.min():valid_rows.max() + 1,
                                    valid_cols.min():valid_cols.max() + 1]
        self.n = int(np.isfinite(self._values).sum())
        self.mean = float(np.nanmean(self._values))
        self.sd = float(np.nanstd(self._values, ddof=1))
        self.k_max = int(np.floor(max_lag_fraction * min(self._values.shape)))

    def _load_difference(self) -> tuple[np.ndarray, float]:
        """Read the selected band and compute Eq. (1)."""
        with rasterio.open(self.spec.earlier_path) as earlier, rasterio.open(self.spec.later_path) as later:
            if earlier.crs != later.crs or earlier.transform != later.transform or earlier.shape != later.shape:
                raise ValueError("Raster pair has mismatched CRS, transform, or shape")
            earlier_data = _read_band(earlier, self.band)
            later_data = _read_band(later, self.band)
            cell_size = float(earlier.res[0])
            if not np.isclose(earlier.res[0], earlier.res[1]):
                LOGGER.warning("Raster pixels are not square: %s", earlier.res)
        difference = later_data - earlier_data
        difference[~(np.isfinite(earlier_data) & np.isfinite(later_data))] = np.nan
        return difference, cell_size

    @property
    def values(self) -> np.ndarray:
        """Return the difference raster, with NaN for invalid pixels."""
        return self._values


def _read_band(source: rasterio.DatasetReader, band: str | int) -> np.ndarray:
    """Read one named or numbered band as float64 with NaN masking."""
    return read_band(source, band)
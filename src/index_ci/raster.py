"""Loading, masking, and summarizing one index raster observation."""

from __future__ import annotations

import logging

import numpy as np
import rasterio

from spatial_ci.raster import read_band

from .discovery import IndexObservationSpec

LOGGER = logging.getLogger(__name__)


class RasterObservation:
    """Load and summarize one single-year index raster."""

    def __init__(
        self,
        spec: IndexObservationSpec,
        band: str,
        max_lag_fraction: float = 0.25,
    ):
        self.spec = spec
        self.band = band
        with rasterio.open(spec.path) as source:
            self._values = read_band(source, band)
            self.crs = source.crs
            self.transform = source.transform
            self.shape = source.shape
            self.cell_size = float(source.res[0])
            if not np.isclose(source.res[0], source.res[1]):
                LOGGER.warning("Raster pixels are not square: %s", source.res)
        self.max_lag_fraction = max_lag_fraction
        self._summarize(crop=False)

    def _summarize(self, *, crop: bool) -> None:
        """Update summaries and crop the array to its valid bounding box."""
        valid_rows, valid_cols = np.where(np.isfinite(self._values))
        if len(valid_rows) < 2:
            raise ValueError(f"Fewer than two valid pixels in observation: {self.spec}")
        row_start, row_end = valid_rows.min(), valid_rows.max() + 1
        col_start, col_end = valid_cols.min(), valid_cols.max() + 1
        if crop:
            self._values = self._values[row_start:row_end, col_start:col_end]
        self.n = int(np.isfinite(self._values).sum())
        self.mean = float(np.nanmean(self._values))
        self.sd = float(np.nanstd(self._values, ddof=1))
        self.k_max = int(np.floor(
            self.max_lag_fraction * min(row_end - row_start, col_end - col_start)
        ))

    @property
    def values(self) -> np.ndarray:
        """Return the index raster, with invalid pixels represented by NaN."""
        return self._values

    @property
    def grid_signature(self) -> tuple[object, object, tuple[int, int]]:
        """Return grid metadata used to verify temporal co-registration."""
        return self.crs, self.transform, self.shape

    def restrict_to(self, valid_mask: np.ndarray) -> None:
        """Apply a shared valid-pixel mask and recompute spatial summaries."""
        if valid_mask.shape != self._values.shape:
            raise ValueError(f"Common mask does not match observation grid: {self.spec}")
        self._values = np.where(valid_mask & np.isfinite(self._values), self._values, np.nan)
        self._summarize(crop=True)

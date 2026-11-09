"""Shared raster band reading utilities."""

from __future__ import annotations

import numpy as np
import rasterio


def read_band(source: rasterio.DatasetReader, band: str | int) -> np.ndarray:
    """Read one named or numbered band as float64 with invalid values as NaN."""
    if isinstance(band, str):
        try:
            band_number = source.descriptions.index(band) + 1
        except ValueError as exc:
            raise ValueError(f"Band {band!r} is not described in {source.name}") from exc
    else:
        band_number = band
    if not 1 <= band_number <= source.count:
        raise ValueError(f"Band {band_number} is outside 1..{source.count} in {source.name}")
    return source.read(band_number, masked=True).astype("float64").filled(np.nan)

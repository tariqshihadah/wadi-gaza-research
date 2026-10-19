"""Canonical defaults for the Sentinel-2 acquisition workflow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcquisitionConfig:
    """Default parameters used to build monthly study-area composites."""

    months: tuple[int, ...] = (1, 5, 9, 11)
    years: tuple[int, ...] = tuple(range(2019, 2026))
    bands: tuple[str, ...] = (
        "B02",
        "B03",
        "B04",
        "B05",
        "B08",
        "B8A",
        "B11",
        "B12",
    )
    indices: tuple[str, ...] = ("NDVI", "GNDVI", "SAVI", "NDRE")
    resolution: int = 10
    upsampling: str = "NEAREST"
    max_cloud: int = 20
    mask_scl: tuple[int, ...] = (0, 1, 2, 3, 7, 8, 9, 10, 11)
    compute_std: bool = True

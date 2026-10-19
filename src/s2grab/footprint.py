"""Study-area footprint: the single rule deciding which pixels belong to a site.

A pixel is inside the study area when its **center** falls inside the site
polygon (rasterio/GDAL default rasterization, ``all_touched=False``). The
footprint is applied once, at acquisition, in :meth:`s2grab.S2Client.fetch`:
pixels outside it are set to NaN before anything is saved. Downstream steps
treat NaN as "outside the study area or no usable observation" and never
re-mask.

Saved GeoTIFFs carry :data:`FOOTPRINT_RULE` and the footprint pixel count in
their metadata tags so the denominator for coverage statistics is known
without re-reading the polygons.
"""

from __future__ import annotations

import numpy as np
from affine import Affine
from rasterio.features import geometry_mask
from shapely.geometry.base import BaseGeometry

FOOTPRINT_RULE = "pixel_center"
TAG_RULE = "FOOTPRINT_RULE"
TAG_PIXELS = "FOOTPRINT_PIXELS"


def pixel_center_mask(
    geometry: BaseGeometry,
    transform: Affine,
    shape: tuple[int, int],
) -> np.ndarray:
    """Boolean (H, W) mask, True where the pixel center lies inside ``geometry``."""
    return geometry_mask(
        [geometry.__geo_interface__],
        out_shape=shape,
        transform=transform,
        all_touched=False,
        invert=True,
    )


def apply_footprint(array: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Return ``array`` (H, W[, bands]) as float32 with pixels outside ``footprint`` set to NaN."""
    if array.shape[:2] != footprint.shape:
        raise ValueError(
            f"Array shape {array.shape[:2]} does not match footprint shape {footprint.shape}"
        )
    out = array.astype("float32", copy=True)
    out[~footprint] = np.nan
    return out

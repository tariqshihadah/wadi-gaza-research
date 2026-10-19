"""IO: write a numpy array to a georeferenced GeoTIFF.

Kept separate from fetching so we can test the raster writing independently and
reuse it for any band stack.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import rasterio
from affine import Affine
from rasterio.transform import from_bounds
from sentinelhub import BBox


def write_geotiff(
    path: str | Path,
    array: np.ndarray,
    bbox: BBox,
    band_names: Sequence[str] | None = None,
    tags: Mapping[str, object] | None = None,
    transform: Affine | None = None,
) -> Path:
    """Write ``array`` to ``path`` as a FLOAT32 GeoTIFF georeferenced by ``bbox``.

    Parameters
    ----------
    array: shape (H, W) or (H, W, bands).
    bbox: the request BBox (carries CRS and extent).
    band_names: optional per-band descriptions written into metadata.
    tags: optional dataset-level metadata tags (values stored as strings).
    transform: grid transform; derived from ``bbox`` and the array size if None.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if array.ndim == 2:
        array = array[:, :, np.newaxis]
    # (H, W, bands) -> (bands, H, W)
    arr = np.transpose(array, (2, 0, 1)).astype("float32")
    count, height, width = arr.shape

    if transform is None:
        transform = from_bounds(*bbox, width=width, height=height)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=count,
        dtype="float32",
        crs=f"EPSG:{bbox.crs.value}",
        transform=transform,
        compress="deflate",
    ) as dst:
        dst.write(arr)
        if tags:
            dst.update_tags(**{key: str(value) for key, value in tags.items()})
        if band_names:
            for i, name in enumerate(band_names, start=1):
                dst.set_band_description(i, name)
    return path

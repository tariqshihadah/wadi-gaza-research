"""Site loading — the only place that touches geopandas / vector files.

Kept separate from :mod:`s2grab.aoi` so the geometry core stays lean and
dependency-light. This module bridges a GeoDataFrame (or a vector file path)
into ``{site_id: AOI}`` using :meth:`AOI.from_geometry`.

    import geopandas as gpd
    from s2grab.sites import load_aois

    aois = load_aois("sites/Cities_SS4A/Cities_SS4A.shp", id_field="CITY_NAME")
    # or from an already-loaded frame:
    gdf = gpd.read_file(...)
    aois = load_aois(gdf, id_field="CITY_NAME")
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import geopandas as gpd

from .aoi import AOI


def load_aois(
    source: Union[str, Path, "gpd.GeoDataFrame"],
    id_field: Union[str, None] = None,
    resolution: float = 10,
    clip: bool = True,
) -> dict[str, AOI]:
    """Build one :class:`AOI` per feature.

    Parameters
    ----------
    source: a path to a vector file, or an already-loaded GeoDataFrame.
    id_field: attribute column used as the dict key. If None, the row index is
        used ("site0", "site1", ...). Non-unique values get a numeric suffix.
    resolution: ground resolution in metres, passed through to each AOI.
    clip: keep each polygon for server-side masking (option B). See
        :meth:`AOI.from_geometry`.

    Returns
    -------
    dict mapping site id -> AOI, preserving feature order.
    """
    gdf = source if isinstance(source, gpd.GeoDataFrame) else gpd.read_file(source)
    if gdf.crs is None:
        raise ValueError("Source has no CRS defined; assign one before loading.")

    aois: dict[str, AOI] = {}
    for idx, row in gdf.iterrows():
        if id_field is not None:
            site_id = str(row[id_field])
        else:
            site_id = f"site{idx}"

        # Guard against duplicate ids so no feature is silently dropped.
        unique_id = site_id
        suffix = 1
        while unique_id in aois:
            suffix += 1
            unique_id = f"{site_id}_{suffix}"

        aois[unique_id] = AOI.from_geometry(
            row.geometry, crs=gdf.crs, resolution=resolution, clip=clip
        )
    return aois

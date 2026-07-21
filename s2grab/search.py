"""Search: discover which Sentinel-2 scenes exist for an AOI and time window.

This is the "look before you download" step. It queries the CDSE Catalog (STAC)
API and returns a tidy pandas DataFrame — the natural format for research — with
one row per acquisition and its metadata.

Kept as a pure function (config passed in) so it is easy to test and reuse; a
richer object-oriented wrapper is layered on top later.
"""

from __future__ import annotations

import pandas as pd
from sentinelhub import SentinelHubCatalog, SHConfig

from .aoi import AOI
from .fetch import cdse_collection


def search(
    config: SHConfig,
    aoi: AOI,
    start: str,
    end: str,
    max_cloud_cover: float = 100,
) -> pd.DataFrame:
    """Return acquisitions intersecting ``aoi`` within ``[start, end]``.

    Parameters
    ----------
    config: authenticated SHConfig (see :mod:`s2grab.auth`).
    aoi: request geometry (see :mod:`s2grab.aoi`).
    start, end: inclusive date bounds as YYYY-MM-DD strings.
    max_cloud_cover: scene-level cloud filter, percent (0-100).

    Returns
    -------
    pandas.DataFrame with columns: id, datetime, date, cloud_cover.
    Sorted by datetime; empty (with those columns) if nothing qualifies.
    """
    catalog = SentinelHubCatalog(config=config)
    search_area = (
        {"geometry": aoi.geometry}
        if aoi.geometry is not None
        else {"bbox": aoi.bbox}
    )
    results = catalog.search(
        cdse_collection(),
        time=(start, end),
        filter=f"eo:cloud_cover < {max_cloud_cover}",
        fields={
            "include": ["id", "properties.datetime", "properties.eo:cloud_cover"],
            "exclude": [],
        },
        **search_area,
    )

    rows = []
    for item in results:
        props = item["properties"]
        rows.append(
            {
                "id": item.get("id"),
                "datetime": props["datetime"],
                "date": props["datetime"][:10],
                "cloud_cover": props.get("eo:cloud_cover"),
            }
        )

    columns = ["id", "datetime", "date", "cloud_cover"]
    if not rows:
        return pd.DataFrame(columns=columns)
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("datetime")
        .reset_index(drop=True)
    )

"""Fetch: run a single Process API request and return a numpy array.

One request = one AOI + one time interval + one evalscript. Keeping it to a
single scene makes failures easy to localise and retry.
"""

from __future__ import annotations

import numpy as np
from sentinelhub import (
    DataCollection,
    MimeType,
    MosaickingOrder,
    SentinelHubRequest,
    SHConfig,
)

from .aoi import AOI
from .auth import CDSE_BASE_URL


def cdse_collection() -> DataCollection:
    """Sentinel-2 L2A bound to the CDSE service URL."""
    return DataCollection.SENTINEL2_L2A.define_from(
        "s2l2a_cdse", service_url=CDSE_BASE_URL
    )


def fetch_array(
    config: SHConfig,
    evalscript: str,
    aoi: AOI,
    time_interval: tuple[str, str],
    max_cloud_cover: int = 100,
    mosaicking: MosaickingOrder = MosaickingOrder.MOST_RECENT,
) -> np.ndarray | None:
    """Fetch one scene/composite as a numpy array.

    Parameters
    ----------
    config: authenticated SHConfig (see :mod:`s2grab.auth`).
    evalscript: the evalscript string (see :mod:`s2grab.evalscripts`).
    aoi: request geometry + size (see :mod:`s2grab.aoi`).
    time_interval: (start, end) as YYYY-MM-DD strings.
    max_cloud_cover: scene-level cloud filter, percent (0-100).
    mosaicking: how to pick among candidate scenes in the interval.

    Returns
    -------
    numpy.ndarray of shape (H, W, bands), or None if the response is empty.
    """
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=cdse_collection(),
                time_interval=time_interval,
                mosaicking_order=mosaicking,
                maxcc=max_cloud_cover / 100,
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        size=aoi.size,
        config=config,
        # When the AOI carries a polygon, clip to it (pixels outside are masked);
        # otherwise request the full bounding box.
        **(
            {"geometry": aoi.geometry}
            if aoi.geometry is not None
            else {"bbox": aoi.bbox}
        ),
    )
    data = request.get_data()[0]
    if data is None or not np.any(data):
        return None
    # Single-band responses come back 2D; normalise to (H, W, bands).
    if data.ndim == 2:
        data = data[:, :, np.newaxis]
    return data

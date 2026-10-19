"""S2Client — a thin, credential-bound facade over the functional core.

Binds authentication once, then delegates to the pure functions in
:mod:`s2grab.search` and :mod:`s2grab.fetch`, returning the rich objects from
:mod:`s2grab.models`. It holds no processing logic itself — just the session
and convenient method signatures.

    client = S2Client()
    aoi = AOI.from_bounds(-114.63, 32.70, -114.60, 32.72)
    scenes = client.search(aoi, "2024-06-01", "2024-08-31", max_cloud=20)
    image = client.fetch(aoi, date=scenes.cleanest().date)
    image.save("out.tif")
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Union

from sentinelhub import MosaickingOrder, SHConfig

from . import evalscripts
from . import fetch as fetch_mod
from . import search as search_mod
from .aoi import AOI
from .auth import get_config
from .evalscripts import EvalScript
from .footprint import apply_footprint
from .models import Image, Scene, SceneList


class S2Client:
    """Authenticated entry point for searching and fetching Sentinel-2 data."""

    def __init__(self, config: Union[SHConfig, None] = None):
        self.config = config or get_config()

    def search(
        self,
        aoi: AOI,
        start: str,
        end: str,
        max_cloud: float = 100,
    ) -> SceneList:
        """Discover scenes for ``aoi`` between ``start`` and ``end``."""
        df = search_mod.search(self.config, aoi, start, end, max_cloud_cover=max_cloud)
        return SceneList.from_dataframe(df)

    def fetch(
        self,
        aoi: AOI,
        *,
        date: Union[str, Scene, None] = None,
        start: Union[str, None] = None,
        end: Union[str, None] = None,
        product: Union[str, EvalScript] = "true_color",
        max_cloud: float = 100,
        mosaicking: MosaickingOrder = MosaickingOrder.MOST_RECENT,
        upsampling: Union[str, None] = None,
        downsampling: Union[str, None] = None,
    ) -> Union[Image, None]:
        """Fetch one image.

        Provide either a single ``date`` (a YYYY-MM-DD string or a
        :class:`Scene`) for one acquisition, or a ``start``/``end`` window to
        composite according to ``mosaicking``.

        ``product`` may be a preset name ("true_color", "ndvi", "indices",
        "full"), an :class:`~s2grab.evalscripts.EvalScript` built via
        :func:`s2grab.evalscripts.make_evalscript`, or a raw evalscript string.

        ``upsampling`` / ``downsampling`` control how bands whose native
        resolution differs from the output grid are resampled ("NEAREST",
        "BILINEAR", "BICUBIC"). None uses the service default (NEAREST); this
        matters for the 20 m bands (B05, B8A, B11, B12) and NDRE when the grid
        is 10 m.

        The full bounding box is requested and the AOI's pixel-center
        study-area footprint is then applied: pixels outside it are set to NaN.
        This is the only place the footprint is applied.

        Returns an :class:`Image`, or None if no data qualifies.
        """
        if date is not None:
            day = date.date if isinstance(date, Scene) else date
            nxt = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime(
                "%Y-%m-%d"
            )
            time_interval = (day, nxt)
        elif start is not None and end is not None:
            time_interval = (start, end)
        else:
            raise ValueError("Provide either date=... or both start=... and end=...")

        evalscript = evalscripts.resolve(product)
        array = fetch_mod.fetch_array(
            config=self.config,
            evalscript=evalscript.script,
            aoi=aoi,
            time_interval=time_interval,
            max_cloud_cover=max_cloud,
            mosaicking=mosaicking,
            upsampling=upsampling,
            downsampling=downsampling,
        )
        if array is None:
            return None
        array = apply_footprint(array, aoi.footprint)
        product_name = product if isinstance(product, str) else "custom"
        return Image(
            array=array,
            aoi=aoi,
            band_names=list(evalscript.band_names) if evalscript.band_names else None,
            product=product_name,
        )

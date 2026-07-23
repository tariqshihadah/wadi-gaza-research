"""s2grab — a small, layered toolkit for retrieving Sentinel-2 imagery from CDSE.

Two ways to use it:

1. Pythonic facade (recommended for most work)::

       from s2grab import S2Client, AOI
       client = S2Client()
       aoi = AOI.from_bounds(-114.63, 32.70, -114.60, 32.72)
       scenes = client.search(aoi, "2024-06-01", "2024-08-31", max_cloud=20)
       image = client.fetch(aoi, date=scenes.cleanest().date)
       image.save("out.tif")

2. Functional core (explicit, easy to test) — the modules below:

       auth        credentials -> authenticated SHConfig
       aoi         bounds/polygon -> local-UTM BBox + pixel dimensions
       evalscripts named evalscripts (start simple: true colour)
       fetch       one Process API request -> numpy array
       io          numpy array + BBox -> georeferenced GeoTIFF
       search      catalog search -> acquisition DataFrame

The facade delegates to the functional core; it adds no processing logic.
"""

from .aoi import AOI, aoi_from_bounds
from .client import S2Client
from .evalscripts import (
    REDUCERS,
    EvalScript,
    Index,
    make_evalscript,
    make_scl_count_evalscript,
)
from .models import Image, Scene, SceneList
from .windows import month_window, month_windows

__all__ = [
    "S2Client",
    "AOI",
    "aoi_from_bounds",
    "Scene",
    "SceneList",
    "Image",
    "make_evalscript",
    "make_scl_count_evalscript",
    "Index",
    "EvalScript",
    "REDUCERS",
    "month_window",
    "month_windows",
]

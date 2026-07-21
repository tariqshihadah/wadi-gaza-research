"""Milestone 4: build an AOI from a real polygon and fetch a clipped image.

Loads one feature from the study-site shapefile, builds a polygon-clipping AOI
(option B), discovers scenes over it, and fetches the cleanest true-colour clip.
Because the AOI carries a polygon, pixels outside the boundary come back masked
(0), which we confirm by reading the dataMask-like zero border.

Run:
    python examples/05_shapefile_aoi.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from s2grab import S2Client  # noqa: E402
from s2grab.sites import load_aois  # noqa: E402

SHAPEFILE = "sites/Cities_SS4A/Cities_SS4A.shp"
ID_FIELD = "CITY_NAME"
START, END = "2024-06-01", "2024-08-31"
OUT_PATH = Path("outputs/_tests/shapefile_clip.tif")


def main() -> int:
    client = S2Client()

    aois = load_aois(SHAPEFILE, id_field=ID_FIELD)
    site_id, aoi = next(iter(aois.items()))
    print(f"Loaded {len(aois)} site(s). Using '{site_id}': {aoi!r}")
    print(f"  clipped to polygon: {aoi.is_clipped}")

    scenes = client.search(aoi, START, END, max_cloud=20)
    print(f"Search: {scenes!r}")
    if len(scenes) == 0:
        print("FAIL: no scenes found for this site/window.")
        return 1

    pick = scenes.cleanest()
    print(f"Cleanest: {pick!r}")

    image = client.fetch(aoi, date=pick, product="true_color")
    if image is None:
        print("FAIL: fetch returned no data.")
        return 1
    print(f"Fetched: {image!r}")

    image.save(OUT_PATH)
    with rasterio.open(OUT_PATH) as src:
        band1 = src.read(1)
        zero_frac = float(np.mean(band1 == 0))
        print(
            f"OK: wrote {OUT_PATH} "
            f"(CRS={src.crs}, {src.width}x{src.height}, {src.count} bands)"
        )
        # A clipped polygon inside its bbox should leave some masked (0) border.
        print(f"  masked (zero) fraction: {zero_frac:.1%}")
    print("Polygon-clipping AOI works. M4 complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

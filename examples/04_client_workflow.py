"""Milestone 3c: the full Pythonic workflow via S2Client.

Demonstrates the intended end-user experience: authenticate once, discover
scenes, pick the cleanest, fetch it, and save — all through rich objects.

Run:
    python examples/04_client_workflow.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rasterio  # noqa: E402

from s2grab import AOI, S2Client  # noqa: E402

BOUNDS = (-114.63, 32.70, -114.60, 32.72)
START, END = "2024-06-01", "2024-08-31"
OUT_PATH = Path("outputs/_tests/client_truecolor_cleanest.tif")


def main() -> int:
    client = S2Client()
    aoi = AOI.from_bounds(*BOUNDS, resolution=10)
    print(f"AOI: {aoi!r}")

    scenes = client.search(aoi, START, END, max_cloud=20)
    print(f"Search: {scenes!r}")
    if len(scenes) == 0:
        print("FAIL: no scenes found.")
        return 1

    pick = scenes.cleanest()
    print(f"Cleanest scene: {pick!r}")

    image = client.fetch(aoi, date=pick, product="true_color")
    if image is None:
        print("FAIL: fetch returned no data.")
        return 1
    print(f"Fetched: {image!r}")

    image.save(OUT_PATH)
    with rasterio.open(OUT_PATH) as src:
        print(
            f"OK: wrote {OUT_PATH} "
            f"(CRS={src.crs}, {src.width}x{src.height}, {src.count} bands)"
        )
    print("Pythonic workflow works. Core (M1-M3) complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

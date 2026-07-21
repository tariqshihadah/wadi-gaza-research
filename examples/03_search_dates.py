"""Milestone 3a: discover the scenes that exist for an AOI + time window.

Uses the same small test AOI as milestone 2, but instead of blindly fetching,
it lists the real acquisitions and their cloud cover. This is the research
"look before you download" step.

Run:
    python examples/03_search_dates.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from s2grab import aoi as aoi_mod  # noqa: E402
from s2grab.auth import get_config  # noqa: E402
from s2grab.search import search  # noqa: E402

BOUNDS = (-114.63, 32.70, -114.60, 32.72)  # min_lon, min_lat, max_lon, max_lat
START, END = "2024-06-01", "2024-08-31"
MAX_CLOUD_COVER = 20


def main() -> int:
    config = get_config()
    aoi = aoi_mod.aoi_from_bounds(*BOUNDS, resolution=10)

    print(f"Searching {START}..{END} (maxcc<{MAX_CLOUD_COVER}%) for EPSG:{aoi.epsg} AOI...")
    scenes = search(config, aoi, START, END, max_cloud_cover=MAX_CLOUD_COVER)

    if scenes.empty:
        print("FAIL: no scenes found (unexpected for this AOI/window).")
        return 1

    print(f"OK: found {len(scenes)} scene(s).")
    print(scenes.to_string(index=False))
    print(
        f"\nCloud cover: min={scenes['cloud_cover'].min():.1f}% "
        f"max={scenes['cloud_cover'].max():.1f}%"
    )
    print("Search works. Ready for M3b (SceneList wrapper) / M3c (S2Client).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

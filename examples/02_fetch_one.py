"""Milestone 2: fetch ONE true-colour image and write a verified GeoTIFF.

Everything here is hardcoded on purpose — a small AOI (irrigated farmland by the
Colorado River near Yuma, AZ; reliably clear skies) and a fixed one-month window
with known Sentinel-2 coverage. No catalog search yet: we ask for the most
recent low-cloud scene in the window. If this writes a valid GeoTIFF, the core
pipeline (auth -> AOI -> fetch -> write) works.

Run:
    python examples/02_fetch_one.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rasterio  # noqa: E402

from s2grab import aoi as aoi_mod  # noqa: E402
from s2grab import evalscripts, fetch  # noqa: E402
from s2grab.auth import get_config  # noqa: E402
from s2grab.io import write_geotiff  # noqa: E402

# --- Hardcoded test parameters ------------------------------------------------
BOUNDS = (-114.63, 32.70, -114.60, 32.72)  # min_lon, min_lat, max_lon, max_lat
TIME_INTERVAL = ("2024-07-01", "2024-07-31")
MAX_CLOUD_COVER = 20
OUT_PATH = Path("outputs/_tests/truecolor_yuma_2024-07.tif")
# -----------------------------------------------------------------------------


def main() -> int:
    config = get_config()

    aoi = aoi_mod.aoi_from_bounds(*BOUNDS, resolution=10)
    print(f"AOI: EPSG:{aoi.epsg}, size={aoi.size}px, res={aoi.resolution:.1f}m")

    print(f"Fetching true colour for {TIME_INTERVAL} (maxcc={MAX_CLOUD_COVER}%)...")
    array = fetch.fetch_array(
        config=config,
        evalscript=evalscripts.get("true_color"),
        aoi=aoi,
        time_interval=TIME_INTERVAL,
        max_cloud_cover=MAX_CLOUD_COVER,
    )
    if array is None:
        print("FAIL: empty response (no qualifying scene in window).")
        return 1
    print(f"Got array shape={array.shape}, dtype={array.dtype}")

    write_geotiff(
        OUT_PATH, array, aoi.bbox, band_names=evalscripts.BAND_NAMES["true_color"]
    )

    # Verify by reopening.
    with rasterio.open(OUT_PATH) as src:
        print(
            f"OK: wrote {OUT_PATH}\n"
            f"    CRS={src.crs}, size={src.width}x{src.height}, "
            f"bands={src.count}, dtype={src.dtypes[0]}"
        )
        stats = src.read(1)
        print(f"    band1 range: {stats.min():.4f}..{stats.max():.4f}")
    print("Pipeline works. Ready for milestone 3 (catalog search).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

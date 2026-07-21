"""Milestone 5: bands & indices via the hybrid evalscript system.

Exercises all three tiers:
  1. a preset ("indices"),
  2. an on-demand make_evalscript(bands=..., indices=...),
  3. confirms band count/names stay in sync with the data returned.

Run:
    python examples/06_indices.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from s2grab import AOI, S2Client, make_evalscript  # noqa: E402
from s2grab import evalscripts  # noqa: E402

BOUNDS = (-114.63, 32.70, -114.60, 32.72)
DATE = "2024-06-05"  # a known clear scene from milestone 3


def _check_offline() -> None:
    """Pure-logic checks on the generator (no network)."""
    es = make_evalscript(bands=["B04", "B08"], indices=["NDVI"], include_datamask=True)
    assert es.band_names == ("B04", "B08", "NDVI", "dataMask"), es.band_names
    # Output band count in setup() must equal the number of returned values.
    assert 'output: { bands: 4' in es.script, es.script
    # NDVI needs B08+B04; both should appear as inputs exactly once.
    assert es.script.count('"B08"') == 1 and es.script.count('"B04"') == 1
    print("Offline generator checks passed.")


def main() -> int:
    _check_offline()

    client = S2Client()
    aoi = AOI.from_bounds(*BOUNDS, resolution=10)

    # Tier 1: preset.
    preset = evalscripts.PRESETS["indices"]
    print(f"Preset 'indices' -> bands {preset.band_names}")
    img = client.fetch(aoi, date=DATE, product="indices")
    if img is None:
        print("FAIL: no data for preset fetch.")
        return 1
    print(f"Fetched preset: {img!r}, band_names={img.band_names}")
    assert img.shape[2] == len(preset.band_names)

    ndvi = img.array[:, :, img.band_names.index("NDVI")]
    finite = ndvi[np.isfinite(ndvi)]
    print(f"  NDVI range: {finite.min():.3f}..{finite.max():.3f}")

    # Tier 2: on-demand build.
    custom = make_evalscript(bands=["B08", "B04"], indices=["NDVI", "NDMI"])
    img2 = client.fetch(aoi, date=DATE, product=custom)
    if img2 is None:
        print("FAIL: no data for custom build fetch.")
        return 1
    print(f"Fetched custom build: {img2!r}, band_names={img2.band_names}")
    assert img2.shape[2] == 4

    print("Hybrid evalscript system works. M5 complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

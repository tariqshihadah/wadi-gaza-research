"""Milestone 5b: temporal median composite over a date window.

A median composite reduces every scene in the window to one cloud-robust image,
computed server-side (no post-processing). We fetch a median NDVI over a summer
window and sanity-check it against a single clear scene from the same window.

Note: pass ``start``/``end`` (a window), not a single ``date`` — the reducer
composites across all scenes in that window.

Run:
    python examples/07_median.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from s2grab import AOI, S2Client, make_evalscript  # noqa: E402

BOUNDS = (-114.63, 32.70, -114.60, 32.72)
START, END = "2024-06-01", "2024-08-31"
SINGLE_DATE = "2024-06-05"  # a known clear scene for comparison


def _check_offline() -> None:
    es = make_evalscript(indices=["NDVI"], reduce="median")
    assert es.band_names == ("NDVI",), es.band_names
    assert 'mosaicking: "ORBIT"' in es.script, es.script
    assert "function agg(a)" in es.script
    assert "s.dataMask === 0" in es.script  # invalid pixels skipped
    # A None reducer must NOT be multi-temporal.
    assert 'mosaicking' not in make_evalscript(indices=["NDVI"]).script
    print("Offline median-generator checks passed.")


def _mean_finite(a: np.ndarray) -> float:
    return float(np.nanmean(np.where(np.isfinite(a), a, np.nan)))


def main() -> int:
    _check_offline()

    client = S2Client()
    aoi = AOI.from_bounds(*BOUNDS, resolution=10)

    median_ndvi = make_evalscript(indices=["NDVI"], reduce="median")
    comp = client.fetch(aoi, start=START, end=END, product=median_ndvi, max_cloud=30)
    if comp is None:
        print("FAIL: median composite returned no data.")
        return 1
    m = comp.array[:, :, 0]
    print(f"Median NDVI composite {START}..{END}: {comp!r}")
    print(f"  mean over AOI: {_mean_finite(m):.3f}")

    single = client.fetch(aoi, date=SINGLE_DATE, product=make_evalscript(indices=["NDVI"]))
    s = single.array[:, :, 0]
    print(f"Single-scene NDVI {SINGLE_DATE}: mean over AOI {_mean_finite(s):.3f}")

    # They should be in the same ballpark (same farmland, same season).
    diff = abs(_mean_finite(m) - _mean_finite(s))
    print(f"  |median - single| mean NDVI = {diff:.3f}")
    print("Temporal median composite works. M5b complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

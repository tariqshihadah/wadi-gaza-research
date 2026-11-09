"""Helpers for fetching composites and their quality metrics."""

from __future__ import annotations

from typing import Sequence, TypedDict

import numpy as np

from .aoi import AOI
from .client import S2Client
from .evalscripts import make_evalscript
from .models import Image


class CompositeQA(TypedDict):
    """Quality metrics calculated for one site and monthly window."""

    n_scenes: int
    mean_cloud: float
    pct_nodata: float
    mean_pixel_std: float


def composite_qa(
    client: S2Client,
    aoi: AOI,
    start: str,
    end: str,
    *,
    bands: Sequence[str],
    indices: Sequence[str],
    max_cloud: float,
    mask_scl: Sequence[int],
    compute_std: bool,
    upsampling: str | None = None,
    savi_l: float | None = None,
) -> tuple[Image | None, CompositeQA]:
    """Fetch a masked median composite and its quality metrics.

    Returns ``(None, qa)`` when no scenes or no composite data qualify.
    """
    scenes = client.search(aoi, start, end, max_cloud=max_cloud)
    clouds = [scene.cloud_cover for scene in scenes if scene.cloud_cover is not None]
    qa: CompositeQA = {
        "n_scenes": len(scenes),
        "mean_cloud": float(np.mean(clouds)) if clouds else float("nan"),
        "pct_nodata": float("nan"),
        "mean_pixel_std": float("nan"),
    }

    if qa["n_scenes"] == 0:
        return None, qa

    median_product = make_evalscript(
        bands=bands,
        indices=indices,
        reduce="median",
        mask_scl=mask_scl,
        savi_l=savi_l,
    )
    image = client.fetch(
        aoi,
        start=start,
        end=end,
        product=median_product,
        max_cloud=max_cloud,
        upsampling=upsampling,
    )
    if image is None:
        return None, qa

    study = aoi.footprint
    no_data = np.all(np.isnan(image.array), axis=2) & study
    study_pixels = int(study.sum())
    qa["pct_nodata"] = (
        100.0 * no_data.sum() / study_pixels if study_pixels else float("nan")
    )

    if compute_std:
        std_product = make_evalscript(
            bands=bands,
            indices=indices,
            reduce="std",
            mask_scl=mask_scl,
            savi_l=savi_l,
        )
        std_image = client.fetch(
            aoi,
            start=start,
            end=end,
            product=std_product,
            max_cloud=max_cloud,
            upsampling=upsampling,
        )
        if std_image is not None:
            qa["mean_pixel_std"] = float(np.nanmean(std_image.array))

    return image, qa

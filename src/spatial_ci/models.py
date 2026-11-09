"""Shared result records for spatial correlograms and confidence intervals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CorrelogramData:
    """Moran's I and ordered pair counts indexed by lag."""

    lags: np.ndarray
    moran_i: np.ndarray
    pair_counts: np.ndarray


@dataclass(frozen=True)
class EffectiveNResult:
    """Effective sample size and range decision for one threshold."""

    range_px: int | None
    n_eff: float
    flag_no_range: bool


@dataclass(frozen=True)
class CIResult:
    """Confidence interval details for a mean and effective sample size."""

    lower: float
    upper: float
    se: float
    df: float
    t_crit: float

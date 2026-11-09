"""Shared estimators for spatial effective sample size and mean confidence intervals."""

from __future__ import annotations

import numpy as np
from scipy.stats import t

from .models import CIResult, CorrelogramData, EffectiveNResult


def find_range(moran_i: np.ndarray, tau: float) -> int | None:
    """Return the first 1-indexed lag with ``I_k < tau``."""
    matches = np.flatnonzero(np.asarray(moran_i) < tau)
    return int(matches[0] + 1) if len(matches) else None


def effective_sample_size(
    moran_i: np.ndarray, pair_counts: np.ndarray, n: int, range_px: int
) -> float:
    """Estimate effective sample size by summing lags below range."""
    if range_px < 1:
        raise ValueError("range_px must be at least one")
    if range_px == 1:
        return float(n)
    denominator = 1.0 + float(np.sum((pair_counts[:range_px - 1] / n) * moran_i[:range_px - 1]))
    if denominator <= 0:
        raise ValueError("Effective sample size denominator must be positive")
    return float(n / denominator)


def estimate_effective_n(data: CorrelogramData, n: int, tau: float) -> EffectiveNResult:
    """Find the range and estimate effective sample size."""
    range_px = find_range(data.moran_i, tau)
    if range_px is None:
        return EffectiveNResult(None, float("nan"), True)
    return EffectiveNResult(
        range_px,
        effective_sample_size(data.moran_i, data.pair_counts, n, range_px),
        False,
    )


def confidence_interval(mean: float, sd: float, n_eff: float, alpha: float) -> CIResult:
    """Return a Student-t confidence interval for a spatial mean."""
    if not np.isfinite(n_eff) or n_eff <= 1:
        raise ValueError("n_eff must be finite and greater than one")
    df = float(n_eff - 1)
    t_crit = float(t.ppf(1 - alpha / 2, df))
    se = float(sd / np.sqrt(n_eff))
    margin = t_crit * se
    return CIResult(float(mean - margin), float(mean + margin), se, df, t_crit)

"""Data records shared by the change confidence interval pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

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


@dataclass(frozen=True)
class ChangeCIResult:
    """One threshold-specific result record for a date pair."""

    study_area: str
    index: str
    month: str
    year_start: int
    year_end: int
    tau: float
    is_primary_tau: bool
    engine: str
    n: int
    mean_change: float
    sd: float
    k_max: int
    cell_size: float
    range_px: int | None
    range_map_units: float
    n_eff: float
    df: float
    t_crit: float
    se: float
    ci_low: float
    ci_high: float
    naive_se: float
    naive_ci_low: float
    naive_ci_high: float
    ci_excludes_zero: bool
    flag_no_range: bool
    flag_low_n_eff: bool
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the result as a tabular record."""
        return asdict(self)
"""Data records shared by the change confidence interval pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from spatial_ci.models import CIResult, CorrelogramData, EffectiveNResult


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
"""Result records for index-level spatial confidence intervals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class IndexCIResult:
    """One threshold-specific CI for one site-month-year index observation."""

    study_area: str
    index: str
    month: str
    year: int
    tau: float
    is_primary_tau: bool
    engine: str
    n: int
    mean_index: float
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
    flag_no_range: bool
    flag_low_n_eff: bool
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a tabular result mapping."""
        return asdict(self)

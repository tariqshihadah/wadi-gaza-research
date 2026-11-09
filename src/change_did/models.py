"""Result records for the weighted fixed-effects model on index change."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FitTerm:
    """One estimated indicator term from a weighted fixed-effects fit."""

    term: str
    estimate: float
    se: float
    ci_low: float
    ci_high: float
    p_value: float


@dataclass(frozen=True)
class WeightedFitResult:
    """One weighted fixed-effects fit with its variance components."""

    terms: dict[str, FitTerm]
    sigma_u: float
    sigma_u_clipped: bool
    df: int
    n_obs: int
    dropped_terms: tuple[str, ...] = ()
    coefficients: dict[str, float] = field(default_factory=dict)

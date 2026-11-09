"""Result records and model specifications for the fixed-effects model."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MODEL_SITE_PERIOD = "site_period"
MODEL_PERIOD_ONLY = "period_only"

#: Model name -> whether the design includes site fixed effects.
MODEL_SPECS = {MODEL_SITE_PERIOD: True, MODEL_PERIOD_ONLY: False}


@dataclass(frozen=True)
class FitTerm:
    """One estimated term from a weighted fixed-effects fit."""

    term: str
    estimate: float
    se: float
    ci_low: float
    ci_high: float
    p_value: float

    @property
    def significant(self) -> bool:
        """Return whether the confidence interval excludes zero."""
        return self.ci_low > 0.0 or self.ci_high < 0.0


@dataclass(frozen=True)
class JointTest:
    """One joint Wald F-test over a block of fixed effects."""

    name: str
    statistic: float
    df_num: int
    df_den: int
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
    columns: tuple[str, ...] = ()
    cov: np.ndarray | None = field(default=None, repr=False, compare=False)
    site_effects: bool = True

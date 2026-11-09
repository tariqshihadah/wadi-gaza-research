"""Backward-compatible imports for shared spatial CI estimators."""

from spatial_ci.estimation import (
    confidence_interval,
    effective_sample_size,
    estimate_effective_n,
    find_range,
)
from spatial_ci.models import CIResult, EffectiveNResult

__all__ = [
    "confidence_interval",
    "CIResult",
    "effective_sample_size",
    "estimate_effective_n",
    "find_range",
    "EffectiveNResult",
]
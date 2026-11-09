"""Shared spatial-autocorrelation confidence interval primitives."""

from .correlogram import MoranCorrelogram
from .discovery import RasterRecord, discover_rasters
from .engines import (
    BruteForceEngine,
    CorrelogramEngine,
    FFTEngine,
    PySALEngine,
    get_engine,
)
from .estimation import (
    confidence_interval,
    effective_sample_size,
    estimate_effective_n,
    find_range,
)
from .models import CIResult, CorrelogramData, EffectiveNResult
from .raster import read_band

__all__ = [
    "BruteForceEngine",
    "CIResult",
    "CorrelogramData",
    "CorrelogramEngine",
    "EffectiveNResult",
    "FFTEngine",
    "MoranCorrelogram",
    "PySALEngine",
    "RasterRecord",
    "confidence_interval",
    "discover_rasters",
    "effective_sample_size",
    "estimate_effective_n",
    "find_range",
    "get_engine",
    "read_band",
]

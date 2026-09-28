"""Spatial-autocorrelation-adjusted confidence intervals for raster changes."""

from .analysis import ChangeCIAnalysis, MoranCorrelogram
from .config import AnalysisConfig
from .discovery import PairSpec, RasterRecord, build_pairs, discover_rasters
from .engines import (
    BruteForceEngine,
    CorrelogramEngine,
    FFTEngine,
    PySALEngine,
    get_engine,
)
from .estimation import confidence_interval, effective_sample_size, find_range
from .models import CorrelogramData, ChangeCIResult, CIResult, EffectiveNResult
from .raster import RasterPair

__all__ = [
    "AnalysisConfig",
    "BruteForceEngine",
    "ChangeCIAnalysis",
    "ChangeCIResult",
    "CIResult",
    "CorrelogramData",
    "CorrelogramEngine",
    "EffectiveNResult",
    "FFTEngine",
    "MoranCorrelogram",
    "PairSpec",
    "PySALEngine",
    "RasterPair",
    "RasterRecord",
    "build_pairs",
    "confidence_interval",
    "discover_rasters",
    "effective_sample_size",
    "find_range",
    "get_engine",
]
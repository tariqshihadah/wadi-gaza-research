"""Shared Moran's I correlogram computation and tidy output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .engines import CorrelogramEngine
from .estimation import estimate_effective_n
from .models import CorrelogramData, EffectiveNResult


@dataclass
class MoranCorrelogram:
    """A computed raster correlogram independent of the analysis metric."""

    data: CorrelogramData
    n: int

    @classmethod
    def from_values(
        cls, values: np.ndarray, engine: CorrelogramEngine, max_lag: int
    ) -> MoranCorrelogram:
        """Compute one correlogram from a two-dimensional raster."""
        n = int(np.isfinite(values).sum())
        return cls(engine.compute(values, max_lag), n)

    def effective_n(self, tau: float) -> EffectiveNResult:
        """Estimate effective sample size at the requested threshold."""
        return estimate_effective_n(self.data, self.n, tau)

    def to_frame(self, metadata: Mapping[str, Any]) -> pd.DataFrame:
        """Return tidy lag rows with caller-provided observation metadata."""
        frame = pd.DataFrame({
            "lag": self.data.lags,
            "moran_i": self.data.moran_i,
            "pair_count": self.data.pair_counts,
        })
        for key, value in metadata.items():
            frame[key] = value
        return frame[[*metadata, "lag", "moran_i", "pair_count"]]

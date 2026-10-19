"""Correlogram objects and end-to-end change CI orchestration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import pandas as pd

from .config import AnalysisConfig
from .discovery import PairSpec
from .engines import CorrelogramEngine, get_engine
from .estimation import confidence_interval, estimate_effective_n
from .models import ChangeCIResult, CorrelogramData
from .raster import RasterPair

LOGGER = logging.getLogger(__name__)


@dataclass
class MoranCorrelogram:
    """A single pair's computed Moran's I correlogram."""

    data: CorrelogramData
    n: int
    pair: RasterPair

    @classmethod
    def from_raster_pair(
        cls, pair: RasterPair, engine: CorrelogramEngine, max_lag: int | None = None
    ) -> "MoranCorrelogram":
        """Compute a correlogram for ``pair`` once."""
        return cls(engine.compute(pair.values, max_lag or pair.k_max), pair.n, pair)

    def effective_n(self, tau: float):
        """Estimate effective sample size at ``tau`` (Eqs. 8-9)."""
        return estimate_effective_n(self.data, self.n, tau)

    def to_frame(self) -> pd.DataFrame:
        """Return tidy lag rows for correlogram output."""
        return pd.DataFrame({
            "study_area": self.pair.spec.study_area,
            "month": self.pair.spec.month,
            "year_start": self.pair.spec.year_start,
            "year_end": self.pair.spec.year_end,
            "lag": self.data.lags,
            "moran_i": self.data.moran_i,
            "pair_count": self.data.pair_counts,
        })


class ChangeCIAnalysis:
    """Run configured confidence interval calculations over raster pairs."""

    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.engine = get_engine(config.engine)

    def run_pair(self, spec: PairSpec) -> tuple[list[ChangeCIResult], pd.DataFrame]:
        """Analyze one pair and return threshold results plus correlogram rows."""
        pair = RasterPair(spec, self.config.index_band, self.config.max_lag_fraction)
        correlogram = MoranCorrelogram.from_raster_pair(pair, self.engine)
        naive = confidence_interval(pair.mean, pair.sd, pair.n, self.config.alpha)
        results: list[ChangeCIResult] = []
        for tau in self.config.tau_sensitivity:
            effective = correlogram.effective_n(tau)
            if effective.flag_no_range:
                ci_values = (float("nan"),) * 5
                range_px = None
            else:
                ci = confidence_interval(pair.mean, pair.sd, effective.n_eff, self.config.alpha)
                ci_values = (ci.df, ci.t_crit, ci.se, ci.lower, ci.upper)
                range_px = effective.range_px
            ci_low, ci_high = ci_values[3], ci_values[4]
            results.append(ChangeCIResult(
                spec.study_area, spec.month, spec.year_start, spec.year_end,
                tau, tau == self.config.tau, self.config.engine, pair.n,
                pair.mean, pair.sd, pair.k_max, pair.cell_size, range_px,
                float(range_px * pair.cell_size) if range_px is not None else float("nan"),
                effective.n_eff, ci_values[0], ci_values[1], ci_values[2], ci_low, ci_high,
                naive.se, naive.lower, naive.upper,
                bool(ci_low > 0 or ci_high < 0) if range_px is not None else False,
                effective.flag_no_range,
                bool(effective.n_eff < self.config.min_n_eff) if not effective.flag_no_range else False,
            ))
        return results, correlogram.to_frame()

    def run(self, specs: list[PairSpec]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Process all pairs, recording per-pair failures and continuing."""
        result_rows: list[dict] = []
        correlogram_frames: list[pd.DataFrame] = []
        for spec in specs:
            try:
                results, frame = self.run_pair(spec)
                result_rows.extend(result.to_dict() for result in results)
                correlogram_frames.append(frame)
            except Exception as exc:
                LOGGER.exception("Pair failed: %s", spec)
                result_rows.append(_error_result(spec, self.config, str(exc)))
        columns = list(ChangeCIResult.__dataclass_fields__)
        return pd.DataFrame(result_rows, columns=columns), pd.concat(correlogram_frames, ignore_index=True) if correlogram_frames else pd.DataFrame()

    def save(self, results: pd.DataFrame, correlograms: pd.DataFrame) -> None:
        """Write CSV outputs and the audit configuration."""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        results.to_csv(self.config.output_dir / "results.csv", index=False)
        correlograms.to_csv(self.config.output_dir / "correlograms.csv", index=False)
        with (self.config.output_dir / "config.json").open("w", encoding="utf-8") as stream:
            json.dump(self.config.to_dict(), stream, indent=2)


def _error_result(spec: PairSpec, config: AnalysisConfig, error: str) -> dict:
    """Create a result-shaped error row for a failed pair."""
    values = {field: None for field in ChangeCIResult.__dataclass_fields__}
    values.update({
        "study_area": spec.study_area, "month": spec.month,
        "year_start": spec.year_start, "year_end": spec.year_end,
        "tau": config.tau, "is_primary_tau": True, "engine": config.engine,
        "flag_no_range": False, "flag_low_n_eff": False, "error": error,
    })
    return values
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
from spatial_ci.correlogram import MoranCorrelogram as SpatialMoranCorrelogram

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
        correlogram = SpatialMoranCorrelogram.from_values(
            pair.values, engine, max_lag or pair.k_max
        )
        return cls(correlogram.data, correlogram.n, pair)

    def effective_n(self, tau: float):
        """Estimate effective sample size at ``tau`` (Eqs. 8-9)."""
        return estimate_effective_n(self.data, self.n, tau)

    def to_frame(self) -> pd.DataFrame:
        """Return tidy lag rows for correlogram output."""
        return SpatialMoranCorrelogram(self.data, self.n).to_frame({
            "study_area": self.pair.spec.study_area,
            "index": self.pair.band,
            "month": self.pair.spec.month,
            "year_start": self.pair.spec.year_start,
            "year_end": self.pair.spec.year_end,
        })


class ChangeCIAnalysis:
    """Run configured confidence interval calculations over raster pairs."""

    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.engine = get_engine(config.engine)

    def run_pair(
        self, spec: PairSpec, index_band: str
    ) -> tuple[list[ChangeCIResult], pd.DataFrame]:
        """Analyze one pair and return threshold results plus correlogram rows."""
        pair = RasterPair(spec, index_band, self.config.max_lag_fraction)
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
                study_area=spec.study_area,
                index=index_band,
                month=spec.month,
                year_start=spec.year_start,
                year_end=spec.year_end,
                tau=tau,
                is_primary_tau=tau == self.config.tau,
                engine=self.config.engine,
                n=pair.n,
                mean_change=pair.mean,
                sd=pair.sd,
                k_max=pair.k_max,
                cell_size=pair.cell_size,
                range_px=range_px,
                range_map_units=(
                    float(range_px * pair.cell_size)
                    if range_px is not None else float("nan")
                ),
                n_eff=effective.n_eff,
                df=ci_values[0],
                t_crit=ci_values[1],
                se=ci_values[2],
                ci_low=ci_low,
                ci_high=ci_high,
                naive_se=naive.se,
                naive_ci_low=naive.lower,
                naive_ci_high=naive.upper,
                ci_excludes_zero=(
                    bool(ci_low > 0 or ci_high < 0)
                    if range_px is not None else False
                ),
                flag_no_range=effective.flag_no_range,
                flag_low_n_eff=(
                    bool(effective.n_eff < self.config.min_n_eff)
                    if not effective.flag_no_range else False
                ),
            ))
        return results, correlogram.to_frame()

    def run(self, specs: list[PairSpec]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Process all pairs, recording per-pair failures and continuing."""
        result_rows: list[dict] = []
        correlogram_frames: list[pd.DataFrame] = []
        for index_band in self.config.index_bands:
            for spec in specs:
                try:
                    results, frame = self.run_pair(spec, index_band)
                    result_rows.extend(result.to_dict() for result in results)
                    correlogram_frames.append(frame)
                except Exception as exc:
                    LOGGER.exception("Pair failed for %s: %s", index_band, spec)
                    result_rows.append(
                        _error_result(spec, self.config, index_band, str(exc))
                    )
        columns = list(ChangeCIResult.__dataclass_fields__)
        correlogram_columns = [
            "study_area", "index", "month", "year_start", "year_end",
            "lag", "moran_i", "pair_count",
        ]
        correlograms = (
            pd.concat(correlogram_frames, ignore_index=True)
            if correlogram_frames
            else pd.DataFrame(columns=correlogram_columns)
        )
        return pd.DataFrame(result_rows, columns=columns), correlograms

    def save(self, results: pd.DataFrame, correlograms: pd.DataFrame) -> None:
        """Write CSV outputs and the audit configuration."""
        for index_band in self.config.index_bands:
            output_dir = self.config.output_dir / index_band
            output_dir.mkdir(parents=True, exist_ok=True)
            results.loc[results["index"] == index_band].to_csv(
                output_dir / "results.csv", index=False
            )
            correlograms.loc[correlograms["index"] == index_band].to_csv(
                output_dir / "correlograms.csv", index=False
            )
            config = self.config.to_dict()
            config["index_band"] = index_band
            config["output_dir"] = str(output_dir)
            with (output_dir / "config.json").open("w", encoding="utf-8") as stream:
                json.dump(config, stream, indent=2)


def _error_result(
    spec: PairSpec, config: AnalysisConfig, index_band: str, error: str
) -> dict:
    """Create a result-shaped error row for a failed pair."""
    values = {field: None for field in ChangeCIResult.__dataclass_fields__}
    values.update({
        "study_area": spec.study_area, "month": spec.month,
        "index": index_band,
        "year_start": spec.year_start, "year_end": spec.year_end,
        "tau": config.tau, "is_primary_tau": True, "engine": config.engine,
        "flag_no_range": False, "flag_low_n_eff": False, "error": error,
    })
    return values
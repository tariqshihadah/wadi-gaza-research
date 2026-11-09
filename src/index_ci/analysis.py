"""Moran correlograms and confidence intervals for individual index rasters."""

from __future__ import annotations

import json
import logging
from collections import defaultdict

import numpy as np
import pandas as pd

from spatial_ci import MoranCorrelogram, confidence_interval, get_engine

from .config import IndexAnalysisConfig
from .discovery import IndexObservationSpec
from .models import IndexCIResult
from .raster import RasterObservation

LOGGER = logging.getLogger(__name__)
_CORRELOGRAM_COLUMNS = [
    "study_area", "index", "month", "year", "lag", "moran_i", "pair_count",
]


class IndexCIAnalysis:
    """Run spatial-autocorrelation-adjusted CIs on annual index rasters."""

    def __init__(self, config: IndexAnalysisConfig):
        self.config = config
        self.engine = get_engine(config.engine)

    def run(
        self, specs: list[IndexObservationSpec]
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Analyze observations using a shared valid-pixel mask by site/month/index."""
        groups: dict[tuple[str, str], list[IndexObservationSpec]] = defaultdict(list)
        for spec in specs:
            groups[(spec.study_area, spec.month)].append(spec)

        result_rows: list[dict] = []
        correlogram_frames: list[pd.DataFrame] = []
        for index_band in self.config.index_bands:
            for group_key in sorted(groups):
                group_specs = sorted(groups[group_key], key=lambda spec: spec.year)
                try:
                    observations = [
                        RasterObservation(spec, index_band, self.config.max_lag_fraction)
                        for spec in group_specs
                    ]
                    reference_grid = observations[0].grid_signature
                    if any(
                        observation.grid_signature != reference_grid
                        for observation in observations[1:]
                    ):
                        raise ValueError(
                            f"Observation rasters have mismatched grids: {group_key}"
                        )
                    common_mask = np.logical_and.reduce([
                        np.isfinite(observation.values) for observation in observations
                    ])
                    if int(common_mask.sum()) < 2:
                        raise ValueError(
                            f"Fewer than two common valid pixels for {group_key}, {index_band}"
                        )
                    for observation in observations:
                        observation.restrict_to(common_mask)
                except Exception as exc:
                    LOGGER.exception(
                        "Observation group failed for %s %s: %s", index_band, group_key, exc
                    )
                    for spec in group_specs:
                        result_rows.extend(
                            _error_result(spec, self.config, index_band, tau, str(exc))
                            for tau in self.config.tau_sensitivity
                        )
                    continue

                for spec, observation in zip(group_specs, observations):
                    try:
                        results, correlogram = self.run_observation(
                            spec, observation, index_band
                        )
                        result_rows.extend(result.to_dict() for result in results)
                        correlogram_frames.append(correlogram)
                    except Exception as exc:
                        LOGGER.exception(
                            "Observation failed for %s %s: %s", index_band, spec, exc
                        )
                        result_rows.extend(
                            _error_result(spec, self.config, index_band, tau, str(exc))
                            for tau in self.config.tau_sensitivity
                        )

        result_columns = list(IndexCIResult.__dataclass_fields__)
        correlograms = (
            pd.concat(correlogram_frames, ignore_index=True)
            if correlogram_frames
            else pd.DataFrame(columns=_CORRELOGRAM_COLUMNS)
        )
        return pd.DataFrame(result_rows, columns=result_columns), correlograms

    def run_observation(
        self,
        spec: IndexObservationSpec,
        observation: RasterObservation,
        index_band: str,
    ) -> tuple[list[IndexCIResult], pd.DataFrame]:
        """Compute all threshold results and correlogram rows for one observation."""
        correlogram = MoranCorrelogram.from_values(
            observation.values, self.engine, observation.k_max
        )
        naive = confidence_interval(
            observation.mean, observation.sd, observation.n, self.config.alpha
        )
        results: list[IndexCIResult] = []
        for tau in self.config.tau_sensitivity:
            effective = correlogram.effective_n(tau)
            if effective.flag_no_range:
                ci_values = (float("nan"),) * 5
                range_px = None
            else:
                ci = confidence_interval(
                    observation.mean, observation.sd, effective.n_eff, self.config.alpha
                )
                ci_values = (ci.df, ci.t_crit, ci.se, ci.lower, ci.upper)
                range_px = effective.range_px
            results.append(IndexCIResult(
                study_area=spec.study_area,
                index=index_band,
                month=spec.month,
                year=spec.year,
                tau=tau,
                is_primary_tau=tau == self.config.tau,
                engine=self.config.engine,
                n=observation.n,
                mean_index=observation.mean,
                sd=observation.sd,
                k_max=observation.k_max,
                cell_size=observation.cell_size,
                range_px=range_px,
                range_map_units=(
                    float(range_px * observation.cell_size)
                    if range_px is not None else float("nan")
                ),
                n_eff=effective.n_eff,
                df=ci_values[0],
                t_crit=ci_values[1],
                se=ci_values[2],
                ci_low=ci_values[3],
                ci_high=ci_values[4],
                naive_se=naive.se,
                naive_ci_low=naive.lower,
                naive_ci_high=naive.upper,
                flag_no_range=effective.flag_no_range,
                flag_low_n_eff=(
                    bool(effective.n_eff < self.config.min_n_eff)
                    if not effective.flag_no_range else False
                ),
            ))
        frame = correlogram.to_frame({
            "study_area": spec.study_area,
            "index": index_band,
            "month": spec.month,
            "year": spec.year,
        })
        return results, frame

    def save(self, results: pd.DataFrame, correlograms: pd.DataFrame) -> None:
        """Write result tables and per-index audit configuration."""
        for index_band in self.config.index_bands:
            output_dir = self.config.output_dir / index_band
            output_dir.mkdir(parents=True, exist_ok=True)
            results.loc[results["index"] == index_band].to_csv(
                output_dir / "results.csv", index=False
            )
            correlograms.loc[correlograms["index"] == index_band].to_csv(
                output_dir / "correlograms.csv", index=False
            )
            snapshot = self.config.to_dict()
            snapshot["index_band"] = index_band
            snapshot["output_dir"] = str(output_dir)
            with (output_dir / "config.json").open("w", encoding="utf-8") as stream:
                json.dump(snapshot, stream, indent=2)


def _error_result(
    spec: IndexObservationSpec,
    config: IndexAnalysisConfig,
    index_band: str,
    tau: float,
    error: str,
) -> dict[str, object]:
    """Create a result-shaped error row for a failed observation."""
    values: dict[str, object] = {
        field: None for field in IndexCIResult.__dataclass_fields__
    }
    values.update({
        "study_area": spec.study_area,
        "index": index_band,
        "month": spec.month,
        "year": spec.year,
        "tau": tau,
        "is_primary_tau": tau == config.tau,
        "engine": config.engine,
        "flag_no_range": False,
        "flag_low_n_eff": False,
        "error": error,
    })
    return values

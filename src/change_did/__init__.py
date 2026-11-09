"""Weighted fixed-effects difference-in-differences model on index change."""

from .analysis import ChangeDidAnalysis, DidResults, Variant
from .config import DidAnalysisConfig
from .data import (
    FILL_METHODS,
    fill_missing_se,
    flagged_se_report,
    load_change_results,
    validate_change_results,
)
from .fitting import build_design, compute_anomalies, fit_did, fit_weighted
from .models import FitTerm, WeightedFitResult
from .placebo import EVENT_TERM, PERSIST_TERM, run_placebo_space, run_placebo_spacetime
from .plotting import (
    plot_anomaly_heatmap,
    plot_change_trajectories,
    plot_combined_evidence,
    plot_observed_vs_counterfactual,
    plot_placebo_space,
    plot_placebo_spacetime,
    plot_sensitivity_forest,
    save_figure,
)

__all__ = [
    "EVENT_TERM",
    "FILL_METHODS",
    "PERSIST_TERM",
    "ChangeDidAnalysis",
    "DidAnalysisConfig",
    "DidResults",
    "FitTerm",
    "Variant",
    "WeightedFitResult",
    "build_design",
    "compute_anomalies",
    "fill_missing_se",
    "fit_did",
    "fit_weighted",
    "flagged_se_report",
    "load_change_results",
    "plot_anomaly_heatmap",
    "plot_change_trajectories",
    "plot_combined_evidence",
    "plot_observed_vs_counterfactual",
    "plot_placebo_space",
    "plot_placebo_spacetime",
    "plot_sensitivity_forest",
    "run_placebo_space",
    "run_placebo_spacetime",
    "save_figure",
    "validate_change_results",
]

"""Weighted fixed-effects difference-in-differences model on index change."""

from .analysis import MODEL_LABELS, ChangeDidAnalysis, DidResults, Variant
from .config import DidAnalysisConfig
from .data import (
    FILL_METHODS,
    fill_missing_se,
    flagged_se_report,
    load_change_results,
    validate_change_results,
)
from .fitting import (
    build_design,
    compute_anomalies,
    effect_levels,
    fit_did,
    fit_weighted,
    joint_wald_test,
    omitted_level_term,
)
from .models import (
    MODEL_PERIOD_ONLY,
    MODEL_SITE_PERIOD,
    MODEL_SPECS,
    FitTerm,
    JointTest,
    WeightedFitResult,
)
from .placebo import EVENT_TERM, PERSIST_TERM, run_placebo_space, run_placebo_spacetime
from .plotting import (
    plot_anomaly_heatmap,
    plot_change_trajectories,
    plot_combined_evidence,
    plot_combined_evidence_by_index,
    plot_observed_vs_counterfactual,
    plot_placebo_space,
    plot_placebo_spacetime,
    plot_sensitivity_forest,
    save_figure,
)

__all__ = [
    "EVENT_TERM",
    "FILL_METHODS",
    "MODEL_LABELS",
    "MODEL_PERIOD_ONLY",
    "MODEL_SITE_PERIOD",
    "MODEL_SPECS",
    "PERSIST_TERM",
    "ChangeDidAnalysis",
    "DidAnalysisConfig",
    "DidResults",
    "FitTerm",
    "JointTest",
    "Variant",
    "WeightedFitResult",
    "build_design",
    "compute_anomalies",
    "effect_levels",
    "fill_missing_se",
    "fit_did",
    "fit_weighted",
    "flagged_se_report",
    "joint_wald_test",
    "load_change_results",
    "omitted_level_term",
    "plot_anomaly_heatmap",
    "plot_change_trajectories",
    "plot_combined_evidence",
    "plot_combined_evidence_by_index",
    "plot_observed_vs_counterfactual",
    "plot_placebo_space",
    "plot_placebo_spacetime",
    "plot_sensitivity_forest",
    "run_placebo_space",
    "run_placebo_spacetime",
    "save_figure",
    "validate_change_results",
]

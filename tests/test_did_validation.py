"""Reproduce the handoff brief's NDVI validation targets to within 0.001.

A mismatch means the design, the SE fill, or the sigma_u^2 step differs from
the brief. Targets exist for NDVI only; the other indices run unchanged.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from change_did import ChangeDidAnalysis, DidAnalysisConfig, load_change_results

ROOT = Path(__file__).resolve().parents[1]
NDVI_RESULTS = ROOT / "outputs" / "change_ci" / "NDVI" / "results.csv"
TOL = 1e-3

pytestmark = pytest.mark.skipif(
    not NDVI_RESULTS.exists(), reason="NDVI change-CI results are not available"
)

# month: (beta, ci_low, ci_high, p, beta', ci_low', ci_high', sigma_u)
MAIN_TARGETS = {
    1: (-0.099, -0.268, 0.071, 0.24, -0.090, -0.255, 0.075, 0.0628),
    5: (-0.095, -0.141, -0.049, 2.2e-4, -0.039, -0.087, 0.008, 0.0149),
    9: (-0.111, -0.161, -0.061, 9.5e-5, -0.044, -0.094, 0.006, 0.0100),
    11: (-0.132, -0.195, -0.070, 1.7e-4, -0.015, -0.077, 0.048, 0.0177),
}

# month: (placebo_low, placebo_high, p, ratio)
SPACE_TARGETS = {
    1: (-0.078, 0.137, 1 / 7, 0.7),
    5: (-0.030, 0.022, 1 / 7, 3.1),
    9: (-0.014, 0.019, 1 / 7, 5.9),
    11: (-0.019, 0.019, 1 / 7, 6.8),
}

# month: (real, placebo_low, placebo_high, p)
SPACETIME_TARGETS = {
    1: (-0.096, -0.121, 0.137, 3 / 35),
    5: (-0.095, -0.036, 0.049, 1 / 35),
    9: (-0.111, -0.029, 0.043, 1 / 35),
    11: (-0.132, -0.072, 0.058, 1 / 35),
}

# variant: {month: (beta, ci_low, ci_high, df)}
SENSITIVITY_TARGETS = {
    "tau_0.02": {
        1: (-0.100, -0.268, 0.067, 28),
        5: (-0.095, -0.141, -0.048, 28),
        9: (-0.113, -0.160, -0.066, 28),
        11: (-0.132, -0.192, -0.072, 28),
    },
    "tau_0.1": {
        1: (-0.099, -0.267, 0.069, 28),
        5: (-0.094, -0.138, -0.049, 28),
        9: (-0.109, -0.158, -0.061, 28),
        11: (-0.131, -0.193, -0.070, 28),
    },
    "exclude_flagged": {
        1: (-0.087, -0.256, 0.081, 21),
        5: (-0.096, -0.144, -0.048, 23),
        9: (-0.112, -0.163, -0.061, 24),
        11: (-0.132, -0.196, -0.067, 24),
    },
    "n_eff_fill": {
        1: (-0.098, -0.265, 0.069, 28),
        5: (-0.095, -0.139, -0.052, 28),
        9: (-0.112, -0.161, -0.062, 28),
        11: (-0.132, -0.190, -0.073, 28),
    },
}


@pytest.fixture(scope="module")
def ndvi_run():
    config = DidAnalysisConfig.from_yaml(
        ROOT / "configs" / "change_did.yaml", project_root=ROOT
    )
    config = replace(
        config, input_paths=(NDVI_RESULTS,), indices=("NDVI",), primary_index="NDVI"
    )
    frame = load_change_results(config)
    return ChangeDidAnalysis(config).run(frame)


@pytest.mark.parametrize("month", sorted(MAIN_TARGETS))
def test_main_model_matches_targets(ndvi_run, month):
    main = ndvi_run.main
    rows = main.loc[
        (main["variant"] == "primary") & (main["month"] == month)
    ].set_index("term")
    event = rows.loc["d_event"]
    persist = rows.loc["d_persist"]
    beta, low, high, p, beta_p, low_p, high_p, sigma_u = MAIN_TARGETS[month]
    assert event["estimate"] == pytest.approx(beta, abs=TOL)
    assert event["ci_low"] == pytest.approx(low, abs=TOL)
    assert event["ci_high"] == pytest.approx(high, abs=TOL)
    assert event["p_value"] == pytest.approx(p, abs=5e-3)
    assert event["sigma_u"] == pytest.approx(sigma_u, abs=TOL)
    assert event["df"] == 28
    assert persist["estimate"] == pytest.approx(beta_p, abs=TOL)
    assert persist["ci_low"] == pytest.approx(low_p, abs=TOL)
    assert persist["ci_high"] == pytest.approx(high_p, abs=TOL)


@pytest.mark.parametrize("month", sorted(SPACE_TARGETS))
def test_placebo_space_matches_targets(ndvi_run, month):
    placebo = ndvi_run.placebo_space
    rows = placebo.loc[placebo["month"] == month]
    low, high, p, ratio = SPACE_TARGETS[month]
    estimates = rows.loc[~rows["is_real"], "estimate"]
    assert len(rows) == 7
    assert estimates.min() == pytest.approx(low, abs=TOL)
    assert estimates.max() == pytest.approx(high, abs=TOL)
    assert rows["p_value"].iloc[0] == pytest.approx(p, abs=5e-4)
    assert rows["ratio_to_largest_placebo"].iloc[0] == pytest.approx(ratio, abs=0.05)


@pytest.mark.parametrize("month", sorted(SPACETIME_TARGETS))
def test_placebo_spacetime_matches_targets(ndvi_run, month):
    placebo = ndvi_run.placebo_spacetime
    rows = placebo.loc[placebo["month"] == month]
    real, low, high, p = SPACETIME_TARGETS[month]
    estimates = rows.loc[~rows["is_real"], "estimate"]
    assert len(rows) == 35
    assert rows.loc[rows["is_real"], "estimate"].iloc[0] == pytest.approx(real, abs=TOL)
    assert estimates.min() == pytest.approx(low, abs=TOL)
    assert estimates.max() == pytest.approx(high, abs=TOL)
    assert rows["p_value"].iloc[0] == pytest.approx(p, abs=5e-4)


@pytest.mark.parametrize("variant", sorted(SENSITIVITY_TARGETS))
@pytest.mark.parametrize("month", sorted(MAIN_TARGETS))
def test_sensitivity_matches_targets(ndvi_run, variant, month):
    main = ndvi_run.main
    row = main.loc[
        (main["variant"] == variant)
        & (main["month"] == month)
        & (main["term"] == "d_event")
    ].iloc[0]
    beta, low, high, df = SENSITIVITY_TARGETS[variant][month]
    assert row["estimate"] == pytest.approx(beta, abs=TOL)
    assert row["ci_low"] == pytest.approx(low, abs=TOL)
    assert row["ci_high"] == pytest.approx(high, abs=TOL)
    assert row["df"] == df


def test_flagged_count_matches_brief(ndvi_run):
    report = ndvi_run.flagged_report
    assert int(report.loc[report["index"] == "NDVI", "total"].iloc[0]) == 22

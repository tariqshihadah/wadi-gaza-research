"""Reproduce the update brief's NDVI validation targets to within 0.001.

Targets are the event estimates (beta, 2023-24) with 95% CIs for both model
specifications at tau = 0.05 with the largest-SE fill, including the Step 1
change (both Wadi Gaza post-event rows excluded from mean(SE^2)). A mismatch
means the design, the SE fill, or the sigma_u^2 step differs from the brief.
The brief's earlier placebo and sensitivity targets no longer apply exactly,
so those runs are checked structurally and their values are reported in the
saved outputs rather than pinned here. Targets exist for NDVI only; the other
indices run unchanged.
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

# model: {month: (beta, ci_low, ci_high)}
MAIN_TARGETS = {
    "site_period": {
        1: (-0.099, -0.268, 0.071),
        5: (-0.095, -0.141, -0.049),
        9: (-0.111, -0.162, -0.060),
        11: (-0.132, -0.195, -0.069),
    },
    "period_only": {
        1: (-0.088, -0.234, 0.058),
        5: (-0.082, -0.123, -0.040),
        9: (-0.101, -0.148, -0.053),
        11: (-0.128, -0.185, -0.072),
    },
}

# model: residual degrees of freedom (42 obs; 14 or 8 parameters)
MODEL_DF = {"site_period": 28, "period_only": 34}

MONTHS = (1, 5, 9, 11)


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


@pytest.mark.parametrize("model", sorted(MAIN_TARGETS))
@pytest.mark.parametrize("month", MONTHS)
def test_main_model_matches_targets(ndvi_run, model, month):
    main = ndvi_run.main
    rows = main.loc[
        (main["model"] == model)
        & (main["variant"] == "primary")
        & (main["month"] == month)
    ].set_index("term")
    event = rows.loc["d_event"]
    beta, low, high = MAIN_TARGETS[model][month]
    assert event["estimate"] == pytest.approx(beta, abs=TOL)
    assert event["ci_low"] == pytest.approx(low, abs=TOL)
    assert event["ci_high"] == pytest.approx(high, abs=TOL)
    assert event["df"] == MODEL_DF[model]
    assert "d_persist" in rows.index


@pytest.mark.parametrize("model", sorted(MODEL_DF))
@pytest.mark.parametrize("month", MONTHS)
def test_effects_table_structure(ndvi_run, model, month):
    effects = ndvi_run.effects
    rows = effects.loc[
        (effects["model"] == model) & (effects["month"] == month)
    ]
    counts = rows.groupby("group").size().to_dict()
    expected = {"pair": 6, "pair_joint": 1}
    if model == "site_period":
        expected.update({"site": 7, "site_joint": 1})
    assert counts == expected
    for group in ("site", "pair"):
        if group not in counts:
            continue
        block = rows.loc[rows["group"] == group]
        # Deviation-coded effects sum to zero across levels.
        assert abs(block["estimate"].sum()) < 1e-9
        assert block["derived"].sum() == 1
    joints = rows.loc[rows["group"].str.endswith("_joint")]
    assert joints["p_value"].between(0.0, 1.0).all()
    assert joints["df_num"].tolist() == ([6, 5] if model == "site_period" else [5])


@pytest.mark.parametrize("model", sorted(MODEL_DF))
@pytest.mark.parametrize("month", MONTHS)
def test_placebo_structure(ndvi_run, model, month):
    space = ndvi_run.placebo_space
    rows = space.loc[(space["model"] == model) & (space["month"] == month)]
    assert len(rows) == 7
    assert rows["is_real"].sum() == 1
    assert 1 / 7 <= rows["p_value"].iloc[0] <= 1.0

    spacetime = ndvi_run.placebo_spacetime
    rows = spacetime.loc[
        (spacetime["model"] == model) & (spacetime["month"] == month)
    ]
    assert len(rows) == 35
    assert rows["is_real"].sum() == 1
    assert 1 / 35 <= rows["p_value"].iloc[0] <= 1.0


@pytest.mark.parametrize("model", sorted(MODEL_DF))
@pytest.mark.parametrize(
    "variant", ["tau_0.02", "tau_0.1", "exclude_flagged", "n_eff_fill"]
)
def test_sensitivity_structure(ndvi_run, model, variant):
    main = ndvi_run.main
    rows = main.loc[
        (main["model"] == model)
        & (main["variant"] == variant)
        & (main["term"] == "d_event")
    ]
    assert sorted(rows["month"]) == sorted(MONTHS)
    assert rows["estimate"].notna().all()
    if variant != "exclude_flagged":
        assert (rows["df"] == MODEL_DF[model]).all()


def test_flagged_count_matches_brief(ndvi_run):
    report = ndvi_run.flagged_report
    assert int(report.loc[report["index"] == "NDVI", "total"].iloc[0]) == 22

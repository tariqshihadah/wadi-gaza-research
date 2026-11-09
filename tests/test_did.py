import numpy as np
import pandas as pd
import pytest
from scipy import stats

from change_did.data import fill_missing_se, flagged_se_report, validate_change_results
from change_did.fitting import (
    build_design,
    compute_anomalies,
    effect_levels,
    fit_did,
    fit_weighted,
    joint_wald_test,
    omitted_level_term,
)
from change_did.placebo import run_placebo_space, run_placebo_spacetime

SITES = ("WadiGaza", "SiteA", "SiteB", "SiteC", "SiteD", "SiteE", "SiteF")
YEARS = tuple(range(2019, 2025))


def _grid(
    beta: float = 0.0,
    beta_persist: float = 0.0,
    se: float = 0.02,
    site_slope: float = 0.01,
) -> pd.DataFrame:
    """Build one month x tau subset with known fixed effects and no noise."""
    rows = []
    for s, site in enumerate(SITES):
        for t, year_start in enumerate(YEARS):
            value = site_slope * s - 0.005 * t
            if site == "WadiGaza" and year_start == 2023:
                value += beta
            if site == "WadiGaza" and year_start == 2024:
                value += beta_persist
            rows.append({
                "study_area": site, "index": "NDVI", "month": 5,
                "year_start": year_start, "year_end": year_start + 1,
                "tau": 0.05, "mean_change": value, "se": se, "sd": 0.1,
                "flag_no_range": False,
            })
    return pd.DataFrame(rows)


def test_validate_accepts_complete_grid(did_config_factory):
    config = did_config_factory(
        indices=("NDVI",), primary_index="NDVI", months=(5,), supplementary_months=()
    )
    validate_change_results(_grid(), config)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda f: f.drop(index=[0]), "Expected"),
        (lambda f: f.assign(study_area=f["study_area"].where(f.index != 0, "SiteA")),
         "Duplicate"),
        (lambda f: f.assign(year_end=f["year_end"] + (f["year_start"] == 2019)),
         "year_end"),
        (lambda f: f.assign(se=f["se"].where(f.index != 0, np.nan)),
         "flag_no_range"),
        (lambda f: f.assign(mean_change=f["mean_change"].where(f.index != 0, np.nan)),
         "mean_change"),
    ],
)
def test_validate_rejects_broken_inputs(did_config_factory, mutate, message):
    config = did_config_factory(
        indices=("NDVI",), primary_index="NDVI", months=(5,), supplementary_months=()
    )
    with pytest.raises(ValueError, match=message):
        validate_change_results(mutate(_grid()), config)


def test_fill_missing_se_methods():
    frame = _grid()
    frame.loc[[3, 17], "se"] = np.nan
    frame.loc[[3, 17], "flag_no_range"] = True
    frame.loc[0, "se"] = 0.09

    filled, count = fill_missing_se(frame, "max_se", fill_n_eff=5)
    assert count == 2
    assert filled.loc[[3, 17], "se"].eq(0.09).all()

    filled, count = fill_missing_se(frame, "n_eff_fill", fill_n_eff=5)
    assert count == 2
    assert filled.loc[3, "se"] == pytest.approx(0.1 / np.sqrt(5))

    dropped, count = fill_missing_se(frame, "drop_flagged", fill_n_eff=5)
    assert count == 2
    assert len(dropped) == len(frame) - 2
    assert dropped["se"].notna().all()

    with pytest.raises(ValueError, match="Unknown fill method"):
        fill_missing_se(frame, "zero_fill", fill_n_eff=5)


def test_flagged_se_report_counts_and_warns(did_config_factory, caplog):
    config = did_config_factory(
        indices=("NDVI",), primary_index="NDVI", months=(5,),
        supplementary_months=(), expected_flagged_primary=5,
    )
    frame = _grid()
    frame.loc[[3, 17], "se"] = np.nan
    frame.loc[[3, 17], "flag_no_range"] = True
    with caplog.at_level("WARNING", logger="change_did.data"):
        report = flagged_se_report(frame, config)
    assert report.loc[report["index"] == "NDVI", "total"].iloc[0] == 2
    assert "expected 5" in caplog.text


def test_build_design_columns_and_dropped_indicators():
    frame = _grid()
    X, columns, dropped = build_design(frame, {
        "d_event": ("WadiGaza", (2023, 2024)),
        "d_missing": ("WadiGaza", (2030, 2031)),
    })
    assert X.shape == (42, 13)
    assert columns[0] == "intercept"
    assert sum(name.startswith("site_") for name in columns) == 6
    assert sum(name.startswith("pair_") for name in columns) == 5
    assert columns[-1] == "d_event"
    assert dropped == ("d_missing",)
    assert X[:, -1].sum() == 1.0
    # Deviation coding: every effect column sums to zero over the balanced grid.
    effect_columns = [
        idx for idx, name in enumerate(columns)
        if name.startswith(("site_", "pair_"))
    ]
    assert np.allclose(X[:, effect_columns].sum(axis=0), 0.0)


def test_build_design_without_site_effects():
    frame = _grid()
    X, columns, dropped = build_design(
        frame, {"d_event": ("WadiGaza", (2023, 2024))}, site_effects=False
    )
    assert X.shape == (42, 7)
    assert not any(name.startswith("site_") for name in columns)
    assert sum(name.startswith("pair_") for name in columns) == 5
    assert dropped == ()


def test_effect_levels_orders_blocks_and_marks_omitted():
    frame = _grid()
    blocks = effect_levels(frame)
    assert set(blocks) == {"site", "pair"}
    site_levels = blocks["site"]
    assert site_levels[0] == ("SiteA", None)
    assert site_levels[-1] == ("WadiGaza", "site_WadiGaza")
    pair_levels = blocks["pair"]
    assert pair_levels[0] == ("2019_2020", None)
    assert pair_levels[-1] == ("2024_2025", "pair_2024_2025")
    assert "site" not in effect_levels(frame, site_effects=False)


def test_fit_did_recovers_known_effects():
    frame = _grid(beta=-0.1, beta_persist=-0.04)
    fit = fit_did(
        frame,
        {"d_event": ("WadiGaza", (2023, 2024)), "d_persist": ("WadiGaza", (2024, 2025))},
        alpha=0.05,
    )
    assert fit.terms["d_event"].estimate == pytest.approx(-0.1, abs=1e-10)
    assert fit.terms["d_persist"].estimate == pytest.approx(-0.04, abs=1e-10)
    assert fit.df == 28
    assert fit.n_obs == 42
    assert fit.sigma_u == 0.0
    assert fit.sigma_u_clipped
    assert fit.site_effects


def test_fit_did_period_only_recovers_known_effects():
    # Without site-level drift the period-only model is correctly specified.
    frame = _grid(beta=-0.1, beta_persist=-0.04, site_slope=0.0)
    fit = fit_did(
        frame,
        {"d_event": ("WadiGaza", (2023, 2024)), "d_persist": ("WadiGaza", (2024, 2025))},
        alpha=0.05,
        site_effects=False,
    )
    assert fit.terms["d_event"].estimate == pytest.approx(-0.1, abs=1e-10)
    assert fit.terms["d_persist"].estimate == pytest.approx(-0.04, abs=1e-10)
    assert fit.df == 34
    assert fit.n_obs == 42
    assert not fit.site_effects
    assert not any(name.startswith("site_") for name in fit.columns)


def test_fit_did_reports_deviation_coded_effects():
    frame = _grid(beta=-0.1)
    fit = fit_did(frame, {"d_event": ("WadiGaza", (2023, 2024))}, alpha=0.05)
    # Site s has drift 0.01 * s; deviation effects are relative to the average.
    offsets = {site: 0.01 * s for s, site in enumerate(SITES)}
    mean_offset = np.mean(list(offsets.values()))
    for site in sorted(SITES)[1:]:  # SiteA sorts first and is the omitted level
        assert fit.terms[f"site_{site}"].estimate == pytest.approx(
            offsets[site] - mean_offset, abs=1e-10
        )
    blocks = effect_levels(frame)
    site_columns = [column for _, column in blocks["site"] if column is not None]
    derived = omitted_level_term(fit, site_columns, "site_SiteA", alpha=0.05)
    assert derived.estimate == pytest.approx(offsets["SiteA"] - mean_offset, abs=1e-10)
    # Deviation-coded effects sum to zero across all levels.
    total = derived.estimate + sum(
        fit.terms[column].estimate for column in site_columns
    )
    assert total == pytest.approx(0.0, abs=1e-10)


def test_joint_wald_test_matches_manual_computation():
    rng = np.random.default_rng(11)
    frame = _grid(beta=-0.1)
    frame["mean_change"] += rng.normal(scale=0.01, size=len(frame))
    fit = fit_did(frame, {"d_event": ("WadiGaza", (2023, 2024))}, alpha=0.05)
    blocks = effect_levels(frame)
    site_columns = [column for _, column in blocks["site"] if column is not None]
    test = joint_wald_test(fit, site_columns, "site")
    indices = [fit.columns.index(column) for column in site_columns]
    b = np.array([fit.coefficients[column] for column in site_columns])
    S = fit.cov[np.ix_(indices, indices)]
    statistic = float(b @ np.linalg.solve(S, b)) / len(indices)
    assert test.statistic == pytest.approx(statistic)
    assert test.df_num == 6
    assert test.df_den == fit.df
    assert test.p_value == pytest.approx(
        float(stats.f.sf(statistic, 6, fit.df))
    )
    # The grid has strong site drift, so the joint test must reject.
    assert test.p_value < 0.01


def test_sigma_exclusion_covers_every_indicator_cell():
    rng = np.random.default_rng(3)
    frame = _grid(beta=-0.1, beta_persist=-0.04)
    frame["mean_change"] += rng.normal(scale=0.03, size=len(frame))
    indicators = {
        "d_event": ("WadiGaza", (2023, 2024)),
        "d_persist": ("WadiGaza", (2024, 2025)),
    }
    baseline = fit_did(frame, indicators, alpha=0.05)
    # Inflating the persist cell's SE must not move sigma_u: the row is fit
    # exactly by its own indicator and is excluded from mean(SE^2).
    inflated = frame.copy()
    persist_row = (
        inflated["study_area"].eq("WadiGaza") & inflated["year_start"].eq(2024)
    )
    inflated.loc[persist_row, "se"] = 10.0
    fit = fit_did(inflated, indicators, alpha=0.05)
    assert fit.sigma_u == pytest.approx(baseline.sigma_u)


def test_fit_weighted_matches_brief_reference():
    rng = np.random.default_rng(7)
    frame = _grid()
    X, columns, _ = build_design(frame, {"d_event": ("WadiGaza", (2023, 2024))})
    y = rng.normal(scale=0.05, size=len(frame))
    se = rng.uniform(0.01, 0.05, size=len(frame))
    treated = (
        frame["study_area"].eq("WadiGaza") & frame["year_start"].eq(2023)
    ).to_numpy()
    term_idx = columns.index("d_event")

    # Reference implementation from the handoff brief.
    n, k = X.shape
    dof = n - k
    b_ols = np.linalg.lstsq(X, y, rcond=None)[0]
    s2 = ((y - X @ b_ols) ** 2).sum() / dof
    sigma_u2 = max(0.0, s2 - (se[~treated] ** 2).mean())
    w = 1.0 / (sigma_u2 + se**2)
    XtW = X.T * w
    cov = np.linalg.inv(XtW @ X)
    b = cov @ XtW @ y
    est, sd_b = b[term_idx], np.sqrt(cov[term_idx, term_idx])
    t_crit = stats.t.ppf(0.975, dof)

    fit = fit_weighted(X, y, se, treated, {"d_event": term_idx}, alpha=0.05)
    term = fit.terms["d_event"]
    assert term.estimate == pytest.approx(est)
    assert term.se == pytest.approx(sd_b)
    assert term.ci_low == pytest.approx(est - t_crit * sd_b)
    assert term.ci_high == pytest.approx(est + t_crit * sd_b)
    assert fit.sigma_u == pytest.approx(np.sqrt(sigma_u2))
    assert fit.df == dof


def test_compute_anomalies_isolates_event_cells():
    frame = _grid(beta=-0.1, beta_persist=-0.04)
    fit = fit_did(
        frame,
        {"d_event": ("WadiGaza", (2023, 2024)), "d_persist": ("WadiGaza", (2024, 2025))},
        alpha=0.05,
    )
    anomalies = compute_anomalies(frame, fit)
    wadi = anomalies["study_area"].eq("WadiGaza")
    event = wadi & anomalies["year_start"].eq(2023)
    persist = wadi & anomalies["year_start"].eq(2024)
    assert anomalies.loc[event, "anomaly"].iloc[0] == pytest.approx(-0.1, abs=1e-10)
    assert anomalies.loc[persist, "anomaly"].iloc[0] == pytest.approx(-0.04, abs=1e-10)
    assert anomalies.loc[~event & ~persist, "anomaly"].abs().max() == pytest.approx(
        0.0, abs=1e-10
    )
    assert (
        anomalies["mean_change"] - anomalies["counterfactual"]
    ).equals(anomalies["anomaly"])


def test_compute_anomalies_period_only_counterfactual():
    frame = _grid(beta=-0.1, beta_persist=-0.04, site_slope=0.0)
    fit = fit_did(
        frame,
        {"d_event": ("WadiGaza", (2023, 2024)), "d_persist": ("WadiGaza", (2024, 2025))},
        alpha=0.05,
        site_effects=False,
    )
    anomalies = compute_anomalies(frame, fit)
    # Without site drift the period-only counterfactual is exact everywhere.
    wadi = anomalies["study_area"].eq("WadiGaza")
    event = wadi & anomalies["year_start"].eq(2023)
    assert anomalies.loc[event, "anomaly"].iloc[0] == pytest.approx(-0.1, abs=1e-10)
    non_event = ~(wadi & anomalies["year_start"].isin([2023, 2024]))
    assert anomalies.loc[non_event, "anomaly"].abs().max() == pytest.approx(
        0.0, abs=1e-10
    )


@pytest.mark.parametrize("site_effects", [True, False])
def test_placebo_space_rows_and_p_value(did_config_factory, site_effects):
    config = did_config_factory()
    frame = _grid(beta=-0.1, beta_persist=-0.04, site_slope=0.0)
    result = run_placebo_space(
        frame, real_estimate=-0.1, config=config, site_effects=site_effects
    )
    assert len(result) == 7
    assert result["is_real"].sum() == 1
    placebos = result.loc[~result["is_real"], "estimate"]
    # The noiseless grid has no effect anywhere else, so every placebo is zero
    # and only the real estimate falls at or below itself.
    assert placebos.abs().max() == pytest.approx(0.0, abs=1e-10)
    assert result["p_value"].iloc[0] == pytest.approx(1 / 7)


@pytest.mark.parametrize("site_effects", [True, False])
def test_placebo_spacetime_rows_and_p_value(did_config_factory, site_effects):
    config = did_config_factory()
    frame = _grid(beta=-0.1, beta_persist=-0.04, site_slope=0.0)
    result = run_placebo_spacetime(frame, config, site_effects=site_effects)
    assert len(result) == 35
    assert result["is_real"].sum() == 1
    real = result.loc[result["is_real"]].iloc[0]
    assert real["year_start"] == 2023
    assert real["estimate"] == pytest.approx(-0.1, abs=1e-10)
    assert result["p_value"].iloc[0] == pytest.approx(1 / 35)
    # The persistence pair is dropped before fitting.
    assert not result["year_start"].eq(2024).any()

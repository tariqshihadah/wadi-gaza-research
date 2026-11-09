import numpy as np
import pandas as pd
import pytest
from scipy import stats

from change_did.data import fill_missing_se, flagged_se_report, validate_change_results
from change_did.fitting import build_design, compute_anomalies, fit_did, fit_weighted
from change_did.placebo import run_placebo_space, run_placebo_spacetime

SITES = ("WadiGaza", "SiteA", "SiteB", "SiteC", "SiteD", "SiteE", "SiteF")
YEARS = tuple(range(2019, 2025))


def _grid(beta: float = 0.0, beta_persist: float = 0.0, se: float = 0.02) -> pd.DataFrame:
    """Build one month x tau subset with known fixed effects and no noise."""
    rows = []
    for s, site in enumerate(SITES):
        for t, year_start in enumerate(YEARS):
            value = 0.01 * s - 0.005 * t
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


def test_fit_did_recovers_known_effects():
    frame = _grid(beta=-0.1, beta_persist=-0.04)
    fit = fit_did(
        frame,
        {"d_event": ("WadiGaza", (2023, 2024)), "d_persist": ("WadiGaza", (2024, 2025))},
        [("WadiGaza", (2023, 2024))],
        alpha=0.05,
    )
    assert fit.terms["d_event"].estimate == pytest.approx(-0.1, abs=1e-10)
    assert fit.terms["d_persist"].estimate == pytest.approx(-0.04, abs=1e-10)
    assert fit.df == 28
    assert fit.n_obs == 42
    assert fit.sigma_u == 0.0
    assert fit.sigma_u_clipped


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
        [("WadiGaza", (2023, 2024))],
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


def test_placebo_space_rows_and_p_value(did_config_factory):
    config = did_config_factory()
    frame = _grid(beta=-0.1, beta_persist=-0.04)
    result = run_placebo_space(frame, real_estimate=-0.1, config=config)
    assert len(result) == 7
    assert result["is_real"].sum() == 1
    placebos = result.loc[~result["is_real"], "estimate"]
    # The noiseless grid has no effect anywhere else, so every placebo is zero
    # and only the real estimate falls at or below itself.
    assert placebos.abs().max() == pytest.approx(0.0, abs=1e-10)
    assert result["p_value"].iloc[0] == pytest.approx(1 / 7)


def test_placebo_spacetime_rows_and_p_value(did_config_factory):
    config = did_config_factory()
    frame = _grid(beta=-0.1, beta_persist=-0.04)
    result = run_placebo_spacetime(frame, config)
    assert len(result) == 35
    assert result["is_real"].sum() == 1
    real = result.loc[result["is_real"]].iloc[0]
    assert real["year_start"] == 2023
    assert real["estimate"] == pytest.approx(-0.1, abs=1e-10)
    assert result["p_value"].iloc[0] == pytest.approx(1 / 35)
    # The persistence pair is dropped before fitting.
    assert not result["year_start"].eq(2024).any()

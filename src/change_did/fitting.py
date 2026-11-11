"""Design construction and the weighted fixed-effects fit on site-level changes."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import replace

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS, WLS, RegressionResultsWrapper

from .models import FitTerm, JointTest, WeightedFitResult

LOGGER = logging.getLogger(__name__)

Cell = tuple[str, tuple[int, int]]


def build_design(
    frame: pd.DataFrame,
    indicators: Mapping[str, Cell],
    *,
    site_effects: bool = True,
) -> tuple[np.ndarray, list[str], tuple[str, ...]]:
    """Build the deviation-coded fixed-effects design matrix with event indicators.

    Columns are an intercept, sum-to-zero (deviation) coded site dummies when
    ``site_effects`` is true (the first sorted site is the omitted level),
    deviation-coded year-pair dummies (the first sorted pair is the omitted
    level), and one indicator per entry of ``indicators`` mapping a term name
    to its (site, (year_start, year_end)) cell. Each coded column equals the
    plain dummy minus the omitted level's dummy, so every reported effect is
    relative to the average site or year pair, and the omitted level's effect
    is minus the sum of the block's coefficients. The event indicators are
    identical under either coding. Indicators whose cell is absent from
    ``frame`` are dropped and reported in the returned tuple.
    """
    columns = ["intercept"]
    data = [np.ones(len(frame))]
    if site_effects:
        sites = sorted(frame["study_area"].unique())
        omitted = frame["study_area"].eq(sites[0]).to_numpy(dtype=float)
        for site in sites[1:]:
            columns.append(f"site_{site}")
            data.append(frame["study_area"].eq(site).to_numpy(dtype=float) - omitted)
    pairs = sorted(set(zip(frame["year_start"], frame["year_end"])))
    omitted = frame["year_start"].eq(pairs[0][0]).to_numpy(dtype=float)
    for year_start, year_end in pairs[1:]:
        columns.append(f"pair_{year_start}_{year_end}")
        data.append(frame["year_start"].eq(year_start).to_numpy(dtype=float) - omitted)
    dropped: list[str] = []
    for name, cell in indicators.items():
        column = _cell_mask(frame, cell).astype(float)
        if column.any():
            columns.append(name)
            data.append(column)
        else:
            dropped.append(name)
    return np.column_stack(data), columns, tuple(dropped)


def effect_levels(
    frame: pd.DataFrame, *, site_effects: bool = True
) -> dict[str, tuple[tuple[str, str | None], ...]]:
    """Return each effect block's ordered (level label, design column) pairs.

    Blocks are ``"site"`` (when ``site_effects`` is true) and ``"pair"``. The
    omitted (first sorted) level carries column ``None``; its deviation-coded
    effect is minus the sum of the block's fitted coefficients (see
    :func:`omitted_level_term`).
    """
    blocks: dict[str, tuple[tuple[str, str | None], ...]] = {}
    if site_effects:
        sites = sorted(frame["study_area"].unique())
        blocks["site"] = tuple(
            (site, f"site_{site}" if position else None)
            for position, site in enumerate(sites)
        )
    pairs = sorted(set(zip(frame["year_start"], frame["year_end"])))
    blocks["pair"] = tuple(
        (f"{year_start}_{year_end}", f"pair_{year_start}_{year_end}" if position else None)
        for position, (year_start, year_end) in enumerate(pairs)
    )
    return blocks


def fit_weighted(
    X: np.ndarray,
    y: np.ndarray,
    se: np.ndarray,
    term_indices: Mapping[str, int],
    alpha: float,
    columns: Sequence[str] | None = None,
) -> WeightedFitResult:
    """Fit WLS with Hedges' leverage-adjusted method-of-moments variance.

    OLS residuals and leverages give ``sigma_u2 = max(0,
    (RSS - sum((1 - h) * se^2)) / (n - k))``. Weights are
    ``1 / (sigma_u2 + se^2)`` and are treated as fixed inverse variances:
    covariance is ``(X'WX)^-1``, without residual rescaling. Statsmodels
    supplies the fit and t inference with ``n - k`` degrees of freedom.
    When ``columns`` is given, retain the native fit, coefficients, and
    covariance for derived contrasts and joint tests.
    """
    if X.ndim != 2:
        raise ValueError("Design must be a two-dimensional array")
    n, k = X.shape
    if y.shape != (n,) or se.shape != (n,):
        raise ValueError("Response and measurement SEs must match the design rows")
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError("Design and response must be finite")
    if not np.isfinite(se).all() or np.any(se <= 0):
        raise ValueError("Measurement SEs must be finite and positive")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one")
    dof = n - k
    if dof <= 0:
        raise ValueError(f"Model has no residual degrees of freedom: n={n}, k={k}")
    if k == 0 or np.linalg.matrix_rank(X) != k:
        raise ValueError("Model design must have full column rank")
    if columns is not None and (len(columns) != k or len(set(columns)) != k):
        raise ValueError("columns must contain one unique name per design column")
    if any(idx < 0 or idx >= k for idx in term_indices.values()):
        raise ValueError("Term indices must identify design columns")
    ols = OLS(y, X, missing="raise").fit()
    leverage = ols.get_influence().hat_matrix_diag
    with np.errstate(over="raise", invalid="raise"):
        measurement_variance = se**2
        sigma_u2 = float(
            (ols.ssr - np.dot(1.0 - leverage, measurement_variance)) / dof
        )
    clipped = sigma_u2 < 0
    if clipped:
        LOGGER.warning(
            "sigma_u^2 clipped to zero (HE estimate=%.3g): "
            "measurement variances exceed residual scatter",
            sigma_u2,
        )
        sigma_u2 = 0.0
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        weights = 1.0 / (sigma_u2 + measurement_variance)
    if not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError("Model weights must be finite and positive")
    regression = WLS(y, X, weights=weights, missing="raise").fit(
        cov_type="fixed scale", cov_kwds={"scale": 1.0}, use_t=True
    )
    intervals = regression.conf_int(alpha=alpha)
    terms: dict[str, FitTerm] = {}
    for name, idx in term_indices.items():
        terms[name] = FitTerm(
            term=name,
            estimate=float(regression.params[idx]),
            se=float(regression.bse[idx]),
            ci_low=float(intervals[idx, 0]),
            ci_high=float(intervals[idx, 1]),
            p_value=float(regression.pvalues[idx]),
        )
    return WeightedFitResult(
        terms=terms,
        sigma_u=float(np.sqrt(sigma_u2)),
        sigma_u_clipped=clipped,
        df=dof,
        n_obs=n,
        coefficients=(
            {name: float(value) for name, value in zip(columns, regression.params)}
            if columns is not None else {}
        ),
        columns=tuple(columns) if columns is not None else (),
        cov=regression.cov_params() if columns is not None else None,
        regression=regression if columns is not None else None,
    )


def fit_did(
    frame: pd.DataFrame,
    indicators: Mapping[str, Cell],
    alpha: float,
    *,
    site_effects: bool = True,
) -> WeightedFitResult:
    """Fit the model on one prepared (SE-handled) subset of site-level changes.

    ``indicators`` maps term names to event cells; ``site_effects`` selects
    the site + period model (true) or the period-only model (false). Every
    indicator cell has leverage one, so it contributes neither residual scatter
    nor measurement variance to the HE estimate. Indicators whose cell is
    absent from ``frame`` are dropped from the design and recorded on the result.
    Full estimates are returned for every design column.
    """
    X, columns, dropped = build_design(frame, indicators, site_effects=site_effects)
    term_indices = {name: idx for idx, name in enumerate(columns)}
    result = fit_weighted(
        X,
        frame["mean_change"].to_numpy(dtype=float),
        frame["se"].to_numpy(dtype=float),
        term_indices,
        alpha,
        columns=columns,
    )
    return replace(result, dropped_terms=dropped, site_effects=site_effects)


def omitted_level_term(
    fit: WeightedFitResult, block_columns: Sequence[str], name: str, alpha: float
) -> FitTerm:
    """Return the omitted level's deviation-coded effect for one block.

    Under sum-to-zero coding the omitted level's effect is minus the sum of
    the block's coefficients; its variance is the sum of the block's
    covariance entries. Intervals use the fit's t distribution.
    """
    indices = _block_indices(fit, block_columns)
    contrast = np.zeros(len(fit.columns))
    contrast[indices] = -1.0
    test = _regression(fit).t_test(contrast, use_t=True)
    interval = test.conf_int(alpha=alpha)[0]
    return FitTerm(
        term=name,
        estimate=float(np.asarray(test.effect).item()),
        se=float(np.asarray(test.sd).item()),
        ci_low=float(interval[0]),
        ci_high=float(interval[1]),
        p_value=float(np.asarray(test.pvalue).item()),
    )


def joint_wald_test(
    fit: WeightedFitResult, block_columns: Sequence[str], name: str
) -> JointTest:
    """Return the joint Wald F-test that one block's effects are all zero.

    The statistic is ``b' S^-1 b / q`` over the block's coefficients and
    covariance, referred to an F(q, n - k) distribution, consistent with the
    fit's weights-as-known covariance and t intervals. The hypothesis is the
    same under reference or deviation coding.
    """
    indices = _block_indices(fit, block_columns)
    test = _regression(fit).f_test(np.eye(len(fit.columns))[indices])
    return JointTest(
        name=name,
        statistic=float(np.asarray(test.fvalue).item()),
        df_num=int(test.df_num),
        df_den=int(test.df_denom),
        p_value=float(np.asarray(test.pvalue).item()),
    )


def compute_anomalies(frame: pd.DataFrame, fit: WeightedFitResult) -> pd.DataFrame:
    """Return each cell's deviation from the fitted fixed-effects counterfactual.

    The counterfactual is the fitted intercept plus the fit's fixed effects
    (site and year-pair, or year-pair only for the period-only model), with
    every event-indicator contribution zeroed. At non-event cells the anomaly
    is the fit's residual; at an event cell it is the indicator estimate plus
    that cell's residual.
    """
    if not fit.coefficients:
        raise ValueError("Fit has no stored coefficients; refit via fit_did")
    X, columns, _ = build_design(frame, {}, site_effects=fit.site_effects)
    b = np.array([fit.coefficients[column] for column in columns])
    result = frame[["study_area", "year_start", "year_end", "mean_change"]].copy()
    result["counterfactual"] = X @ b
    result["anomaly"] = result["mean_change"] - result["counterfactual"]
    return result


def _block_indices(fit: WeightedFitResult, block_columns: Sequence[str]) -> np.ndarray:
    """Return the design indices for one block, validating the stored fit."""
    if fit.cov is None or not fit.columns:
        raise ValueError("Fit has no stored covariance; refit via fit_did")
    if not block_columns or len(set(block_columns)) != len(block_columns):
        raise ValueError("A contrast block must contain distinct design columns")
    return np.array([fit.columns.index(column) for column in block_columns])


def _regression(fit: WeightedFitResult) -> RegressionResultsWrapper:
    if fit.regression is None:
        raise ValueError("Fit has no stored statsmodels result; refit via fit_did")
    return fit.regression


def _cell_mask(frame: pd.DataFrame, cell: Cell) -> np.ndarray:
    """Return the boolean row mask for one site x year-pair cell."""
    site, (year_start, year_end) = cell
    return (
        frame["study_area"].eq(site)
        & frame["year_start"].eq(year_start)
        & frame["year_end"].eq(year_end)
    ).to_numpy()

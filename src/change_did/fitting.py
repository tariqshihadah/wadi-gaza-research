"""Design construction and the weighted fixed-effects fit on site-level changes."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from scipy import stats

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
    exclude_from_sigma: np.ndarray,
    term_indices: Mapping[str, int],
    alpha: float,
    columns: Sequence[str] | None = None,
) -> WeightedFitResult:
    """Fit the weighted fixed-effects model with known measurement variances.

    An OLS fit provides the residual variance ``s2``; the site-year variance
    ``sigma_u2`` is ``max(0, s2 - mean(se^2))`` over the rows not excluded by
    ``exclude_from_sigma``. Each row is then weighted by
    ``1 / (sigma_u2 + se^2)`` and the weighted fit treats the weights as known
    inverse variances, so the covariance is ``(X'WX)^-1`` with no extra scale
    factor. Intervals and p-values use a t distribution with ``n - k`` degrees
    of freedom. A term in ``term_indices`` gets a full :class:`FitTerm`; when
    ``columns`` is given the raw coefficients and covariance are stored for
    derived effects and joint tests.
    """
    n, k = X.shape
    dof = n - k
    if dof <= 0:
        raise ValueError(f"Model has no residual degrees of freedom: n={n}, k={k}")
    b_ols = np.linalg.lstsq(X, y, rcond=None)[0]
    s2 = float(((y - X @ b_ols) ** 2).sum() / dof)
    sigma_u2 = s2 - float((se[~exclude_from_sigma] ** 2).mean())
    clipped = sigma_u2 < 0
    if clipped:
        LOGGER.warning(
            "sigma_u^2 clipped to zero (s2=%.3g): measurement SEs exceed total scatter",
            s2,
        )
        sigma_u2 = 0.0
    weights = 1.0 / (sigma_u2 + se**2)
    XtW = X.T * weights
    cov = np.linalg.inv(XtW @ X)
    b = cov @ (XtW @ y)
    t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, dof))
    terms: dict[str, FitTerm] = {}
    for name, idx in term_indices.items():
        estimate = float(b[idx])
        se_b = float(np.sqrt(cov[idx, idx]))
        p_value = float(2.0 * stats.t.sf(abs(estimate / se_b), dof))
        terms[name] = FitTerm(
            term=name,
            estimate=estimate,
            se=se_b,
            ci_low=estimate - t_crit * se_b,
            ci_high=estimate + t_crit * se_b,
            p_value=p_value,
        )
    return WeightedFitResult(
        terms=terms,
        sigma_u=float(np.sqrt(sigma_u2)),
        sigma_u_clipped=clipped,
        df=dof,
        n_obs=n,
        coefficients=(
            {name: float(value) for name, value in zip(columns, b)}
            if columns is not None else {}
        ),
        columns=tuple(columns) if columns is not None else (),
        cov=cov if columns is not None else None,
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
    indicator cell is excluded from the sigma_u^2 estimate because a one-row
    indicator fits its own row exactly, so the row contributes nothing to the
    residual scatter. Indicators whose cell is absent from ``frame`` are
    dropped from the design and recorded on the result. Full estimates are
    returned for every design column.
    """
    X, columns, dropped = build_design(frame, indicators, site_effects=site_effects)
    exclude = np.zeros(len(frame), dtype=bool)
    for cell in indicators.values():
        exclude |= _cell_mask(frame, cell)
    term_indices = {name: idx for idx, name in enumerate(columns)}
    result = fit_weighted(
        X,
        frame["mean_change"].to_numpy(dtype=float),
        frame["se"].to_numpy(dtype=float),
        exclude,
        term_indices,
        alpha,
        columns=columns,
    )
    return WeightedFitResult(
        terms=result.terms,
        sigma_u=result.sigma_u,
        sigma_u_clipped=result.sigma_u_clipped,
        df=result.df,
        n_obs=result.n_obs,
        dropped_terms=dropped,
        coefficients=result.coefficients,
        columns=result.columns,
        cov=result.cov,
        site_effects=site_effects,
    )


def omitted_level_term(
    fit: WeightedFitResult, block_columns: Sequence[str], name: str, alpha: float
) -> FitTerm:
    """Return the omitted level's deviation-coded effect for one block.

    Under sum-to-zero coding the omitted level's effect is minus the sum of
    the block's coefficients; its variance is the sum of the block's
    covariance entries. Intervals use the fit's t distribution.
    """
    indices = _block_indices(fit, block_columns)
    b = np.array([fit.coefficients[column] for column in block_columns])
    estimate = -float(b.sum())
    se = float(np.sqrt(fit.cov[np.ix_(indices, indices)].sum()))
    t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, fit.df))
    p_value = float(2.0 * stats.t.sf(abs(estimate / se), fit.df))
    return FitTerm(
        term=name,
        estimate=estimate,
        se=se,
        ci_low=estimate - t_crit * se,
        ci_high=estimate + t_crit * se,
        p_value=p_value,
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
    b = np.array([fit.coefficients[column] for column in block_columns])
    S = fit.cov[np.ix_(indices, indices)]
    q = len(indices)
    statistic = float(b @ np.linalg.solve(S, b)) / q
    return JointTest(
        name=name,
        statistic=statistic,
        df_num=q,
        df_den=fit.df,
        p_value=float(stats.f.sf(statistic, q, fit.df)),
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
    return np.array([fit.columns.index(column) for column in block_columns])


def _cell_mask(frame: pd.DataFrame, cell: Cell) -> np.ndarray:
    """Return the boolean row mask for one site x year-pair cell."""
    site, (year_start, year_end) = cell
    return (
        frame["study_area"].eq(site)
        & frame["year_start"].eq(year_start)
        & frame["year_end"].eq(year_end)
    ).to_numpy()

"""Design construction and the weighted fixed-effects fit on site-level changes."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from .models import FitTerm, WeightedFitResult

LOGGER = logging.getLogger(__name__)

Cell = tuple[str, tuple[int, int]]


def build_design(
    frame: pd.DataFrame, indicators: Mapping[str, Cell]
) -> tuple[np.ndarray, list[str], tuple[str, ...]]:
    """Build the two-way fixed-effects design matrix with event indicators.

    Columns are an intercept, site dummies (first sorted site is the
    reference), year-pair dummies (first sorted pair is the reference), and one
    indicator per entry of ``indicators`` mapping a term name to its
    (site, (year_start, year_end)) cell. Indicators whose cell is absent from
    ``frame`` are dropped and reported in the returned tuple.
    """
    sites = sorted(frame["study_area"].unique())
    pairs = sorted(set(zip(frame["year_start"], frame["year_end"])))
    columns = ["intercept"]
    data = [np.ones(len(frame))]
    for site in sites[1:]:
        columns.append(f"site_{site}")
        data.append(frame["study_area"].eq(site).to_numpy(dtype=float))
    for year_start, year_end in pairs[1:]:
        columns.append(f"pair_{year_start}_{year_end}")
        data.append(frame["year_start"].eq(year_start).to_numpy(dtype=float))
    dropped: list[str] = []
    for name, cell in indicators.items():
        column = _cell_mask(frame, cell).astype(float)
        if column.any():
            columns.append(name)
            data.append(column)
        else:
            dropped.append(name)
    return np.column_stack(data), columns, tuple(dropped)


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
    of freedom.
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
    )


def fit_did(
    frame: pd.DataFrame,
    indicators: Mapping[str, Cell],
    sigma_exclude_cells: Iterable[Cell],
    alpha: float,
) -> WeightedFitResult:
    """Fit the model on one prepared (SE-handled) subset of site-level changes.

    ``indicators`` maps term names to event cells; ``sigma_exclude_cells``
    lists the cells left out of the sigma_u^2 estimate. Indicators whose cell
    is absent from ``frame`` are dropped from the design and recorded on the
    result.
    """
    X, columns, dropped = build_design(frame, indicators)
    exclude = np.zeros(len(frame), dtype=bool)
    for cell in sigma_exclude_cells:
        exclude |= _cell_mask(frame, cell)
    term_indices = {
        name: columns.index(name) for name in indicators if name not in dropped
    }
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
    )


def compute_anomalies(frame: pd.DataFrame, fit: WeightedFitResult) -> pd.DataFrame:
    """Return each cell's deviation from the fitted fixed-effects counterfactual.

    The counterfactual is the fitted intercept plus site and year-pair fixed
    effects, with every event-indicator contribution zeroed. At non-event cells
    the anomaly is the fit's residual; at an event cell it is the indicator
    estimate plus that cell's residual.
    """
    if not fit.coefficients:
        raise ValueError("Fit has no stored coefficients; refit via fit_did")
    X, columns, _ = build_design(frame, {})
    b = np.array([fit.coefficients[column] for column in columns])
    result = frame[["study_area", "year_start", "year_end", "mean_change"]].copy()
    result["counterfactual"] = X @ b
    result["anomaly"] = result["mean_change"] - result["counterfactual"]
    return result


def _cell_mask(frame: pd.DataFrame, cell: Cell) -> np.ndarray:
    """Return the boolean row mask for one site x year-pair cell."""
    site, (year_start, year_end) = cell
    return (
        frame["study_area"].eq(site)
        & frame["year_start"].eq(year_start)
        & frame["year_end"].eq(year_end)
    ).to_numpy()

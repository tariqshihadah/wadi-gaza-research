"""Placebo refits of the weighted fixed-effects model where nothing happened."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DidAnalysisConfig
from .fitting import Cell, fit_did

EVENT_TERM = "d_event"
PERSIST_TERM = "d_persist"


def run_placebo_space(
    frame: pd.DataFrame, real_estimate: float, config: DidAnalysisConfig
) -> pd.DataFrame:
    """Refit with each comparison site as the fake affected site.

    ``frame`` is one month x tau subset with SEs already handled. Each refit
    drops the affected site's rows, moves both event indicators onto one
    comparison site, and re-estimates sigma_u^2 and the weights excluding that
    site's first event cell. Returns one row per site (the real estimate plus
    one placebo per comparison site) with the month's one-sided p-value and the
    ratio of the real estimate to the largest absolute placebo estimate.
    """
    event_pair, persist_pair = config.event_pairs
    comparison = frame.loc[frame["study_area"] != config.affected_site]
    rows = [{"site": config.affected_site, "is_real": True, "estimate": real_estimate}]
    for site in sorted(comparison["study_area"].unique()):
        fit = fit_did(
            comparison.reset_index(drop=True),
            {EVENT_TERM: (site, event_pair), PERSIST_TERM: (site, persist_pair)},
            [(site, event_pair)],
            config.alpha,
        )
        rows.append({
            "site": site, "is_real": False,
            "estimate": fit.terms[EVENT_TERM].estimate,
        })
    result = pd.DataFrame(rows)
    estimates = result["estimate"].to_numpy()
    placebos = result.loc[~result["is_real"], "estimate"].to_numpy()
    result["p_value"] = float((estimates <= real_estimate).sum()) / len(estimates)
    largest_placebo = float(np.abs(placebos).max())
    result["ratio_to_largest_placebo"] = (
        abs(real_estimate) / largest_placebo if largest_placebo else np.inf
    )
    return result


def run_placebo_spacetime(
    frame: pd.DataFrame, config: DidAnalysisConfig
) -> pd.DataFrame:
    """Refit with every unaffected site x year-pair cell as a fake event.

    ``frame`` is one month x tau subset with SEs already handled. The second
    event pair is dropped entirely; the real estimate puts a single indicator
    on the affected site's first event cell. Each placebo then drops that real
    cell and puts the indicator on one of the remaining cells. Returns one row
    per cell with the month's one-sided p-value.
    """
    event_pair, persist_pair = config.event_pairs
    pre = frame.loc[frame["year_start"] != persist_pair[0]].reset_index(drop=True)
    real_cell: Cell = (config.affected_site, event_pair)
    real_fit = fit_did(pre, {EVENT_TERM: real_cell}, [real_cell], config.alpha)
    real_estimate = real_fit.terms[EVENT_TERM].estimate
    rows = [{
        "site": config.affected_site,
        "year_start": event_pair[0], "year_end": event_pair[1],
        "is_real": True, "estimate": real_estimate,
    }]
    placebo_mask = ~(
        pre["study_area"].eq(config.affected_site)
        & pre["year_start"].eq(event_pair[0])
    )
    placebo_frame = pre.loc[placebo_mask].reset_index(drop=True)
    cells = placebo_frame[["study_area", "year_start", "year_end"]].drop_duplicates()
    for site, year_start, year_end in cells.itertuples(index=False):
        cell: Cell = (site, (int(year_start), int(year_end)))
        fit = fit_did(placebo_frame, {EVENT_TERM: cell}, [cell], config.alpha)
        rows.append({
            "site": site, "year_start": int(year_start), "year_end": int(year_end),
            "is_real": False, "estimate": fit.terms[EVENT_TERM].estimate,
        })
    result = pd.DataFrame(rows)
    placebos = result.loc[~result["is_real"], "estimate"].to_numpy()
    result["p_value"] = (1.0 + float((placebos <= real_estimate).sum())) / len(result)
    return result

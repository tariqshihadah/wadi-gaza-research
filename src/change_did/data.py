"""Load and validate upstream change-CI results for the fixed-effects model."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import DidAnalysisConfig

LOGGER = logging.getLogger(__name__)

REQUIRED_COLUMNS = (
    "study_area",
    "index",
    "month",
    "year_start",
    "year_end",
    "tau",
    "mean_change",
    "se",
    "sd",
    "flag_no_range",
)

FILL_METHODS = ("max_se", "drop_flagged", "n_eff_fill")


def load_change_results(config: DidAnalysisConfig) -> pd.DataFrame:
    """Read, concatenate, and validate the configured change-CI result tables.

    Returns the combined frame restricted to the configured indices and months,
    with ``month`` normalized to an integer. Raises ``ValueError`` when any of
    the brief's load checks fail.
    """
    frames = []
    for path in config.input_paths:
        if not path.exists():
            raise ValueError(f"Input results file not found: {path}")
        frames.append(pd.read_csv(path))
    combined = pd.concat(frames, ignore_index=True)
    missing_columns = set(REQUIRED_COLUMNS) - set(combined.columns)
    if missing_columns:
        raise ValueError(f"Input results missing columns: {sorted(missing_columns)}")
    combined["month"] = combined["month"].astype(int)
    combined = combined.loc[
        combined["index"].isin(config.indices) & combined["month"].isin(config.months)
    ].reset_index(drop=True)
    validate_change_results(combined, config)
    return combined


def validate_change_results(frame: pd.DataFrame, config: DidAnalysisConfig) -> None:
    """Run the brief's load checks, raising ``ValueError`` on the first failure."""
    missing_indices = set(config.indices) - set(frame["index"])
    if missing_indices:
        raise ValueError(f"No rows found for configured indices: {sorted(missing_indices)}")

    sites = sorted(frame["study_area"].unique())
    if config.affected_site not in sites:
        raise ValueError(f"Affected site not present in results: {config.affected_site}")
    pairs = sorted(set(zip(frame["year_start"], frame["year_end"])))
    expected_rows = len(sites) * len(pairs)

    for (index, month, tau), subset in frame.groupby(["index", "month", "tau"]):
        label = f"index={index}, month={month}, tau={tau}"
        if len(subset) != expected_rows:
            raise ValueError(
                f"Expected {expected_rows} rows ({len(sites)} sites x {len(pairs)} pairs) "
                f"for {label}; found {len(subset)}"
            )
        duplicates = subset.duplicated(["study_area", "year_start", "year_end"])
        if duplicates.any():
            raise ValueError(f"Duplicate site x pair rows for {label}")

    if not frame["year_end"].eq(frame["year_start"] + 1).all():
        raise ValueError("year_end must equal year_start + 1 for every row")

    se_missing = frame["se"].isna()
    flagged = frame["flag_no_range"].astype(bool)
    if not se_missing.equals(flagged):
        mismatched = frame.loc[se_missing != flagged]
        raise ValueError(
            "se must be missing exactly where flag_no_range is true; "
            f"{len(mismatched)} row(s) violate this"
        )
    if frame["mean_change"].isna().any():
        raise ValueError("mean_change must never be missing")


def flagged_se_report(frame: pd.DataFrame, config: DidAnalysisConfig) -> pd.DataFrame:
    """Count flagged (missing-SE) rows at the primary tau per index and month.

    Returns one row per index with per-month and total counts, and logs a
    warning when the primary index's total differs from the expected count.
    """
    primary = frame.loc[np.isclose(frame["tau"], config.tau)]
    counts = (
        primary.groupby(["index", "month"])["flag_no_range"].sum().unstack(fill_value=0)
    )
    report = counts.reindex(index=list(config.indices), columns=list(config.months))
    report.columns = [f"month_{month:02d}" for month in report.columns]
    report["total"] = report.sum(axis=1)
    report = report.astype(int).reset_index()
    expected = config.expected_flagged_primary
    if expected is not None:
        total = int(
            report.loc[report["index"] == config.primary_index, "total"].iloc[0]
        )
        if total != expected:
            LOGGER.warning(
                "Flagged-SE count for %s at tau=%s is %d, expected %d",
                config.primary_index, config.tau, total, expected,
            )
    return report


def fill_missing_se(
    frame: pd.DataFrame, method: str, fill_n_eff: float
) -> tuple[pd.DataFrame, int]:
    """Handle missing SEs in one month x tau subset and count affected rows.

    ``max_se`` fills with the subset's largest non-missing SE, ``n_eff_fill``
    fills with the row's ``sd / sqrt(fill_n_eff)``, and ``drop_flagged`` drops
    the flagged rows. Returns the handled copy and the number of filled or
    dropped rows.
    """
    if method not in FILL_METHODS:
        raise ValueError(f"Unknown fill method: {method}")
    handled = frame.copy()
    missing = handled["se"].isna()
    count = int(missing.sum())
    if method == "drop_flagged":
        return handled.loc[~missing].reset_index(drop=True), count
    if method == "max_se":
        if count and handled["se"].notna().sum() == 0:
            raise ValueError("Cannot fill missing SEs: no non-missing se in subset")
        handled.loc[missing, "se"] = handled["se"].max()
    else:
        handled.loc[missing, "se"] = handled.loc[missing, "sd"] / np.sqrt(fill_n_eff)
    return handled, count

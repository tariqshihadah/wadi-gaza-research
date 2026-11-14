"""Plot saved fixed-effects results without recomputing statistical estimates."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from plot_style import FIGURE_DPI, add_gridlines, add_shared_legend, annotate_cells, finish_panel_grid, month_name

from .placebo import EVENT_TERM

REAL_COLOR = "#b2182b"
PLACEBO_COLOR = "#4393c3"
VARIANT_LABELS = {
    "primary": "Primary",
    "exclude_flagged": "Exclude flagged",
    "n_eff_fill": "n_eff = 5 fill",
}


def plot_placebo_space(
    placebo: pd.DataFrame,
    months: Sequence[int] | None = None,
    ncols: int = 2,
) -> tuple[Figure, np.ndarray]:
    """Plot each month's placebo-in-space estimates by site with the real site highlighted.

    ``placebo`` holds one index's ``did_placebo_space.csv`` rows. Panels show
    one month each; the real estimate is a square with a matching vertical
    line, and the panel title carries the month's one-sided p-value and the
    ratio of the real estimate to the largest absolute placebo.
    """
    fig, axes, month_values = _month_panels(placebo, months, ncols, (11, 7))
    for ax, month in zip(axes.flat, month_values):
        rows = placebo.loc[placebo["month"] == month]
        rows = pd.concat([
            rows.loc[rows["is_real"]],
            rows.loc[~rows["is_real"]].sort_values("estimate"),
        ])
        positions = np.arange(len(rows))[::-1]
        real = rows.loc[rows["is_real"]]
        real_estimate = float(real["estimate"].iloc[0])
        ax.axvline(real_estimate, color=REAL_COLOR, linewidth=1.4, alpha=0.8, zorder=2)
        ax.scatter(
            real["estimate"], positions[rows["is_real"].to_numpy()],
            color=REAL_COLOR, marker="D", s=55, zorder=4,
            label="Real (affected site)",
        )
        mask = ~rows["is_real"]
        ax.scatter(
            rows.loc[mask, "estimate"], positions[mask.to_numpy()],
            color=PLACEBO_COLOR, label="Placebo", zorder=3,
        )
        ax.axvline(0.0, color="0.4", linewidth=0.9)
        ax.set_yticks(positions)
        ax.set_yticklabels(rows["site"])
        ax.set_xlabel("Event estimate")
        ax.set_title(_panel_title(rows, month))
        add_gridlines(ax, axis="x")
    add_shared_legend(fig, axes)
    return fig, axes


def plot_placebo_spacetime(
    placebo: pd.DataFrame,
    months: Sequence[int] | None = None,
    ncols: int = 2,
) -> tuple[Figure, np.ndarray]:
    """Plot each month's placebo-in-space-and-time distribution against the real estimate.

    ``placebo`` holds one index's ``did_placebo_spacetime.csv`` rows. Panels
    rank every estimate; the real estimate is a square at its own rank with a
    matching vertical line, and the panel title carries the month's one-sided
    p-value.
    """
    fig, axes, month_values = _month_panels(placebo, months, ncols, (11, 6))
    for ax, month in zip(axes.flat, month_values):
        rows = placebo.loc[placebo["month"] == month].sort_values("estimate")
        ranks = np.arange(1, len(rows) + 1)
        real_mask = rows["is_real"].to_numpy()
        real = float(rows.loc[rows["is_real"], "estimate"].iloc[0])
        ax.axvline(real, color=REAL_COLOR, linewidth=1.4, alpha=0.8, zorder=2)
        ax.scatter(
            rows.loc[~rows["is_real"], "estimate"], ranks[~real_mask],
            color=PLACEBO_COLOR, label="Placebo", zorder=3,
        )
        ax.scatter(
            [real], ranks[real_mask],
            color=REAL_COLOR, marker="D", s=55, zorder=4,
            label="Real (affected site)",
        )
        ax.axvline(0.0, color="0.4", linewidth=0.9)
        values = np.append(rows["estimate"].to_numpy(), 0.0)
        pad = 0.06 * (values.max() - values.min())
        ax.set_xlim(values.min() - pad, values.max() + pad)
        ax.set_xlabel("Event estimate")
        ax.set_ylabel("Rank")
        ax.set_title(_panel_title(rows, month))
        add_gridlines(ax, axis="x")
    add_shared_legend(fig, axes)
    return fig, axes


def plot_sensitivity_forest(
    main: pd.DataFrame,
    term: str = "d_event",
    months: Sequence[int] | None = None,
    ncols: int = 2,
) -> tuple[Figure, np.ndarray]:
    """Plot each month's event estimate with its CI across the model variants.

    ``main`` holds one index's ``did_main.csv`` rows; ``term`` selects which
    indicator to show. The primary specification is highlighted.
    """
    rows = main.loc[main["term"] == term]
    if rows.empty:
        raise ValueError(f"No rows found for term: {term}")
    fig, axes, month_values = _month_panels(rows, months, ncols, (11, 6))
    variants = list(dict.fromkeys(rows["variant"]))
    labels = [_variant_label(variant) for variant in variants]
    for ax, month in zip(axes.flat, month_values):
        month_rows = rows.loc[rows["month"] == month].set_index("variant")
        positions = np.arange(len(variants))[::-1]
        for position, variant in zip(positions, variants):
            row = month_rows.loc[variant]
            color = REAL_COLOR if variant == "primary" else PLACEBO_COLOR
            label = "Primary" if variant == "primary" else "Sensitivity"
            ax.errorbar(
                row["estimate"], position,
                xerr=[[row["estimate"] - row["ci_low"]], [row["ci_high"] - row["estimate"]]],
                fmt="o", color=color, capsize=3, label=label, zorder=3,
            )
        ax.axvline(0.0, color="0.4", linewidth=0.9)
        ax.set_yticks(positions)
        ax.set_yticklabels(labels)
        ax.set_xlabel("Event estimate (95% CI)")
        ax.set_title(month_name(month))
        add_gridlines(ax, axis="x")
    add_shared_legend(fig, axes)
    return fig, axes


def save_figure(fig: Figure, path: str | Path, dpi: int = FIGURE_DPI) -> Path:
    """Save a figure after creating its parent directory and return the path."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=dpi, bbox_inches="tight")
    return destination


def plot_change_trajectories(
    results: pd.DataFrame,
    affected_site: str,
    event_pairs: Sequence[tuple[int, int]],
    months: Sequence[int] | None = None,
    ncols: int = 2,
) -> tuple[Figure, np.ndarray]:
    """Plot every site's mean change over year pairs with the affected site highlighted.

    ``results`` holds one index's change-CI rows; primary-tau rows are selected
    when ``is_primary_tau`` is present. Comparison sites are drawn in muted
    grey, the affected site in the highlight colour with its spatially adjusted
    95% CI as error bars (``ci_low``/``ci_high``) when present, and the event
    year pairs are shaded.
    """
    frame = results.copy()
    if "is_primary_tau" in frame:
        frame = frame.loc[frame["is_primary_tau"].astype(bool)]
    frame["month"] = frame["month"].astype(int)
    fig, axes, month_values = _month_panels(frame, months, ncols, (11, 7))
    pairs = sorted(set(zip(frame["year_start"].astype(int), frame["year_end"].astype(int))))
    event_starts = [pair[0] for pair in event_pairs]
    for ax, month in zip(axes.flat, month_values):
        rows = frame.loc[frame["month"] == month]
        ax.axvspan(
            min(event_starts) - 0.35, max(event_starts) + 0.35,
            color=REAL_COLOR, alpha=0.08, zorder=0,
        )
        for site in sorted(rows["study_area"].unique()):
            series = rows.loc[rows["study_area"] == site].sort_values("year_start")
            is_affected = site == affected_site
            ax.plot(
                series["year_start"], series["mean_change"], marker="o",
                markersize=4 if is_affected else 3,
                color=REAL_COLOR if is_affected else "0.65",
                linewidth=2.0 if is_affected else 1.0,
                zorder=3 if is_affected else 2,
                label=affected_site if is_affected else "Comparison sites",
            )
            if is_affected and {"ci_low", "ci_high"} <= set(series.columns):
                low = series["ci_low"].to_numpy(dtype=float)
                high = series["ci_high"].to_numpy(dtype=float)
                mean = series["mean_change"].to_numpy(dtype=float)
                valid = np.isfinite(low) & np.isfinite(high) & np.isfinite(mean)
                if valid.any():
                    ax.errorbar(
                        series["year_start"].to_numpy(dtype=float)[valid], mean[valid],
                        yerr=[mean[valid] - low[valid], high[valid] - mean[valid]],
                        fmt="none", ecolor=REAL_COLOR, elinewidth=1.2, capsize=3,
                        zorder=4, label=f"{affected_site} 95% CI",
                    )
        ax.axhline(0.0, color="0.4", linewidth=0.9)
        ax.set_xticks(
            [pair[0] for pair in pairs], [_pair_label(*pair) for pair in pairs]
        )
        ax.set_ylabel("Mean change")
        ax.set_title(month_name(month))
        add_gridlines(ax)
    add_shared_legend(fig, axes)
    return fig, axes


def plot_anomaly_heatmap(
    anomalies: pd.DataFrame,
    months: Sequence[int] | None = None,
    sites: Sequence[str] | None = None,
) -> tuple[Figure, np.ndarray]:
    """Plot each cell's deviation from the fixed-effects counterfactual per month.

    ``anomalies`` holds one model's ``did_anomalies.csv`` rows for one index:
    each cell's deviation from that model's fitted fixed effects. Event cells are
    outlined; their deviations equal the fitted event coefficients. Brown is a
    decrease and teal an increase, matching the change-CI heatmaps. ``sites``
    sets the row order from top to bottom; it defaults to alphabetical.
    """
    frame = anomalies.copy()
    month_values = sorted(months or frame["month"].unique())
    sites = list(sites) if sites is not None else sorted(frame["site"].unique())
    pairs = sorted(set(zip(frame["year_start"], frame["year_end"])))
    limit = float(frame["anomaly"].abs().max())
    ncols = 2
    nrows = math.ceil(len(month_values) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 11), squeeze=False)
    axes = np.asarray(axes)
    for ax in axes.flat[len(month_values):]:
        ax.set_visible(False)
    for ax, month in zip(axes.flat, month_values):
        rows = frame.loc[frame["month"] == month]
        grid = (
            rows.pivot(index="site", columns="year_start", values="anomaly")
            .reindex(index=sites, columns=[pair[0] for pair in pairs])
            .to_numpy(dtype=float)
        )
        image = ax.imshow(grid, cmap="BrBG", vmin=-limit, vmax=limit, aspect="auto")
        labels = np.vectorize(lambda v: f"{v:.2f}" if np.isfinite(v) else "")(grid)
        annotate_cells(ax, image, grid, labels)
        for _, cell in rows.loc[rows["is_event_cell"]].iterrows():
            row = sites.index(cell["site"])
            column = [pair[0] for pair in pairs].index(cell["year_start"])
            ax.add_patch(Rectangle(
                (column - 0.5, row - 0.5), 1, 1,
                fill=False, edgecolor=REAL_COLOR, linewidth=2.0,
            ))
        ax.set_xticks(
            range(len(pairs)), [_pair_label(*pair) for pair in pairs], rotation=45
        )
        ax.set_yticks(range(len(sites)), sites)
        ax.set_title(month_name(month))
    finish_panel_grid(fig, axes, label="Deviation from fixed-effects counterfactual")
    return fig, axes


def plot_observed_vs_counterfactual(
    anomalies: pd.DataFrame,
    affected_site: str,
    event_pairs: Sequence[tuple[int, int]],
    months: Sequence[int] | None = None,
    ncols: int = 2,
) -> tuple[Figure, np.ndarray]:
    """Plot the affected site's observed changes against the model counterfactual.

    ``anomalies`` holds one model's ``did_anomalies.csv`` rows for one index.
    The counterfactual is the fitted intercept plus that model's fixed effects
    (site and year-pair, or year-pair only for the period-only model): what the
    model expects of the affected site absent an event. The
    gap at the first event pair is annotated; it equals the event estimate.
    """
    frame = anomalies.loc[anomalies["site"] == affected_site].copy()
    if frame.empty:
        raise ValueError(f"No anomaly rows for site: {affected_site}")
    fig, axes, month_values = _month_panels(frame, months, ncols, (11, 7))
    event_starts = [pair[0] for pair in event_pairs]
    pairs = sorted(set(zip(frame["year_start"], frame["year_end"])))
    for ax, month in zip(axes.flat, month_values):
        rows = frame.loc[frame["month"] == month].sort_values("year_start")
        ax.axvspan(
            min(event_starts) - 0.35, max(event_starts) + 0.35,
            color=REAL_COLOR, alpha=0.08, zorder=0,
        )
        ax.plot(
            rows["year_start"], rows["counterfactual"], marker="o", markersize=4,
            linestyle="--", color="0.45", label="Fixed-effects counterfactual",
        )
        ax.plot(
            rows["year_start"], rows["mean_change"], marker="o", markersize=4,
            color=REAL_COLOR, linewidth=2.0, label="Observed", zorder=3,
        )
        event = rows.loc[rows["year_start"] == event_starts[0]].iloc[0]
        ax.annotate(
            "", xy=(event["year_start"], event["mean_change"]),
            xytext=(event["year_start"], event["counterfactual"]),
            arrowprops={"arrowstyle": "<->", "color": "0.2", "linewidth": 1.2},
        )
        ax.annotate(
            f"gap = {event['anomaly']:+.3f}",
            xy=(event["year_start"] + 0.08,
                (event["mean_change"] + event["counterfactual"]) / 2),
            fontsize=9, va="center", zorder=5,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1.5},
        )
        ax.axhline(0.0, color="0.4", linewidth=0.9)
        ax.set_xticks(
            [pair[0] for pair in pairs], [_pair_label(*pair) for pair in pairs]
        )
        ax.set_ylabel("Mean change")
        ax.set_title(month_name(month))
        add_gridlines(ax)
    add_shared_legend(fig, axes)
    return fig, axes


def plot_combined_evidence(
    main: pd.DataFrame,
    placebo_space: pd.DataFrame,
    placebo_spacetime: pd.DataFrame,
    months: Sequence[int] | None = None,
    ncols: int = 2,
) -> tuple[Figure, np.ndarray]:
    """Plot the event estimate, its CI, and the placebo distributions per month.

    Inputs are one index's ``did_main.csv``, ``did_placebo_space.csv``, and
    ``did_placebo_spacetime.csv`` rows. Each panel stacks the primary event
    estimate with its 95% CI over two placebo rows on a shared estimate axis:
    the comparison sites (space placebos) and every unaffected site x pair
    cell (space-and-time placebos). Panel titles carry both one-sided placebo
    p-values.
    """
    event = main.loc[(main["variant"] == "primary") & (main["term"] == EVENT_TERM)]
    if event.empty:
        raise ValueError("No primary event rows found in main results")
    fig, axes, month_values = _month_panels(event, months, ncols, (11, 7))
    for ax, month in zip(axes.flat, month_values):
        _combined_evidence_panel(
            ax,
            event.loc[event["month"] == month].iloc[0],
            placebo_space.loc[placebo_space["month"] == month],
            placebo_spacetime.loc[placebo_spacetime["month"] == month],
            month_name(month),
        )
    add_shared_legend(fig, axes)
    return fig, axes


def plot_combined_evidence_by_index(
    results_by_index: Mapping[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]],
    month: int,
    ncols: int = 2,
) -> tuple[Figure, np.ndarray]:
    """Plot one month's combined evidence with one panel per index.

    Transpose of :func:`plot_combined_evidence`: ``results_by_index`` maps each
    index name to its (``did_main.csv``, ``did_placebo_space.csv``,
    ``did_placebo_spacetime.csv``) frames, and every panel shows the requested
    month so the indices can be compared directly.
    """
    if not results_by_index:
        raise ValueError("results_by_index must not be empty")
    indices = list(results_by_index)
    nrows = math.ceil(len(indices) / ncols)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(11, 7), constrained_layout=True, squeeze=False
    )
    axes = np.asarray(axes)
    for ax in axes.flat[len(indices):]:
        ax.set_visible(False)
    for ax, index in zip(axes.flat, indices):
        main, placebo_space, placebo_spacetime = results_by_index[index]
        event = main.loc[
            (main["variant"] == "primary")
            & (main["term"] == EVENT_TERM)
            & (main["month"] == month)
        ]
        if event.empty:
            raise ValueError(f"No primary event rows for month {month} in {index}")
        _combined_evidence_panel(
            ax,
            event.iloc[0],
            placebo_space.loc[placebo_space["month"] == month],
            placebo_spacetime.loc[placebo_spacetime["month"] == month],
            index,
        )
    add_shared_legend(fig, axes)
    return fig, axes


def _combined_evidence_panel(
    ax: Axes,
    row: pd.Series,
    placebo_space: pd.DataFrame,
    placebo_spacetime: pd.DataFrame,
    title: str,
) -> None:
    """Draw one combined-evidence panel from a single month's result rows."""
    space = placebo_space.loc[~placebo_space["is_real"]]
    spacetime = placebo_spacetime.loc[~placebo_spacetime["is_real"]]
    ax.errorbar(
        row["estimate"], 2.0,
        xerr=[[row["estimate"] - row["ci_low"]], [row["ci_high"] - row["estimate"]]],
        fmt="o", color=REAL_COLOR, capsize=3, zorder=3,
        label=r"Event estimate ($\beta$, 95% CI)",
    )
    ax.scatter(
        space["estimate"], np.full(len(space), 1.0),
        facecolors="none", edgecolors=PLACEBO_COLOR, zorder=3,
        label="Space placebos",
    )
    ax.scatter(
        spacetime["estimate"], np.full(len(spacetime), 0.0),
        color=PLACEBO_COLOR, alpha=0.45, zorder=3, label="Space-and-time placebos",
    )
    ax.axvline(0.0, color="0.4", linewidth=0.9)
    ax.set_yticks(
        [2.0, 1.0, 0.0],
        [
            r"Event estimate ($\beta$)",
            f"Space placebos ({len(space)})",
            f"Space-and-time placebos ({len(spacetime)})",
        ],
    )
    ax.set_ylim(-0.6, 2.6)
    ax.set_xlabel("Event estimate")
    space_p = float(placebo_space["p_value"].iloc[0])
    spacetime_p = float(placebo_spacetime["p_value"].iloc[0])
    ax.set_title(
        f"{title}: p = {space_p:.3f} (space), "
        f"{spacetime_p:.3f} (space-and-time)"
    )
    add_gridlines(ax, axis="x")


def _pair_label(start: int, end: int) -> str:
    """Format years as a compact pair label."""
    return f"{int(start)}\N{RIGHTWARDS ARROW}{int(end) % 100:02d}"


def _month_panels(
    frame: pd.DataFrame,
    months: Sequence[int] | None,
    ncols: int,
    figsize: tuple[float, float],
) -> tuple[Figure, np.ndarray, list[int]]:
    """Create one panel per month and hide any unused axes."""
    month_values = sorted(months or frame["month"].unique())
    if not month_values:
        raise ValueError("No months to plot")
    nrows = math.ceil(len(month_values) / ncols)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=figsize, constrained_layout=True, squeeze=False
    )
    axes = np.asarray(axes)
    for ax in axes.flat[len(month_values):]:
        ax.set_visible(False)
    return fig, axes, month_values


def _panel_title(rows: pd.DataFrame, month: int) -> str:
    """Return a placebo panel title with the month's p-value and optional ratio."""
    title = f"{month_name(month)}: p = {float(rows['p_value'].iloc[0]):.3f}"
    if "ratio_to_largest_placebo" in rows:
        title += f", ratio = {float(rows['ratio_to_largest_placebo'].iloc[0]):.1f}"
    return title


def _variant_label(variant: str) -> str:
    """Return a readable label for a variant name such as ``tau_0.02``."""
    if variant.startswith("tau_"):
        return f"\u03c4 = {variant[4:]}"
    return VARIANT_LABELS.get(variant, variant)

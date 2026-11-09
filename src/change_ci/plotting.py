"""Plot saved change-CI results without recomputing statistical estimates."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure

from plot_style import add_gridlines, add_shared_legend, annotate_cells, month_name


def _month(value: object) -> str:
    """Normalize an integer or string month to two digits."""
    return str(value).zfill(2)


def _select(
    results: pd.DataFrame,
    tau: float | None = None,
    filters: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Select primary-threshold results and requested filters."""
    frame = results.copy()
    if tau is not None:
        if "tau" not in frame:
            raise ValueError("results must contain a 'tau' column")
        frame = frame.loc[np.isclose(frame["tau"].astype(float), tau)]
    elif "is_primary_tau" in frame:
        frame = frame.loc[frame["is_primary_tau"].fillna(False).astype(bool)]
    elif "tau" in frame and frame["tau"].nunique(dropna=True) > 1:
        raise ValueError("Multiple tau values require is_primary_tau or an explicit tau")
    for column, value in (filters or {}).items():
        if column not in frame:
            raise ValueError(f"Unknown results filter column: {column}")
        if column == "month":
            series = frame[column].map(_month)
            frame = frame.loc[series.isin(map(_month, value))] if isinstance(value, (list, tuple, set)) else frame.loc[series == _month(value)]
        elif isinstance(value, (list, tuple, set, frozenset)):
            frame = frame.loc[frame[column].isin(value)]
        else:
            frame = frame.loc[frame[column] == value]
    if frame.empty:
        raise ValueError("No result rows match the requested selection")
    return frame


def _pair_label(start: int, end: int) -> str:
    """Format years as a compact pair label."""
    return f"{int(start)}\N{RIGHTWARDS ARROW}{int(end) % 100:02d}"


def _pairs(frame: pd.DataFrame) -> list[tuple[int, int]]:
    """Return sorted year-pair identifiers."""
    return sorted({(int(a), int(b)) for a, b in zip(frame.year_start, frame.year_end)})


def _figure_axes(ax: Axes | None, figsize: tuple[float, float] = (9, 5)) -> tuple[Figure, Axes]:
    """Return an existing axes or create a new figure and axes."""
    return plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)


def _errorbars(ax: Axes, x: np.ndarray, rows: pd.DataFrame, color: Any) -> None:
    """Draw adjusted confidence intervals only where both bounds are finite."""
    mean = rows["mean_change"].to_numpy(dtype=float)
    low = rows["ci_low"].to_numpy(dtype=float)
    high = rows["ci_high"].to_numpy(dtype=float)
    valid = np.isfinite(mean) & np.isfinite(low) & np.isfinite(high)
    if valid.any():
        ax.errorbar(x[valid], mean[valid],
                    yerr=np.vstack((mean[valid] - low[valid], high[valid] - mean[valid])),
                    fmt="none", ecolor=color, elinewidth=1.1, capsize=3)


def plot_change_timeseries(
    results: pd.DataFrame,
    group_by: str = "month",
    filters: Mapping[str, Any] | None = None,
    show_ci_for: str | Sequence[str] | None = "all",
    ax: Axes | None = None,
    tau: float | None = None,
    highlight: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot mean changes and optional adjusted CIs over year pairs.

    Parameters
    ----------
    results : pandas.DataFrame
        Results produced by the analysis module.
    group_by : {"month", "study_area"}
        Column used to define plotted series.
    filters : mapping, optional
        Column/value filters applied before plotting.
    show_ci_for : {"all", None} or sequence of str, optional
        Series labels whose adjusted CIs should be drawn.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw.
    tau : float, optional
        Threshold to plot; defaults to the primary tau.
    highlight : str, optional
        Series label to emphasize with a distinct color and marker.

    Returns
    -------
    tuple
        Figure and axes containing the plot.

    Raises
    ------
    ValueError
        If the grouping column is unsupported or no rows match.
    """
    if group_by not in {"month", "study_area"}:
        raise ValueError("group_by must be 'month' or 'study_area'")
    frame = _select(results, tau, filters)
    frame = frame.assign(_series=frame[group_by].map(_month) if group_by == "month" else frame[group_by].astype(str))
    groups = sorted(frame["_series"].unique())
    if highlight is not None and highlight not in groups:
        raise ValueError(f"Highlighted series not present: {highlight}")
    pairs = _pairs(frame)
    pair_index = {pair: index for index, pair in enumerate(pairs)}
    offsets = np.linspace(-0.18, 0.18, len(groups)) if len(groups) > 1 else np.array([0.0])
    ci_groups = set(groups) if isinstance(show_ci_for, str) and show_ci_for == "all" else set(show_ci_for or ())
    fig, ax = _figure_axes(ax)
    for index, (group, offset) in enumerate(zip(groups, offsets)):
        rows = frame.loc[frame["_series"] == group].sort_values(["year_start", "year_end"])
        x = np.array([pair_index[(int(r.year_start), int(r.year_end))] + offset for r in rows.itertuples()])
        color = "C3" if group == highlight else ("0.62" if highlight is not None else f"C{index % 10}")
        marker = "D" if group == highlight else "o"
        label = month_name(group) if group_by == "month" else group
        ax.plot(x, rows["mean_change"], marker=marker, linestyle="--", linewidth=1,
                markersize=5, color=color, label=label)
        if group in ci_groups:
            _errorbars(ax, x, rows, color)
    ax.axhline(0, color="black", linewidth=0.9)
    ax.set_xticks(range(len(pairs)), [_pair_label(*pair) for pair in pairs])
    ax.set_xlabel("Year pair")
    ax.set_ylabel("Mean index change")
    add_gridlines(ax)
    ax.legend(title=group_by.replace("_", " "))
    fig.tight_layout()
    return fig, ax


def plot_change_small_multiples(
    results: pd.DataFrame,
    facet_by: str,
    filters: Mapping[str, Any] | None = None,
    show_ci_for: str | Sequence[str] | None = "all",
    ax: np.ndarray | Sequence[Axes] | None = None,
    tau: float | None = None,
    ncols: int = 3,
    highlight: str | None = None,
) -> tuple[Figure, np.ndarray]:
    """Plot one shared-y time-series panel per month or study area.

    Parameters
    ----------
    results : pandas.DataFrame
        Results produced by the analysis module.
    facet_by : {"month", "study_area"}
        Column whose unique values define panels.
    filters : mapping, optional
        Additional column/value filters.
    show_ci_for : {"all", None} or sequence of str, optional
        Series labels whose adjusted CIs should be drawn.
    ax : array-like of matplotlib.axes.Axes, optional
        Existing axes, one for each facet.
    tau : float, optional
        Threshold to plot; defaults to the primary tau.
    ncols : int
        Number of columns when creating new axes.
    highlight : str, optional
        Series label to emphasize in each panel.

    Returns
    -------
    tuple
        Figure and a two-dimensional axes array.
    """
    if facet_by not in {"month", "study_area"}:
        raise ValueError("facet_by must be 'month' or 'study_area'")
    frame = _select(results, tau, filters)
    frame = frame.assign(_facet=frame[facet_by].map(_month) if facet_by == "month" else frame[facet_by].astype(str))
    facets = sorted(frame["_facet"].unique())
    ncols = max(1, min(ncols, len(facets)))
    nrows = math.ceil(len(facets) / ncols)
    if ax is None:
        fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3.8 * nrows), sharey=True, squeeze=False)
    else:
        flat = np.asarray(ax, dtype=object).ravel()
        if len(flat) < len(facets):
            raise ValueError("Not enough axes supplied for all facets")
        fig = flat[0].figure
        axes = flat[:len(facets)].reshape(1, -1)
    group_by = "study_area" if facet_by == "month" else "month"
    for facet, facet_ax in zip(facets, axes.ravel()):
        plot_change_timeseries(
            results, group_by, {**(filters or {}), facet_by: facet},
            show_ci_for, facet_ax, tau, highlight,
        )
        facet_ax.set_title(month_name(facet) if facet_by == "month" else facet)
    for facet_ax in axes.ravel()[len(facets):]:
        facet_ax.set_visible(False)
    fig.tight_layout()
    add_shared_legend(fig, axes.ravel()[:len(facets)], title=group_by.replace("_", " "))
    return fig, axes


def plot_change_heatmap(
    results: pd.DataFrame,
    month: str | int,
    ax: Axes | None = None,
    tau: float | None = None,
    sites: Sequence[str] | None = None,
    limit: float | None = None,
    cmap: str = "BrBG",
    colorbar: bool = True,
) -> tuple[Figure, Axes]:
    """Plot mean changes as a zero-centered site-by-year-pair heatmap.

    Each cell is labeled with its mean change; an asterisk marks adjusted CIs
    that exclude zero.

    Parameters
    ----------
    results : pandas.DataFrame
        Results produced by the analysis module.
    month : str or int
        Month to display.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw.
    tau : float, optional
        Threshold to plot; defaults to the primary tau.
    sites : sequence of str, optional
        Study areas and row order; defaults to the sorted areas present.
    limit : float, optional
        Symmetric color limit. Pass a shared value to compare panels; defaults
        to the largest absolute change shown.
    cmap : str
        Diverging colormap centered at zero.
    colorbar : bool
        Draw a per-panel colorbar. Set False with a shared ``limit`` when
        combining panels with ``plot_style.finish_panel_grid``.

    Returns
    -------
    tuple
        Figure and axes containing the heatmap.
    """
    frame = _select(results, tau, {"month": month})
    pairs = _pairs(frame)
    areas = list(sites) if sites is not None else sorted(frame["study_area"].astype(str).unique())
    frame = frame.assign(
        study_area=frame["study_area"].astype(str),
        _pair=[_pair_label(a, b) for a, b in zip(frame.year_start, frame.year_end)],
    )
    labels = [_pair_label(*pair) for pair in pairs]
    grid = frame.pivot(index="study_area", columns="_pair", values="mean_change")
    values = grid.reindex(index=areas, columns=labels).to_numpy(dtype=float)
    significant = (
        frame.pivot(index="study_area", columns="_pair", values="ci_excludes_zero")
        .reindex(index=areas, columns=labels)
        .fillna(False).astype(bool).to_numpy()
    )
    if limit is None:
        finite = np.abs(values[np.isfinite(values)])
        limit = float(finite.max()) if finite.size else 1.0
    limit = limit if limit > 0 else 1.0
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (len(labels) * 0.8 + 3.5, len(areas) * 0.8 + 1.8))
    image = ax.imshow(values, aspect="equal", cmap=cmap, norm=norm)
    cell_labels = np.array([
        [f"{value:+.3f}{'*' if flag else ''}" for value, flag in zip(row, flags)]
        for row, flags in zip(values, significant)
    ])
    annotate_cells(ax, image, values, cell_labels)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(len(areas)), areas)
    ax.set_xlabel("Year pair")
    ax.set_ylabel("Study area")
    ax.set_title(f"Mean change by study area, {month_name(month)}")
    if colorbar:
        fig.colorbar(image, ax=ax, label="Mean index change")
    if owns_figure:
        fig.tight_layout()
    return fig, ax


def _identifiers(pair: object) -> dict[str, object]:
    """Extract pair identifiers from a mapping or PairSpec-like object."""
    keys = ("study_area", "month", "year_start", "year_end")
    if isinstance(pair, Mapping):
        return {key: pair[key] for key in keys}
    try:
        return {key: getattr(pair, key) for key in keys}
    except AttributeError as exc:
        raise ValueError("pair must expose study_area, month, year_start, and year_end") from exc


def plot_correlogram(
    correlograms: pd.DataFrame,
    results: pd.DataFrame,
    pair: object,
    ax: Axes | None = None,
    tau: float | None = None,
) -> tuple[Figure, Axes]:
    """Plot saved Moran's I values, sensitivity thresholds, and selected range.

    Parameters
    ----------
    correlograms : pandas.DataFrame
        Saved correlogram table.
    results : pandas.DataFrame
        Saved result table containing range estimates and thresholds.
    pair : PairSpec or mapping
        Pair identifiers: study area, month, start year, and end year.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw.
    tau : float, optional
        Threshold used to choose the range; defaults to primary tau.

    Returns
    -------
    tuple
        Figure and axes containing the plot.

    Raises
    ------
    ValueError
        If no correlogram rows match ``pair``.
    """
    keys = _identifiers(pair)
    data = correlograms.copy()
    selected = results.copy()
    for column, value in keys.items():
        if column == "month":
            data = data.loc[data[column].map(_month) == _month(value)]
            selected = selected.loc[selected[column].map(_month) == _month(value)]
        else:
            data = data.loc[data[column] == value]
            selected = selected.loc[selected[column] == value]
    if data.empty:
        raise ValueError("No correlogram rows match the requested pair")
    pair_results = selected
    selected = _select(selected, tau)
    result = selected.iloc[0]
    fig, ax = _figure_axes(ax)
    ax.plot(data["lag"], data["moran_i"], color="C0", marker="o", markersize=3, linewidth=1)
    thresholds = sorted(pair_results["tau"].dropna().unique())
    for threshold in thresholds:
        ax.axhline(float(threshold), linestyle="--", linewidth=0.9, alpha=0.7, label=f"tau={threshold:g}")
    ax.axhline(0, color="black", linewidth=0.8)
    if pd.notna(result["range_px"]):
        ax.axvline(float(result["range_px"]), color="C3", linestyle=":", label=f"range={int(result['range_px'])}")
    ax.set_xlabel("Lag (pixels)")
    ax.set_ylabel("Moran's I")
    ax.set_title(f"{keys['study_area']} {month_name(keys['month'])} {keys['year_start']}-{keys['year_end']}")
    add_gridlines(ax)
    if thresholds or pd.notna(result["range_px"]):
        ax.legend()
    fig.tight_layout()
    return fig, ax


def plot_n_eff(
    results: pd.DataFrame,
    min_n_eff: float = 30,
    ax: Axes | None = None,
    tau: float | None = None,
) -> tuple[Figure, Axes]:
    """Plot effective sample size across pairs with the flag threshold.

    Parameters
    ----------
    results : pandas.DataFrame
        Results produced by the analysis module.
    min_n_eff : float
        Low-effective-sample-size threshold.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw.
    tau : float, optional
        Threshold to plot; defaults to primary tau.

    Returns
    -------
    tuple
        Figure and axes containing the plot.
    """
    frame = _select(results, tau).sort_values(["study_area", "month", "year_start", "year_end"]).reset_index(drop=True)
    fig, ax = _figure_axes(ax, (max(9, len(frame) * 0.38), 5))
    x = np.arange(len(frame))
    valid = np.isfinite(frame["n_eff"].to_numpy(dtype=float))
    ax.scatter(x[valid], frame.loc[valid, "n_eff"], c="C0", s=28, zorder=3)
    ax.axhline(min_n_eff, color="C3", linestyle="--", label=f"minimum n_eff={min_n_eff:g}")
    labels = [f"{row.study_area}\n{month_name(row.month)} {_pair_label(row.year_start, row.year_end)}" for row in frame.itertuples()]
    ax.set_xticks(x, labels, rotation=70, ha="right", fontsize=8)
    ax.set_ylabel("Effective sample size")
    add_gridlines(ax)
    ax.legend()
    fig.tight_layout()
    return fig, ax


def plot_tau_sensitivity(
    results: pd.DataFrame,
    filters: Mapping[str, Any] | None = None,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Compare adjusted confidence intervals across saved tau thresholds.

    Parameters
    ----------
    results : pandas.DataFrame
        Results table containing all sensitivity thresholds.
    filters : mapping, optional
        Column/value filters applied before plotting.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw.

    Returns
    -------
    tuple
        Figure and axes containing the sensitivity comparison.
    """
    frame = results.copy()
    for column, value in (filters or {}).items():
        if column not in frame:
            raise ValueError(f"Unknown results filter column: {column}")
        if column == "month":
            series = frame[column].map(_month)
            frame = frame.loc[series.isin(map(_month, value))] if isinstance(value, (list, tuple, set)) else frame.loc[series == _month(value)]
        elif isinstance(value, (list, tuple, set, frozenset)):
            frame = frame.loc[frame[column].isin(value)]
        else:
            frame = frame.loc[frame[column] == value]
    if frame.empty:
        raise ValueError("No result rows match the requested selection")
    pair_ids = sorted({(str(r.study_area), _month(r.month), int(r.year_start), int(r.year_end)) for r in frame.itertuples()})
    taus = sorted(frame["tau"].dropna().unique())
    positions = {pair: index for index, pair in enumerate(pair_ids)}
    offsets = np.linspace(-0.22, 0.22, len(taus)) if len(taus) > 1 else np.array([0.0])
    fig, ax = _figure_axes(ax, (max(8, len(pair_ids) * 0.8), 5))
    for index, (threshold, offset) in enumerate(zip(taus, offsets)):
        rows = frame.loc[np.isclose(frame["tau"].astype(float), threshold)]
        x = np.array([positions[(str(r.study_area), _month(r.month), int(r.year_start), int(r.year_end))] + offset
                      for r in rows.itertuples()])
        color = f"C{index % 10}"
        ax.plot(x, rows["mean_change"], marker="o", linestyle="none", color=color, label=f"tau={threshold:g}")
        _errorbars(ax, x, rows, color)
    ax.axhline(0, color="black", linewidth=0.8)
    labels = [f"{area}\n{month_name(month)} {_pair_label(start, end)}" for area, month, start, end in pair_ids]
    ax.set_xticks(range(len(pair_ids)), labels, rotation=55, ha="right", fontsize=8)
    ax.set_ylabel("Mean index change and adjusted CI")
    add_gridlines(ax)
    ax.legend(title="Range threshold")
    fig.tight_layout()
    return fig, ax


def save_figure(fig: Figure, path: str | Path, dpi: int = 180) -> Path:
    """Save a figure after creating its parent directory.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to save.
    path : str or pathlib.Path
        Destination image path.
    dpi : int
        Output resolution in dots per inch.

    Returns
    -------
    pathlib.Path
        Saved figure path.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=dpi, bbox_inches="tight")
    return destination
"""Plots for saved index-level confidence interval results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from plot_style import FIGURE_DPI, add_gridlines, add_title, annotate_cells, month_name, site_label


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
            if isinstance(value, (list, tuple, set)):
                frame = frame.loc[series.isin(map(_month, value))]
            else:
                frame = frame.loc[series == _month(value)]
        elif isinstance(value, (list, tuple, set, frozenset)):
            frame = frame.loc[frame[column].isin(value)]
        else:
            frame = frame.loc[frame[column] == value]
    if frame.empty:
        raise ValueError("No result rows match the requested selection")
    return frame


def _series_label(group: str, group_by: str) -> str:
    """Display month series by name and site series by display name."""
    return month_name(group) if group_by == "month" else site_label(group)


def _figure_axes(
    ax: Axes | None, figsize: tuple[float, float] = (9, 5)
) -> tuple[Figure, Axes]:
    """Return an existing axes or create a new figure and axes."""
    return plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)


def plot_index_timeseries(
    results: pd.DataFrame,
    group_by: str = "month",
    filters: Mapping[str, Any] | None = None,
    show_ci_for: str | Sequence[str] | None = "all",
    ax: Axes | None = None,
    tau: float | None = None,
    highlight: str | None = None,
    base_year: int | None = None,
) -> tuple[Figure, Axes]:
    """Plot annual spatial means with optional spatial CI bands.

    ``group_by`` may be ``month`` or ``study_area``. Other series are dotted
    when ``highlight`` is set, allowing one site and its CI band to stand out.
    When ``base_year`` is set, each series is shown as percent change from its
    own base-year mean. CI bounds are rescaled by the same fixed base value, so
    bands reflect uncertainty in each year's mean but not in the base year.
    """
    if group_by not in {"month", "study_area"}:
        raise ValueError("group_by must be 'month' or 'study_area'")
    frame = _select(results, tau, filters)
    frame = frame.assign(
        _series=frame[group_by].map(_month)
        if group_by == "month" else frame[group_by].astype(str)
    )
    groups = sorted(frame["_series"].unique())
    if highlight is not None and highlight not in groups:
        raise ValueError(f"Highlighted series not present: {highlight}")
    years = sorted(frame["year"].astype(int).unique())
    if base_year is not None:
        frame = _relative_to_base_year(frame, int(base_year))
    other_colors = [
        f"C{color_index}" for color_index in range(10)
        if highlight is None or color_index != 3
    ]
    if isinstance(show_ci_for, str):
        ci_groups = set(groups) if show_ci_for == "all" else {show_ci_for}
    else:
        ci_groups = set(show_ci_for or ())
    owns_figure = ax is None
    fig, ax = _figure_axes(ax)
    for index, group in enumerate(groups):
        rows = frame.loc[frame["_series"] == group].sort_values("year")
        x = rows["year"].to_numpy(dtype=float)
        is_highlight = group == highlight
        color = "C3" if is_highlight else other_colors[index % len(other_colors)]
        linestyle = ":" if highlight is not None and not is_highlight else "-"
        linewidth = 2 if is_highlight else 1.1
        ax.plot(
            x, rows["mean_index"], marker="o", linestyle=linestyle,
            linewidth=linewidth, markersize=4, color=color,
            label=_series_label(group, group_by),
        )
        if group in ci_groups:
            mean = rows["mean_index"].to_numpy(dtype=float)
            low = rows["ci_low"].to_numpy(dtype=float)
            high = rows["ci_high"].to_numpy(dtype=float)
            valid = np.isfinite(mean) & np.isfinite(low) & np.isfinite(high)
            if valid.any():
                ax.fill_between(
                    x, low, high, where=valid, color=color,
                    alpha=0.18 if is_highlight else 0.12,
                    interpolate=True,
                )
    ax.set_xticks(years, years)
    ax.set_xlabel("Observation year")
    if base_year is None:
        ax.set_ylabel("Mean index value")
    else:
        ax.axhline(0, color="0.4", linewidth=0.8, zorder=0)
        ax.set_ylabel(f"Change in mean index from {int(base_year)} (%)")
    add_gridlines(ax)
    ax.legend(title=group_by.replace("_", " "))
    if owns_figure:
        fig.tight_layout()
    return fig, ax


def _relative_to_base_year(frame: pd.DataFrame, base_year: int) -> pd.DataFrame:
    """Express mean and CI columns as percent change from each series' base year."""
    years = frame["year"].astype(int)
    base = frame.loc[years == base_year].set_index("_series")["mean_index"]
    if base.index.duplicated().any():
        raise ValueError(f"Multiple {base_year} rows per series; add filters")
    missing = sorted(set(frame["_series"]) - set(base.index))
    if missing:
        raise ValueError(f"Base year {base_year} missing for series: {missing}")
    base_values = frame["_series"].map(base).astype(float)
    if not (np.isfinite(base_values) & (base_values != 0)).all():
        raise ValueError(f"Base year {base_year} mean must be finite and non-zero")
    frame = frame.copy()
    for column in ("mean_index", "ci_low", "ci_high"):
        if column in frame:
            frame[column] = 100.0 * (frame[column].astype(float) / base_values - 1.0)
    return frame


def plot_index_heatmap(
    results: pd.DataFrame,
    month: str | int,
    ax: Axes | None = None,
    tau: float | None = None,
    sites: Sequence[str] | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    cmap: str = "YlGn",
    colorbar: bool = True,
) -> tuple[Figure, Axes]:
    """Plot annual mean index values as a site-by-year heatmap.

    Set ``colorbar=False`` with shared ``vmin``/``vmax`` when combining
    panels with ``plot_style.finish_panel_grid``.
    """
    frame = _select(results, tau, {"month": month})
    areas = list(sites) if sites is not None else sorted(frame["study_area"].astype(str).unique())
    years = sorted(frame["year"].astype(int).unique())
    grid = frame.pivot(index="study_area", columns="year", values="mean_index")
    values = grid.reindex(index=areas, columns=years).to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    if vmin is None:
        vmin = float(finite.min()) if finite.size else 0.0
    if vmax is None:
        vmax = float(finite.max()) if finite.size else 1.0
    if vmax <= vmin:
        padding = max(abs(vmin) * 0.01, 0.01)
        vmin, vmax = vmin - padding, vmax + padding
    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (len(years) * 0.7 + 3.5, len(areas) * 0.7 + 1.8))
    image = ax.imshow(
        values, aspect="equal", cmap=cmap, norm=Normalize(vmin=vmin, vmax=vmax)
    )
    labels = np.vectorize(lambda value: f"{value:.2f}", otypes=[str])(values)
    annotate_cells(ax, image, values, labels)
    ax.set_xticks(range(len(years)), years)
    ax.set_yticks(range(len(areas)), [site_label(area) for area in areas])
    ax.set_xlabel("Observation year")
    ax.set_ylabel("Study area")
    add_title(ax, f"Mean index value by study area, {month_name(month)}", panel=not owns_figure)
    if colorbar:
        fig.colorbar(image, ax=ax, label="Mean index value")
    if owns_figure:
        fig.tight_layout()
    return fig, ax


def plot_index_n_eff(
    results: pd.DataFrame,
    group_by: str = "study_area",
    filters: Mapping[str, Any] | None = None,
    min_n_eff: float = 30,
    ax: Axes | None = None,
    tau: float | None = None,
) -> tuple[Figure, Axes]:
    """Plot effective sample size by observation year."""
    if group_by not in {"month", "study_area"}:
        raise ValueError("group_by must be 'month' or 'study_area'")
    frame = _select(results, tau, filters)
    frame = frame.assign(
        _series=frame[group_by].map(_month)
        if group_by == "month" else frame[group_by].astype(str)
    )
    groups = sorted(frame["_series"].unique())
    years = sorted(frame["year"].astype(int).unique())
    owns_figure = ax is None
    fig, ax = _figure_axes(ax)
    for index, group in enumerate(groups):
        rows = frame.loc[frame["_series"] == group].sort_values("year")
        ax.plot(
            rows["year"], rows["n_eff"], marker="o", linewidth=1,
            color=f"C{index % 10}", label=_series_label(group, group_by),
        )
    ax.axhline(min_n_eff, color="C3", linestyle="--", label=f"minimum n_eff={min_n_eff:g}")
    ax.set_xticks(years, years)
    ax.set_xlabel("Observation year")
    ax.set_ylabel("Effective sample size")
    add_gridlines(ax)
    ax.legend(title=group_by.replace("_", " "))
    if owns_figure:
        fig.tight_layout()
    return fig, ax


def plot_index_correlogram(
    correlograms: pd.DataFrame,
    results: pd.DataFrame,
    observation: Mapping[str, object],
    ax: Axes | None = None,
    tau: float | None = None,
) -> tuple[Figure, Axes]:
    """Plot Moran's I, threshold sensitivity, and the selected range."""
    keys = ("study_area", "index", "month", "year")
    data = correlograms.copy()
    selected = results.copy()
    for column in keys:
        if column not in observation:
            raise ValueError(f"observation must include {column!r}")
        value = observation[column]
        if column == "month":
            data = data.loc[data[column].map(_month) == _month(value)]
            selected = selected.loc[selected[column].map(_month) == _month(value)]
        else:
            data = data.loc[data[column] == value]
            selected = selected.loc[selected[column] == value]
    if data.empty:
        raise ValueError("No correlogram rows match the requested observation")
    thresholds = sorted(selected["tau"].dropna().unique())
    primary = _select(selected, tau).iloc[0]
    owns_figure = ax is None
    fig, ax = _figure_axes(ax)
    ax.plot(data["lag"], data["moran_i"], color="C0", marker="o", markersize=3)
    for threshold in thresholds:
        ax.axhline(
            float(threshold), linestyle="--", linewidth=0.9,
            alpha=0.7, label=f"tau={threshold:g}",
        )
    ax.axhline(0, color="black", linewidth=0.8)
    if pd.notna(primary["range_px"]):
        ax.axvline(
            float(primary["range_px"]), color="C3", linestyle=":",
            label=f"range={int(primary['range_px'])}",
        )
    ax.set_xlabel("Lag (pixels)")
    ax.set_ylabel("Moran's I")
    ax.set_title(
        f"{site_label(observation['study_area'])} {observation['index']} "
        f"{month_name(observation['month'])} {observation['year']}"
    )
    add_gridlines(ax)
    if thresholds or pd.notna(primary["range_px"]):
        ax.legend()
    if owns_figure:
        fig.tight_layout()
    return fig, ax


def save_figure(fig: Figure, path: Path, dpi: int = FIGURE_DPI) -> None:
    """Create the destination directory and save a figure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")

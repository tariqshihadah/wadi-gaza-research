"""Plot saved climate-context outputs without recomputing summaries."""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import ListedColormap, TwoSlopeNorm
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from plot_style import FIGURE_DPI, add_gridlines, add_title, annotate_cells, contrast_text_color, month_name

from .windows import season_label

MONTH_ABBR = {m: calendar.month_abbr[m] for m in range(1, 13)}


def _figure_axes(ax: Axes | None, figsize: tuple[float, float]) -> tuple[Figure, Axes]:
    return plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)


def plot_cells_map(
    sites: gpd.GeoDataFrame, cells: gpd.GeoDataFrame, ax: Axes | None = None
) -> tuple[Figure, Axes]:
    """Plot site polygons over the ERA5-Land region grid.

    Parameters
    ----------
    sites : geopandas.GeoDataFrame
        Site polygons in any CRS.
    cells : geopandas.GeoDataFrame
        Cell layer with ``cell_id``, ``cell_lat``, ``cell_lon``, ``has_data``
        and ``used`` columns (``era5land_cells.gpkg``). Cells used by a site
        are outlined in blue and labelled; cells without data are hatched.
    """
    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (7, 8))
    used = cells.loc[cells["used"].astype(bool)]
    empty = cells.loc[~cells["has_data"].astype(bool)]
    cells.loc[cells["has_data"].astype(bool)].boundary.plot(ax=ax, color="lightgrey", linewidth=0.6)
    if len(empty):
        empty.plot(ax=ax, facecolor="none", edgecolor="lightgrey", hatch="//", linewidth=0.6)
    used.boundary.plot(ax=ax, color="tab:blue", linewidth=1.4)
    sites.to_crs(4326).plot(ax=ax, color="tab:green", edgecolor="black", linewidth=0.5)
    for row in used.itertuples():
        ax.annotate(row.cell_id, (row.cell_lon - 0.047, row.cell_lat - 0.047), ha="left", va="bottom",
                    fontsize=7, color="tab:blue",
                    bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 0.5})
    handles = [Patch(facecolor="none", edgecolor="tab:blue", label="Cell used by a site"),
               Patch(facecolor="none", edgecolor="lightgrey", label="Cell with data"),
               Patch(facecolor="none", edgecolor="lightgrey", hatch="//", label="No data (sea)"),
               Patch(facecolor="tab:green", edgecolor="black", label="Study site")]
    ax.legend(handles=handles, loc="lower right", fontsize=8)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    add_title(ax, "Study sites over the ERA5-Land 0.1\N{DEGREE SIGN} grid", panel=not owns_figure)
    return fig, ax


def plot_cell_values(
    cells: gpd.GeoDataFrame,
    values: pd.Series,
    sites: gpd.GeoDataFrame | None = None,
    ax: Axes | None = None,
    label: str = "",
    cmap: str = "viridis",
    centre: float | None = None,
    limits: tuple[float, float] | None = None,
    annotate: bool = True,
    fmt: str | None = None,
    colorbar: bool = True,
) -> tuple[Figure, Axes]:
    """Map one value per cell over the region grid, with optional site outlines.

    ``values`` is indexed by ``cell_id``; cells without a value are left blank.
    A ``centre`` gives a diverging scale centred on that value. ``limits``
    fixes the colour range so several maps can share one scale. ``fmt`` is a
    format string for cell labels, such as ``"{:.1f}"``; by default values of
    10 or more show no decimals and smaller values show one. Set
    ``colorbar=False`` with shared ``limits`` when combining maps with
    ``plot_style.finish_panel_grid``.
    """
    frame = cells.assign(value=cells["cell_id"].map(values))
    fig, ax = _figure_axes(ax, (6, 7))
    finite = frame["value"].dropna()
    if limits is not None:
        low, high = limits
    elif centre is not None:
        spread = float((finite - centre).abs().max()) if len(finite) else 1.0
        low, high = centre - (spread or 1.0), centre + (spread or 1.0)
    else:
        low, high = (float(finite.min()), float(finite.max())) if len(finite) else (0.0, 1.0)
    norm = TwoSlopeNorm(vmin=low, vcenter=centre, vmax=high) if centre is not None else plt.Normalize(low, high)
    frame.loc[frame["value"].notna()].plot(ax=ax, column="value", cmap=cmap, norm=norm,
                                            edgecolor="white", linewidth=0.4)
    frame.loc[frame["value"].isna()].plot(ax=ax, facecolor="none", edgecolor="lightgrey",
                                          hatch="//", linewidth=0.4)
    if sites is not None:
        sites.to_crs(4326).boundary.plot(ax=ax, color="black", linewidth=0.8)
    if annotate:
        for row in frame.loc[frame["value"].notna()].itertuples():
            if fmt is not None:
                text = fmt.format(row.value)
            else:
                text = f"{row.value:.0f}" if abs(row.value) >= 10 else f"{row.value:.1f}"
            ax.text(row.cell_lon, row.cell_lat, text, ha="center", va="center", fontsize=7,
                    color=contrast_text_color(plt.get_cmap(cmap)(norm(row.value))))
    if colorbar:
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, label=label, shrink=0.8)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    return fig, ax


def plot_summary_heatmap(
    summary: pd.DataFrame,
    value: str,
    month: int,
    ax: Axes | None = None,
    flag: str | None = None,
    label: str | None = None,
    sites: Sequence[str] | None = None,
    limit: float | None = None,
    colorbar: bool = True,
) -> tuple[Figure, Axes]:
    """Plot one summary column as a site-by-year heatmap for a study month.

    Diverging colours are centred on zero for anomalies, or on 100 when
    ``value`` ends in ``pct_normal``. Cells where ``flag`` is true are hatched
    (for example a near-zero normal that leaves percent of normal blank).
    ``limit`` is the colour half-range around the centre; pass one value for
    every month, with ``colorbar=False``, to combine panels with
    ``plot_style.finish_panel_grid``. By default it is the largest deviation
    shown. Percent-of-normal scales stop at zero.
    """
    frame = summary.loc[summary["month"] == month]
    if frame.empty:
        raise ValueError(f"No summary rows for month {month}")
    sites = list(sites) if sites is not None else sorted(frame["site"].unique())
    years = sorted(frame["year"].unique())
    grid = frame.pivot(index="site", columns="year", values=value).reindex(index=sites, columns=years)
    values = grid.to_numpy(dtype=float)
    centre = 100.0 if value.endswith("pct_normal") else 0.0
    if limit is None:
        finite = np.abs(values[np.isfinite(values)] - centre)
        limit = float(finite.max()) if len(finite) else 1.0
    limit = limit if limit > 0 else 1.0
    # Percent of normal cannot be negative, so the scale stops at zero.
    vmin = max(centre - limit, 0.0) if centre else -limit
    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (len(years) * 0.7 + 3.5, len(sites) * 0.7 + 1.8))
    image = ax.imshow(values, aspect="equal", cmap="BrBG" if "precip" in value else "RdBu_r",
                      norm=TwoSlopeNorm(vmin=vmin, vcenter=centre, vmax=centre + limit))
    if flag is not None:
        flags = frame.pivot(index="site", columns="year", values=flag).reindex(index=sites, columns=years)
        for (i, j), flagged in np.ndenumerate(flags.fillna(False).to_numpy(dtype=bool)):
            if flagged:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, hatch="///",
                                           edgecolor="grey", linewidth=0))
    labels = np.vectorize(lambda number: f"{number:.0f}" if abs(number) >= 10 else f"{number:.1f}",
                          otypes=[str])(values)
    annotate_cells(ax, image, values, labels)
    ax.set_xticks(range(len(years)), years)
    ax.set_yticks(range(len(sites)), sites)
    ax.set_xlabel("Observation year")
    ax.set_ylabel("Site")
    add_title(ax, f"{label or value}, {month_name(month)}", panel=not owns_figure)
    if colorbar:
        fig.colorbar(image, ax=ax, label=label or value)
    return fig, ax


def plot_wet_season_heatmap(
    summary: pd.DataFrame, ax: Axes | None = None, sites: Sequence[str] | None = None
) -> tuple[Figure, Axes]:
    """Plot wet-season percent of normal by site and season label."""
    frame = summary.drop_duplicates(["site", "wet_season_label"])
    sites = list(sites) if sites is not None else sorted(frame["site"].unique())
    labels = sorted(frame["wet_season_label"].unique())
    grid = frame.pivot(index="site", columns="wet_season_label",
                       values="wet_season_precip_pct_normal").reindex(index=sites, columns=labels)
    values = grid.to_numpy(dtype=float)
    finite = np.abs(values[np.isfinite(values)] - 100)
    limit = float(finite.max()) if len(finite) and finite.max() > 0 else 1.0
    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (len(labels) * 0.7 + 3.5, len(sites) * 0.7 + 2.2))
    image = ax.imshow(values, aspect="equal", cmap="BrBG",
                      norm=TwoSlopeNorm(vmin=100 - limit, vcenter=100, vmax=100 + limit))
    annotate_cells(ax, image, values, np.vectorize(lambda number: f"{number:.0f}", otypes=[str])(values))
    ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right")
    ax.set_yticks(range(len(sites)), sites)
    ax.set_xlabel("Wet season (October to April)")
    add_title(ax, "Wet-season precipitation, percent of 1991\N{EN DASH}2020 normal", panel=not owns_figure)
    fig.colorbar(image, ax=ax, label="% of normal")
    return fig, ax


def plot_temperature_anomalies(
    summary: pd.DataFrame, site: str, ax: Axes | None = None
) -> tuple[Figure, Axes]:
    """Plot monthly temperature anomalies by year for one site, both methods."""
    frame = summary.loc[summary["site"] == site]
    if frame.empty:
        raise ValueError(f"No summary rows for site {site}")
    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (9, 4.5))
    months = sorted(frame["month"].unique())
    colours = plt.cm.tab10(np.arange(len(months)))
    for colour, month in zip(colours, months):
        rows = frame.loc[frame["month"] == month].sort_values("year")
        ax.plot(rows["year"], rows["t2m_mean_24h_anom_c"], "-o", color=colour, markersize=4,
                label=f"{month_name(month)} 24-hour mean")
        ax.plot(rows["year"], rows["t2m_midrange_anom_c"], "--", color=colour, linewidth=1,
                label=f"{month_name(month)} midrange")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Observation year")
    ax.set_ylabel("Anomaly from 1991\N{EN DASH}2020 normal (\N{DEGREE SIGN}C)")
    add_title(ax, f"{site}: monthly temperature anomaly", panel=not owns_figure)
    add_gridlines(ax)
    ax.legend(ncol=2, fontsize=8)
    return fig, ax


def plot_climatology(
    normals: pd.DataFrame,
    daily: pd.DataFrame,
    cell_id: str,
    years: Sequence[int],
    ax: Axes | None = None,
    marker_size: float = 3.7,
    outline: bool = False,
    connect: bool = False,
    cmap: str = "viridis",
    cmap_range: tuple[float, float] = (0.0, 0.9),
    start_month: int = 1,
) -> tuple[Figure, Axes]:
    """Plot monthly precipitation normals (+/-1 SD) with observed monthly totals overlaid.

    The x axis runs for twelve months from ``start_month``. With the default
    January start, ``years`` are calendar years. With any other start they are
    the ending years of twelve-month seasons, labelled like ``2019/20``, so
    ``start_month=7`` with ``years=[2020]`` plots July 2019 to June 2020.

    ``marker_size`` is the observed-point diameter in points. ``outline`` adds a
    dark edge to each point, and ``connect`` joins each year's months with a
    dashed line. ``cmap`` colours the years: qualitative maps (such as
    ``"tab10"``) assign their colours in order, continuous maps are sampled
    evenly across ``cmap_range``.
    """
    if not 1 <= start_month <= 12:
        raise ValueError("start_month must be between 1 and 12")
    rows = normals.loc[(normals["cell_id"] == cell_id) & (normals["measure"] == "precip_mm")]
    rows = rows.assign(position=(rows["month"] - start_month) % 12).sort_values("position")
    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (8, 4))
    ax.bar(rows["position"], rows["mean"], yerr=rows["sd"], color="lightgrey", edgecolor="grey",
           capsize=3, label="1991\N{EN DASH}2020 normal \N{PLUS-MINUS SIGN}1 SD")
    cell = daily.loc[daily["cell_id"] == cell_id].copy()
    dates = pd.to_datetime(cell["date"])
    shift = (dates.dt.month >= start_month).astype(int) if start_month > 1 else 0
    cell = cell.assign(year=dates.dt.year + shift, month=dates.dt.month)
    cell = cell.loc[cell["year"].isin(years)]
    totals = cell.groupby(["year", "month"])["precip_mm"].sum(min_count=1).reset_index()
    totals["position"] = (totals["month"] - start_month) % 12
    colormap = plt.get_cmap(cmap)
    if isinstance(colormap, ListedColormap) and colormap.N >= len(years) and colormap.N <= 20:
        colours = colormap(np.arange(len(years)))
    else:
        colours = colormap(np.linspace(*cmap_range, len(years)))
    for colour, year in zip(colours, years):
        observed = totals.loc[totals["year"] == year].sort_values("position")
        ax.plot(observed["position"], observed["precip_mm"], linestyle="--" if connect else "none",
                linewidth=1.1, color=(*colour[:3], 0.90), marker="o", markersize=marker_size,
                markerfacecolor=colour, markeredgecolor="#222222" if outline else colour,
                markeredgewidth=0.7 if outline else 0,
                label=str(year) if start_month == 1 else season_label(year), zorder=3)
    ax.set_xticks(range(12), [MONTH_ABBR[(start_month - 1 + i) % 12 + 1] for i in range(12)])
    ax.set_ylabel("Precipitation (mm)")
    add_title(ax, f"{cell_id}: monthly precipitation", panel=not owns_figure)
    add_gridlines(ax, axis="y")
    ax.legend(fontsize=7, ncol=2)
    return fig, ax


def plot_cumulative_seasons(
    daily: pd.DataFrame,
    cell_id: str,
    end_years: Sequence[int],
    reference_end_years: Sequence[int],
    ax: Axes | None = None,
    start_month: int = 10,
) -> tuple[Figure, Axes]:
    """Plot cumulative precipitation since October 1 for selected seasons.

    The reference envelope is the mean and +/-1 SD of the same curve over the
    reference seasons (labelled by ending year). Each curve runs from October
    1 to September 30.
    """
    cell = daily.loc[daily["cell_id"] == cell_id, ["date", "precip_mm"]].copy()
    cell["date"] = pd.to_datetime(cell["date"])
    cell["end_year"] = np.where(cell["date"].dt.month >= start_month,
                                cell["date"].dt.year + 1, cell["date"].dt.year)
    cell["day"] = (cell["date"] - pd.to_datetime(
        (cell["end_year"] - 1).astype(str) + f"-{start_month:02d}-01")).dt.days
    cell = cell.loc[cell["day"] < 365]
    cell["cumulative"] = cell.groupby("end_year")["precip_mm"].cumsum()
    curves = cell.pivot(index="day", columns="end_year", values="cumulative")

    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (9, 5))
    reference = curves.reindex(columns=list(reference_end_years))
    mean, sd = reference.mean(axis=1), reference.std(axis=1, ddof=1)
    ax.fill_between(curves.index, mean - sd, mean + sd, color="lightgrey",
                    label="1991\N{EN DASH}2020 normal \N{PLUS-MINUS SIGN}1 SD")
    ax.plot(curves.index, mean, color="black", linewidth=1.2, label="1991\N{EN DASH}2020 normal")
    colours = plt.cm.viridis(np.linspace(0, 0.9, len(end_years)))
    for colour, year in zip(colours, end_years):
        if year in curves:
            ax.plot(curves.index, curves[year], color=colour, linewidth=1.2, label=season_label(year))
    ticks = pd.date_range(f"2001-{start_month:02d}-01", periods=12, freq="MS")
    ax.set_xticks((ticks - ticks[0]).days, [t.strftime("%b") for t in ticks])
    ax.set_xlim(0, 364)
    ax.set_ylabel("Cumulative precipitation since October 1 (mm)")
    add_title(ax, f"{cell_id}: cumulative precipitation since October 1", panel=not owns_figure)
    add_gridlines(ax)
    ax.legend(fontsize=8, ncol=2, loc="upper left")
    return fig, ax


def plot_temperature_method_difference(
    daily: pd.DataFrame, ax: Axes | None = None
) -> tuple[Figure, Axes]:
    """Plot the mean (midrange minus 24-hour mean) daily temperature by calendar month and cell."""
    frame = daily.assign(
        month=pd.to_datetime(daily["date"]).dt.month,
        diff=daily["t2m_midrange_c"] - daily["t2m_mean_24h_c"],
    )
    table = frame.groupby(["month", "cell_id"])["diff"].mean().unstack()
    owns_figure = ax is None
    fig, ax = _figure_axes(ax, (8, 4))
    for cell in table.columns:
        ax.plot(table.index, table[cell], "-o", markersize=3, label=cell)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(1, 13), [MONTH_ABBR[m] for m in range(1, 13)])
    ax.set_ylabel("Midrange minus 24-hour mean (\N{DEGREE SIGN}C)")
    add_title(ax, "Daily temperature method difference, 1990\N{EN DASH}2025 mean", panel=not owns_figure)
    add_gridlines(ax)
    ax.legend(fontsize=8, ncol=2)
    return fig, ax


def save_figure(fig: Figure, path: str | Path, dpi: int = FIGURE_DPI) -> Path:
    """Save a figure after creating its parent directory and return the path."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=dpi, bbox_inches="tight")
    return destination

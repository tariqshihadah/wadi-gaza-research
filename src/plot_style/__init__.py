"""Shared figure styling for the project's plotting modules."""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from matplotlib.layout_engine import ConstrainedLayoutEngine
from matplotlib.legend import Legend

PanelAxes = Axes | Sequence[Axes] | np.ndarray
CELL_FONTSIZE = 9


def month_name(month: object) -> str:
    """Return the full English month name for a month number such as 9 or '09'."""
    return calendar.month_name[int(month)]


def contrast_text_color(rgba: Sequence[float]) -> str:
    """Return black or white, whichever has the higher WCAG contrast with ``rgba``."""
    channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgba[:3]]
    luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    return "black" if (luminance + 0.05) / 0.05 >= 1.05 / (luminance + 0.05) else "white"


def annotate_cells(
    ax: Axes,
    image: AxesImage,
    values: np.ndarray,
    labels: np.ndarray,
    fontsize: float = CELL_FONTSIZE,
) -> None:
    """Label each finite heatmap cell in black or white, whichever reads best on its colour."""
    for (row, column), value in np.ndenumerate(np.asarray(values, dtype=float)):
        if np.isfinite(value) and labels[row, column]:
            ax.text(
                column, row, labels[row, column], ha="center", va="center",
                fontsize=fontsize, color=contrast_text_color(image.to_rgba(value)),
            )


def _panels(axes: PanelAxes) -> list[Axes]:
    """Flatten an axes container and keep the visible panels."""
    return [ax for ax in np.ravel(np.asarray(axes, dtype=object)) if ax.get_visible()]


def add_gridlines(ax: Axes, axis: str = "both") -> None:
    """Draw light gridlines behind the plotted data."""
    ax.grid(True, axis=axis, color="0.88", linewidth=0.7)
    ax.set_axisbelow(True)


def add_shared_legend(
    fig: Figure,
    axes: PanelAxes,
    title: str | None = None,
    ncol: int | None = None,
) -> Legend | None:
    """Replace per-panel legends with one legend centered below the figure.

    Entries are merged by label across panels, so a series missing from one
    panel still appears. The legend hangs below the figure; saving with
    ``bbox_inches="tight"`` and inline notebook display keep it in frame.
    """
    handles: dict[str, Any] = {}
    for panel in _panels(axes):
        for handle, label in zip(*panel.get_legend_handles_labels()):
            handles.setdefault(label, handle)
        if panel.get_legend() is not None:
            panel.get_legend().remove()
    if not handles:
        return None
    return fig.legend(
        list(handles.values()), list(handles), title=title,
        loc="upper center", bbox_to_anchor=(0.5, 0.0),
        ncol=ncol or min(len(handles), 4), frameon=False,
    )


def _scale(mappable: ScalarMappable) -> tuple[str, float, float, float | None]:
    """Identify a colour scale by colormap name, limits, and centre."""
    norm = mappable.norm
    return (mappable.get_cmap().name, float(norm.vmin), float(norm.vmax),
            getattr(norm, "vcenter", None))


def finish_panel_grid(
    fig: Figure,
    axes: PanelAxes,
    label: str,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    wspace: float = 0.04,
    hspace: float = 0.05,
) -> Colorbar:
    """Give a grid of same-scale panels one colorbar and outer-only labels.

    Every panel must already be drawn with the same colormap and colour limits
    and share its rows and columns (for example sites by years). Tick labels
    are kept only on the left column and bottom row; inner panels keep their
    tick marks so rows and columns can be traced across the gap. Axis titles
    become figure-level labels, taken from the first panel unless ``xlabel``
    or ``ylabel`` is given. One colorbar spans the full height on the right.
    The figure uses the constrained layout engine.

    Raises
    ------
    ValueError
        If the panels have no colour-mapped artist or do not share one scale.
    """
    panels = _panels(axes)
    mappables = [
        artist for ax in panels for artist in (*ax.images, *ax.collections)
        if isinstance(artist, ScalarMappable) and artist.get_array() is not None
    ]
    if not mappables:
        raise ValueError("No colour-mapped panels to share a colorbar")
    if len({_scale(mappable) for mappable in mappables}) > 1:
        raise ValueError("Panels use different colour scales; pass shared limits")
    xlabel = panels[0].get_xlabel() if xlabel is None else xlabel
    ylabel = panels[0].get_ylabel() if ylabel is None else ylabel
    specs = {ax: ax.get_subplotspec() for ax in panels}
    for ax, spec in specs.items():
        rows, cols = spec.rowspan, spec.colspan
        below = any(
            other.rowspan.start >= rows.stop and set(other.colspan) & set(cols)
            for other in specs.values()
        )
        left = any(
            other.colspan.stop <= cols.start and set(other.rowspan) & set(rows)
            for other in specs.values()
        )
        if below:
            ax.tick_params(labelbottom=False)
        if left:
            ax.tick_params(labelleft=False)
        ax.set_xlabel("")
        ax.set_ylabel("")
    if not isinstance(fig.get_layout_engine(), ConstrainedLayoutEngine):
        fig.set_layout_engine("constrained")
    fig.get_layout_engine().set(wspace=wspace, hspace=hspace)
    size = plt.rcParams["axes.labelsize"]
    if xlabel:
        fig.supxlabel(xlabel, fontsize=size)
    if ylabel:
        fig.supylabel(ylabel, fontsize=size)
    if title:
        fig.suptitle(title)
    return fig.colorbar(mappables[0], ax=panels, label=label, aspect=40)

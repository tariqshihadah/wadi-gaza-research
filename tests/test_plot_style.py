import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from plot_style import (
    add_gridlines,
    add_shared_legend,
    annotate_cells,
    contrast_text_color,
    finish_panel_grid,
    month_name,
    site_order,
)


def _heatmap_grid(limits=((0, 1),) * 4):
    fig, axes = plt.subplots(2, 2, constrained_layout=True)
    for ax, (low, high) in zip(axes.flat, limits):
        ax.imshow(np.arange(6).reshape(2, 3), vmin=low, vmax=high, cmap="YlGn")
        ax.set_xticks(range(3), ["2019", "2020", "2021"])
        ax.set_yticks(range(2), ["SiteA", "SiteB"])
        ax.set_xlabel("Observation year")
        ax.set_ylabel("Study area")
    return fig, axes


def _labels_visible(ax, axis):
    ticks = ax.xaxis.get_major_ticks() if axis == "x" else ax.yaxis.get_major_ticks()
    return any(tick.label1.get_visible() for tick in ticks)


def test_panel_grid_keeps_outer_labels_and_one_colorbar():
    fig, axes = _heatmap_grid()
    colorbar = finish_panel_grid(fig, axes, label="Mean index", title="Title")
    assert [_labels_visible(ax, "x") for ax in axes.flat] == [False, False, True, True]
    assert [_labels_visible(ax, "y") for ax in axes.flat] == [True, False, True, False]
    assert all(ax.get_xlabel() == "" and ax.get_ylabel() == "" for ax in axes.flat)
    assert fig._supxlabel.get_text() == "Observation year"
    assert fig._supylabel.get_text() == "Study area"
    assert colorbar.ax.get_ylabel() == "Mean index"
    assert len(fig.axes) == 5
    plt.close(fig)


def test_panel_grid_rejects_mismatched_scales():
    fig, axes = _heatmap_grid(((0, 1), (0, 1), (0, 1), (0, 2)))
    with pytest.raises(ValueError, match="different colour scales"):
        finish_panel_grid(fig, axes, label="Mean index")
    plt.close(fig)


def test_shared_legend_and_gridlines():
    fig, axes = plt.subplots(1, 2)
    axes[0].plot([0, 1], label="A")
    axes[1].plot([0, 1], label="A")
    axes[1].plot([1, 0], label="B")
    for ax in axes:
        ax.legend()
        add_gridlines(ax)
    legend = add_shared_legend(fig, axes, title="Site")
    assert all(ax.get_legend() is None for ax in axes)
    assert [text.get_text() for text in legend.get_texts()] == ["A", "B"]
    assert any(line.get_visible() for line in axes[0].get_xgridlines())
    plt.close(fig)


def test_month_name_accepts_numbers_and_padded_strings():
    assert month_name(9) == month_name("09") == "September"


def test_site_order_puts_focus_first_then_alphabetical():
    sites = ["Zeta", "WadiGaza", "Alpha", "Alpha"]
    assert site_order(sites, "WadiGaza") == ["WadiGaza", "Alpha", "Zeta"]
    assert site_order(sites) == ["Alpha", "WadiGaza", "Zeta"]
    assert site_order(sites, "Missing") == ["Alpha", "WadiGaza", "Zeta"]


def test_anomaly_heatmap_rows_follow_site_order():
    from change_did.plotting import plot_anomaly_heatmap

    anomalies = pd.DataFrame({
        "site": ["Alpha", "WadiGaza"] * 2,
        "month": [1] * 4,
        "year_start": [2019, 2019, 2020, 2020],
        "year_end": [2020, 2020, 2021, 2021],
        "anomaly": [0.1, -0.2, 0.0, 0.05],
        "is_event_cell": [False, False, False, True],
    })
    fig, axes = plot_anomaly_heatmap(anomalies, sites=site_order(anomalies["site"], "WadiGaza"))
    assert [tick.get_text() for tick in axes.flat[0].get_yticklabels()] == ["Wadi Gaza", "Alpha"]
    plt.close(fig)


def test_cell_labels_contrast_with_background():
    assert contrast_text_color((0.0, 0.2, 0.1, 1.0)) == "white"
    assert contrast_text_color((0.95, 0.95, 0.8, 1.0)) == "black"
    fig, ax = plt.subplots()
    values = np.array([[0.0, 1.0]])
    image = ax.imshow(values, cmap="Greys", vmin=0, vmax=1)
    annotate_cells(ax, image, values, np.array([["low", "high"]]))
    colors = {text.get_text(): text.get_color() for text in ax.texts}
    assert colors == {"low": "black", "high": "white"}
    assert all(text.get_fontsize() > 7 for text in ax.texts)
    plt.close(fig)

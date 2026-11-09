import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from change_ci.plotting import (
    plot_change_heatmap,
    plot_change_small_multiples,
    plot_change_timeseries,
    plot_correlogram,
    plot_n_eff,
    plot_tau_sensitivity,
    save_figure,
)


def _frames():
    results = []
    for area, mean, range_px in (("AreaA", -0.1, 2), ("AreaB", 0.05, np.nan)):
        for tau in (0.02, 0.05, 0.10):
            no_range = area == "AreaB" and tau < 0.10
            results.append({
                "study_area": area, "month": 9, "year_start": 2023, "year_end": 2024,
                "tau": tau, "is_primary_tau": tau == 0.05, "mean_change": mean, "sd": 0.2,
                "range_px": np.nan if no_range else range_px,
                "range_map_units": np.nan if no_range else range_px * 10,
                "n_eff": np.nan if no_range else 50.0, "ci_low": np.nan if no_range else mean - 0.02,
                "ci_high": np.nan if no_range else mean + 0.02,
                "ci_excludes_zero": bool(not no_range and abs(mean) > 0.02),
                "flag_no_range": no_range, "flag_low_n_eff": False, "error": "",
            })
    correlograms = pd.DataFrame([
        {"study_area": area, "month": 9, "year_start": 2023, "year_end": 2024,
         "lag": lag, "moran_i": value, "pair_count": 100 - lag}
        for area, values in (("AreaA", [0.4, 0.01, -0.1]), ("AreaB", [0.3, 0.1, 0.01]))
        for lag, value in enumerate(values, 1)
    ])
    return pd.DataFrame(results), correlograms


def test_plot_functions_and_save_helper(tmp_path):
    results, correlograms = _frames()
    original = results.copy(deep=True)

    fig, ax = plot_change_timeseries(results, group_by="study_area", show_ci_for="all")
    assert len(ax.lines) >= 3
    plt.close(fig)

    fig, axes = plot_change_small_multiples(results, facet_by="study_area")
    assert axes.size == 2
    plt.close(fig)

    fig, ax = plot_change_heatmap(results, month="09")
    assert ax.images[0].get_array().shape == (2, 1)
    plt.close(fig)

    pair = {"study_area": "AreaA", "month": 9, "year_start": 2023, "year_end": 2024}
    fig, ax = plot_correlogram(correlograms, results, pair)
    assert len(ax.lines) >= 3
    horizontal_lines = {float(line.get_ydata()[0]) for line in ax.lines if len(line.get_ydata()) == 2 and line.get_ydata()[0] == line.get_ydata()[1]}
    assert horizontal_lines >= {0.02, 0.05, 0.10}
    plt.close(fig)

    fig, ax = plot_n_eff(results)
    assert ax.get_ylabel() == "Effective sample size"
    plt.close(fig)

    fig, ax = plot_tau_sensitivity(results)
    assert len(ax.get_legend().get_texts()) == 3
    saved = save_figure(fig, tmp_path / "plots" / "sensitivity.png")
    assert saved.exists()
    plt.close(fig)

    pd.testing.assert_frame_equal(results, original)


def test_small_multiples_highlight_study_area():
    results, _ = _frames()
    fig, axes = plot_change_small_multiples(
        results, facet_by="month", highlight="AreaB", ncols=2
    )
    line_colors = {line.get_label(): line.get_color() for line in axes.flat[0].lines}
    assert line_colors["AreaA"] == "0.62"
    assert line_colors["AreaB"] == "C3"
    highlighted_line = next(line for line in axes.flat[0].lines if line.get_label() == "AreaB")
    assert highlighted_line.get_marker() == "D"
    plt.close(fig)


def test_timeseries_rejects_missing_highlight():
    results, _ = _frames()
    with np.testing.assert_raises_regex(ValueError, "Highlighted series not present"):
        plot_change_timeseries(results, group_by="study_area", highlight="Missing")

def test_change_heatmap_labels_cells_and_marks_significance():
    results, _ = _frames()
    fig, axes = plt.subplots(1, 2, constrained_layout=True)
    plot_change_heatmap(results, "09", ax=axes[0], sites=["AreaB", "AreaA"], limit=0.2)
    ax = axes[0]
    assert [tick.get_text() for tick in ax.get_yticklabels()] == ["AreaB", "AreaA"]
    assert sorted(text.get_text() for text in ax.texts) == ["+0.050", "-0.100*"]
    assert ax.images[0].norm.vmin == -0.2 and ax.images[0].norm.vmax == 0.2
    plt.close(fig)


def test_small_multiples_use_one_shared_legend():
    results, _ = _frames()
    fig, axes = plot_change_small_multiples(results, facet_by="month", ncols=2)
    assert all(ax.get_legend() is None for ax in axes.flat)
    assert len(fig.legends) == 1
    assert any(line.get_visible() for line in axes.flat[0].get_ygridlines())
    plt.close(fig)

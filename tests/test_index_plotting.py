import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from index_ci.plotting import plot_index_heatmap, plot_index_timeseries


def _results():
    return pd.DataFrame([
        {
            "study_area": area,
            "index": "NDVI",
            "month": "09",
            "year": year,
            "tau": 0.05,
            "is_primary_tau": True,
            "mean_index": mean,
            "ci_low": mean - 0.04,
            "ci_high": mean + 0.04,
        }
        for area, values in (("WadiGaza", (0.3, 0.4)), ("Other", (0.2, 0.25)))
        for year, mean in zip((2023, 2024), values)
    ])


def test_index_timeseries_uses_observation_year_and_highlighted_ci():
    fig, ax = plot_index_timeseries(
        _results(), group_by="study_area",
        show_ci_for=("WadiGaza",), highlight="WadiGaza",
    )
    assert list(ax.get_xticks()) == [2023, 2024]
    assert ax.get_ylabel() == "Mean index value"
    assert len(ax.collections) == 1
    assert len(ax.lines) == 2
    plt.close(fig)


def test_index_timeseries_base_year_shows_percent_change():
    fig, ax = plot_index_timeseries(
        _results(), group_by="study_area", show_ci_for=("WadiGaza",),
        highlight="WadiGaza", base_year=2023,
    )
    by_label = {line.get_label(): line.get_ydata() for line in ax.lines}
    assert list(by_label["Wadi Gaza"]) == pytest.approx([0.0, 100 / 3])
    assert list(by_label["Other"]) == pytest.approx([0.0, 25.0])
    assert "2023" in ax.get_ylabel()
    plt.close(fig)


def test_index_timeseries_base_year_must_exist_for_every_series():
    with pytest.raises(ValueError, match="Base year 2019 missing"):
        plot_index_timeseries(_results(), group_by="study_area", base_year=2019)


def test_index_heatmap_has_year_columns_and_index_scale():
    fig, ax = plot_index_heatmap(_results(), "09")
    assert len(ax.images) == 1
    assert list(ax.get_xticks()) == [0, 1]
    assert ax.get_xlabel() == "Observation year"
    assert ax.images[0].get_cmap().name == "YlGn"
    plt.close(fig)


def test_index_heatmap_respects_caller_constrained_layout():
    fig, axes = plt.subplots(2, 2, constrained_layout=True)
    for ax in axes.flat:
        plot_index_heatmap(_results(), "09", ax=ax)
    assert all(len(ax.images) == 1 for ax in axes.flat)
    plt.close(fig)


def test_index_timeseries_points_sit_on_observation_years_with_grid():
    fig, ax = plot_index_timeseries(_results(), group_by="study_area")
    for line in ax.lines:
        assert list(line.get_xdata()) == [2023, 2024]
    assert any(line.get_visible() for line in ax.get_xgridlines())
    plt.close(fig)



def test_index_month_series_are_labeled_by_name():
    results = _results().assign(month=["01", "01", "09", "09"])
    fig, ax = plot_index_timeseries(results, group_by="month")
    assert [line.get_label() for line in ax.lines] == ["January", "September"]
    plt.close(fig)

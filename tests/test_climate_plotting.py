from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import box

from cds_pull.cells import cells_geodataframe
from cds_pull.config import ClimateConfig
from cds_pull.plotting import (
    plot_cell_values,
    plot_cells_map,
    plot_climatology,
    plot_cumulative_seasons,
    plot_summary_heatmap,
    plot_temperature_anomalies,
    plot_temperature_method_difference,
    plot_wet_season_heatmap,
    save_figure,
)
from cds_pull.summaries import build_monthly_summary, compute_normals

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ClimateConfig.from_yaml(ROOT / "configs" / "climate.yaml", project_root=ROOT)


def _daily() -> pd.DataFrame:
    dates = pd.date_range(*CONFIG.extraction_range, freq="D")
    rng = np.random.default_rng(1)
    month = dates.month.to_numpy()
    frames = []
    for cell in ("N31.5_E34.4", "N31.3_E34.2"):
        frames.append(pd.DataFrame({
            "cell_id": cell,
            "date": dates.date,
            "precip_mm": np.where(np.isin(month, [11, 12, 1, 2, 3]), rng.exponential(2, len(dates)), 0.0),
            "t2m_mean_24h_c": 20 + 6 * np.sin((month - 4) / 12 * 2 * np.pi),
            "t2m_midrange_c": 20.3 + 6 * np.sin((month - 4) / 12 * 2 * np.pi),
            "precip_hours": 24,
            "t2m_hours": 24,
        }))
    return pd.concat(frames, ignore_index=True)


def test_climate_plots_render_and_save(tmp_path):
    daily = _daily()
    normals = compute_normals(daily, CONFIG)
    site_cells = pd.DataFrame({"site": ["WadiGaza", "Other"], "cell_id": ["N31.5_E34.4", "N31.3_E34.2"]})
    summary = build_monthly_summary(daily, normals, site_cells, CONFIG)
    cells = cells_geodataframe(pd.DataFrame({
        "cell_id": ["N31.5_E34.4", "N31.9_E34.7"], "cell_lat": [31.5, 31.9], "cell_lon": [34.4, 34.7],
        "has_data": [True, False], "used": [True, False],
    }))
    sites = gpd.GeoDataFrame({"site_name": ["WadiGaza"]}, geometry=[box(34.38, 31.44, 34.42, 31.46)], crs=4326)

    figures = [
        plot_cells_map(sites, cells)[0],
        plot_summary_heatmap(summary, "precip_anom_mm", 5, flag="precip_near_zero_normal")[0],
        plot_summary_heatmap(summary, "cum_since_oct1_precip_pct_normal", 1)[0],
        plot_wet_season_heatmap(summary)[0],
        plot_temperature_anomalies(summary, "WadiGaza")[0],
        plot_climatology(normals, daily, "N31.5_E34.4", CONFIG.study_period_years)[0],
        plot_cumulative_seasons(daily, "N31.5_E34.4", range(2018, 2026), CONFIG.reference_years)[0],
        plot_temperature_method_difference(daily)[0],
        plot_cell_values(cells, pd.Series({"N31.5_E34.4": 317.0}), sites, label="mm")[0],
        plot_cell_values(cells, pd.Series({"N31.5_E34.4": 80.0}), centre=100, cmap="BrBG")[0],
    ]

    assert save_figure(figures[0], tmp_path / "plots" / "map.png").exists()
    for figure in figures:
        plt.close(figure)


def test_summary_heatmap_shared_limit_without_colorbar():
    daily = _daily()
    normals = compute_normals(daily, CONFIG)
    site_cells = pd.DataFrame({"site": ["WadiGaza", "Other"], "cell_id": ["N31.5_E34.4", "N31.3_E34.2"]})
    summary = build_monthly_summary(daily, normals, site_cells, CONFIG)
    fig, ax = plot_summary_heatmap(summary, "t2m_mean_24h_anom_c", 1, limit=2.5, colorbar=False)
    norm = ax.images[0].norm
    assert (norm.vmin, norm.vcenter, norm.vmax) == (-2.5, 0.0, 2.5)
    assert len(fig.axes) == 1
    plt.close(fig)

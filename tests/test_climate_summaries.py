from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cds_pull.config import ClimateConfig
from cds_pull.summaries import build_monthly_summary, compute_normals, percent_of_normal

ROOT = Path(__file__).resolve().parents[1]
WET_MONTHS = {11, 12, 1, 2, 3}


@pytest.fixture(scope="module")
def config() -> ClimateConfig:
    return ClimateConfig.from_yaml(ROOT / "configs" / "climate.yaml", project_root=ROOT)


def _daily(cell: str, config: ClimateConfig) -> pd.DataFrame:
    dates = pd.date_range(*config.extraction_range, freq="D")
    month = dates.month.to_numpy()
    return pd.DataFrame(
        {
            "cell_id": cell,
            "date": dates.date,
            "precip_mm": np.where(np.isin(month, list(WET_MONTHS)), 2.0, 0.0),
            "t2m_mean_24h_c": month.astype(float),
            "t2m_midrange_c": month + 0.5,
            "precip_hours": 24,
            "t2m_hours": 24,
        }
    )


def _blank_precip_day(daily: pd.DataFrame, day: date) -> pd.DataFrame:
    daily = daily.copy()
    mask = daily["date"] == day
    daily.loc[mask, "precip_mm"] = np.nan
    daily.loc[mask, "precip_hours"] = 23
    return daily


def _normal(normals, measure, month):
    rows = normals[normals["measure"] == measure]
    rows = rows[rows["month"].isna()] if month is None else rows[rows["month"] == month]
    return rows.iloc[0]


def test_normals_use_thirty_reference_periods(config):
    normals = compute_normals(_daily("C1", config), config)

    jan = _normal(normals, "precip_mm", 1)
    assert jan["mean"] == pytest.approx(62.0)
    assert jan["sd"] == pytest.approx(0.0)
    assert (jan["n_periods"], jan["period_first"], jan["period_last"]) == (30, 1991, 2020)
    assert not jan["incomplete_flag"]
    assert _normal(normals, "precip_mm", 5)["near_zero_flag"]
    assert _normal(normals, "t2m_midrange_c", 7)["mean"] == pytest.approx(7.5)
    wet = _normal(normals, "wet_season_precip_mm", None)
    assert (wet["period_first"], wet["period_last"], wet["n_periods"]) == (1991, 2020, 30)
    # Cumulative for January observations covers Oct-Dec of the prior year.
    assert _normal(normals, "cum_since_oct1_precip_mm", 1)["mean"] == pytest.approx(122.0)


def test_incomplete_reference_month_is_excluded_and_flagged(config):
    daily = _blank_precip_day(_daily("C1", config), date(1995, 1, 10))

    jan = _normal(compute_normals(daily, config), "precip_mm", 1)

    assert jan["n_periods"] == 29
    assert jan["incomplete_flag"]


def test_monthly_summary_rows_and_rules(config):
    daily = pd.concat([_daily(f"C{i}", config) for i in range(6)], ignore_index=True)
    daily = _blank_precip_day(daily, date(2020, 1, 15))
    normals = compute_normals(daily, config)
    site_cells = pd.DataFrame(
        {"site": [f"S{i}" for i in range(7)], "cell_id": [f"C{i}" for i in range(6)] + ["C5"]}
    )

    summary = build_monthly_summary(daily, normals, site_cells, config)

    assert len(summary) == 196
    assert summary.groupby("site")["cell_id"].nunique().eq(1).all()

    may = summary[summary["month"] == 5]
    assert may["precip_pct_normal"].isna().all()
    assert may["precip_near_zero_normal"].all()
    pd.testing.assert_series_equal(
        may["wet_season_precip_mm"], may["cum_since_oct1_precip_mm"], check_names=False
    )

    jan_2020 = summary[(summary["year"] == 2020) & (summary["month"] == 1)]
    assert jan_2020["precip_mm"].isna().all()
    assert (jan_2020["precip_missing_days"] == 1).all()
    assert jan_2020["month_incomplete"].all()
    assert jan_2020["t2m_mean_24h_anom_c"].eq(0).all()

    may_2020 = summary[(summary["year"] == 2020) & (summary["month"] == 5)]
    assert may_2020["wet_season_precip_mm"].isna().all()
    assert (may_2020["wet_season_missing_days"] == 1).all()
    assert (may_2020["wet_season_label"] == "2019/20").all()

    jan_2019 = summary[(summary["year"] == 2019) & (summary["month"] == 1)].iloc[0]
    assert jan_2019["precip_pct_normal"] == pytest.approx(100.0)
    assert jan_2019["wet_season_start"] == "2017-10-01"


def test_percent_of_normal_blank_below_threshold():
    assert percent_of_normal(5.0, 9.9, 10) != percent_of_normal(5.0, 9.9, 10)
    assert percent_of_normal(15.0, 10.0, 10) == pytest.approx(150.0)

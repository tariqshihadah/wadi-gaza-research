from datetime import date

import numpy as np
import pandas as pd
import pytest

from cds_pull.daily import daily_precip, daily_temperature, derive_daily


def _hourly(start: str, periods: int, precip_m=0.0, t2m_k=293.15) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.date_range(start, periods=periods, freq="h"),
            "precip_m": precip_m,
            "t2m_k": t2m_k,
        }
    )


def test_period_ending_hour_belongs_to_previous_day():
    hourly = _hourly("2020-01-01 00:00", 72)
    hourly.loc[hourly["time"] == pd.Timestamp("2020-01-02 00:00"), "precip_m"] = 0.005

    daily = daily_precip(hourly)

    assert daily.loc[date(2020, 1, 1), "precip_mm"] == pytest.approx(5.0)
    assert daily.loc[date(2020, 1, 2), "precip_mm"] == 0.0


def test_negative_hours_are_clamped_and_counted():
    hourly = _hourly("2020-01-01 01:00", 24, precip_m=0.001)
    hourly.loc[[3, 7], "precip_m"] = -1e-9

    daily = daily_precip(hourly)

    assert daily.loc[date(2020, 1, 1), "precip_mm"] == pytest.approx(22.0)
    assert daily.loc[date(2020, 1, 1), "precip_clamped"] == 2


def test_mean_and_midrange_differ_on_asymmetric_cycle():
    hourly = _hourly("2020-01-01 00:00", 24)
    hourly["t2m_k"] = 273.15 + np.array([10.0] * 20 + [30.0] * 4)

    daily = daily_temperature(hourly).loc[date(2020, 1, 1)]

    assert daily["t2m_mean_24h_c"] == pytest.approx((10 * 20 + 30 * 4) / 24)
    assert daily["t2m_midrange_c"] == pytest.approx(20.0)


def test_incomplete_and_absent_days_are_flagged_not_filled():
    hourly = _hourly("2020-01-01 01:00", 48, precip_m=0.001)
    hourly = hourly.drop(index=5).reset_index(drop=True)

    daily = derive_daily(hourly, date(2020, 1, 1), date(2020, 1, 3)).set_index("date")

    first = daily.loc[date(2020, 1, 1)]
    assert first["precip_hours"] == 23
    assert np.isnan(first["precip_mm"])
    assert not first["day_complete"]
    absent = daily.loc[date(2020, 1, 3)]
    assert absent["precip_hours"] == 0 and absent["t2m_hours"] == 1
    assert np.isnan(absent["precip_mm"]) and np.isnan(absent["t2m_mean_24h_c"])
    assert not absent["day_complete"]


def test_complete_day_has_both_variables():
    hourly = _hourly("2020-01-01 00:00", 49, precip_m=0.0005)

    daily = derive_daily(hourly, date(2020, 1, 1), date(2020, 1, 1)).iloc[0]

    assert daily["day_complete"]
    assert daily["precip_mm"] == pytest.approx(12.0)
    assert daily["t2m_mean_24h_c"] == pytest.approx(20.0)


def test_duplicate_times_are_rejected():
    hourly = pd.concat([_hourly("2020-01-01", 2), _hourly("2020-01-01", 1)])

    with pytest.raises(ValueError, match="duplicates"):
        daily_precip(hourly)

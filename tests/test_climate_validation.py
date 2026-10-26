from datetime import date

import numpy as np
import pandas as pd
import pytest

from cds_pull.daily import derive_daily
from cds_pull.validation import compare_daily, standard_daily, standard_request, validation_checks


def _paired_hourly(days: int = 3):
    """Return matching period-ending hourly and 00-UTC-accumulated hourly series."""
    times = pd.date_range("2020-01-01 00:00", periods=days * 24 + 1, freq="h")
    rng = np.random.default_rng(0)
    rate = rng.uniform(0, 0.001, len(times))
    rate[0] = 0.0
    temps = 285 + rng.normal(0, 2, len(times))
    series = pd.DataFrame({"time": times, "precip_m": rate, "t2m_k": temps})
    # Standard product: accumulated since 00 UTC, so 01:00 holds one hour and
    # 00:00 holds the previous 24 hours.
    period_day = (times - pd.Timedelta(hours=1)).date
    accum = pd.Series(rate).groupby(period_day).cumsum().to_numpy()
    standard = pd.DataFrame({"time": times, "tp_accum_m": accum, "t2m_k": temps})
    return series, standard


def test_standard_daily_matches_period_ending_derivation():
    series, standard = _paired_hourly()
    daily = derive_daily(series, date(2020, 1, 1), date(2020, 1, 3))
    daily.insert(0, "cell_id", "N31.5_E34.4")

    comparison = compare_daily(daily, standard_daily(standard), 2020, 1)

    assert comparison["precip_diff_mm"].abs().max() == pytest.approx(0, abs=1e-9)
    assert comparison["t2m_mean_24h_diff_c"].iloc[:2].abs().max() == pytest.approx(0, abs=1e-9)
    checks = validation_checks(comparison.iloc[:3], "N31.5_E34.4").set_index("check")
    assert checks.loc["validation_day_boundary", "passed"]
    assert checks.loc["validation_monthly_precip", "passed"]


def test_shifted_day_boundary_fails_validation():
    series, standard = _paired_hourly()
    shifted = series.assign(time=series["time"] + pd.Timedelta(hours=1))
    daily = derive_daily(shifted, date(2020, 1, 1), date(2020, 1, 2))
    daily.insert(0, "cell_id", "N31.5_E34.4")

    comparison = compare_daily(daily, standard_daily(standard), 2020, 1).iloc[:2]

    assert not validation_checks(comparison, "N31.5_E34.4").set_index("check").loc[
        "validation_day_boundary", "passed"
    ]


def test_standard_request_includes_following_month():
    request = standard_request(31.5, 34.4, 2020, 1)

    assert request["month"] == ["01", "02"]
    assert request["area"] == [31.5, 34.4, 31.5, 34.4]
    assert len(request["time"]) == 24
    with pytest.raises(ValueError):
        standard_request(31.5, 34.4, 2020, 12)

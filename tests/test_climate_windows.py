from datetime import date

import pytest

from cds_pull.windows import cumulative_window, season_label, wet_season_window


@pytest.mark.parametrize(
    ("month", "label", "wet", "cumulative"),
    [
        (1, "2017/18", (date(2017, 10, 1), date(2018, 4, 30)), (date(2018, 10, 1), date(2018, 12, 31))),
        (5, "2018/19", (date(2018, 10, 1), date(2019, 4, 30)), (date(2018, 10, 1), date(2019, 4, 30))),
        (9, "2018/19", (date(2018, 10, 1), date(2019, 4, 30)), (date(2018, 10, 1), date(2019, 8, 31))),
        (11, "2018/19", (date(2018, 10, 1), date(2019, 4, 30)), (date(2019, 10, 1), date(2019, 10, 31))),
    ],
)
def test_windows_match_brief_table_for_2019(month, label, wet, cumulative):
    wet_label, wet_window = wet_season_window(2019, month)
    cum_window = cumulative_window(2019, month)

    assert wet_label == label
    assert (wet_window.start, wet_window.end) == wet
    assert (cum_window.start, cum_window.end) == cumulative


def test_may_cumulative_equals_wet_season():
    assert cumulative_window(2020, 5) == wet_season_window(2020, 5)[1]


def test_season_label_uses_ending_year():
    assert season_label(2020) == "2019/20"
    assert season_label(2000) == "1999/00"


def test_cumulative_window_rejects_season_start_month():
    with pytest.raises(ValueError):
        cumulative_window(2020, 10)

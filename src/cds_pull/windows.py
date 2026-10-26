"""Accumulation windows for wet-season and cumulative precipitation.

Implements the window rules in the climate context brief. With the default
October-April wet season and an observation month in year Y:

=================  =====================  =========================
Observation month  Wet season used        Cumulative since October 1
=================  =====================  =========================
January            Oct Y-2 to Apr Y-1     Oct 1 to Dec 31, Y-1
May                Oct Y-1 to Apr Y       Oct 1, Y-1 to Apr 30, Y
September          Oct Y-1 to Apr Y       Oct 1, Y-1 to Aug 31, Y
November           Oct Y-1 to Apr Y       Oct 1 to Oct 31, Y
=================  =====================  =========================
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Window:
    """An inclusive range of UTC days."""

    start: date
    end: date

    @property
    def n_days(self) -> int:
        """Return the number of days in the window."""
        return (self.end - self.start).days + 1


def month_end(year: int, month: int) -> date:
    """Return the last day of a calendar month."""
    return date(year, month, calendar.monthrange(year, month)[1])


def season_label(end_year: int) -> str:
    """Label a cross-year season by its ending year, e.g. ``2019/20`` for 2020."""
    return f"{end_year - 1}/{end_year % 100:02d}"


def season_window(end_year: int, start_month: int = 10, end_month: int = 4) -> Window:
    """Return the wet season that ends in ``end_month`` of ``end_year``."""
    _check_season(start_month, end_month)
    return Window(date(end_year - 1, start_month, 1), month_end(end_year, end_month))


def wet_season_end_year(year: int, month: int, end_month: int = 4) -> int:
    """Return the ending year of the last wet season completed before a month."""
    return year if month > end_month else year - 1


def wet_season_window(
    year: int, month: int, start_month: int = 10, end_month: int = 4
) -> tuple[str, Window]:
    """Return the label and window of the last wet season completed before a month."""
    end_year = wet_season_end_year(year, month, end_month)
    return season_label(end_year), season_window(end_year, start_month, end_month)


def cumulative_window(year: int, month: int, start_month: int = 10) -> Window:
    """Return the window from the season start through the end of the prior month.

    Raises ``ValueError`` when ``month`` is the season start month, because the
    window would be empty.
    """
    if month == start_month:
        raise ValueError("Cumulative window is empty for the season start month")
    start_year = year if month > start_month else year - 1
    prior_year, prior_month = (year, month - 1) if month > 1 else (year - 1, 12)
    return Window(date(start_year, start_month, 1), month_end(prior_year, prior_month))


def _check_season(start_month: int, end_month: int) -> None:
    if start_month <= end_month:
        raise ValueError("Wet season must span the new year (start month > end month)")

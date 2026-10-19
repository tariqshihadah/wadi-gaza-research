"""Time windows: turn a set of years and months into request date ranges.

Composites in this study are built per calendar month, so the common need is to
expand a list of years and a list of months into ``(start, end)`` ranges that
:meth:`s2grab.client.S2Client.fetch` / :func:`s2grab.search.search` accept.
"""

from __future__ import annotations

import calendar
from typing import Sequence


def month_window(year: int, month: int) -> tuple[str, str]:
    """Return ``(start, end)`` date strings spanning a whole calendar month."""
    last = calendar.monthrange(year, month)[1]
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"


def month_windows(
    years: Sequence[int],
    months: Sequence[int],
) -> list[dict]:
    """Expand ``years`` × ``months`` into a list of monthly window records.

    Each record is a dict with ``label`` ("YYYY-MM"), ``year``, ``month``,
    ``start`` and ``end`` — pandas-friendly (``pd.DataFrame(...)``) and directly
    usable as ``start=``/``end=`` arguments. Iterates years then months, so the
    output order follows ``years`` first.
    """
    windows: list[dict] = []
    for year in years:
        for month in months:
            start, end = month_window(year, month)
            windows.append(
                {
                    "label": f"{year}-{month:02d}",
                    "year": year,
                    "month": month,
                    "start": start,
                    "end": end,
                }
            )
    return windows

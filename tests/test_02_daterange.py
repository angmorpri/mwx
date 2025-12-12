# 2025/12/12
"""
test_02_daterange.py - Tests for the utility functions
"""

from datetime import datetime

import pytest

from mwx.util import daterange


def test_daterange_empty():
    with pytest.raises(ValueError):
        daterange()


def test_daterange_invalid_args():
    with pytest.raises(ValueError):
        daterange(2024, 6, 15, 10)


# daterange(start, end) tests


def test_daterange_only_start():
    # As datetime
    dr = daterange(datetime(2025, 12, 15))
    assert dr.interval() == (
        datetime(2025, 12, 15),
        datetime(2025, 12, 16),
    )

    # As string
    dr = daterange("20241215")
    assert dr.interval() == (
        datetime(2024, 12, 15),
        datetime(2024, 12, 16),
    )

    dr = daterange("2024-06-30")
    assert dr.interval() == (
        datetime(2024, 6, 30),
        datetime(2024, 7, 1),
    )


def test_daterange_only_start_month():
    dr = daterange("202406")
    assert dr.interval() == (
        datetime(2024, 6, 1),
        datetime(2024, 7, 1),
    )

    dr = daterange("2024-12")
    assert dr.interval() == (
        datetime(2024, 12, 1),
        datetime(2025, 1, 1),
    )


def test_daterange_only_start_year():
    dr = daterange("2024")
    assert dr.interval() == (
        datetime(2024, 1, 1),
        datetime(2025, 1, 1),
    )


def test_daterange_onyl_start_bad_string():
    with pytest.raises(ValueError):
        daterange("2024/12/15")


def test_daterange_start_end():
    # As datetime
    dr = daterange(datetime(2025, 12, 15), datetime(2025, 12, 20))
    assert dr.interval() == (
        datetime(2025, 12, 15),
        datetime(2025, 12, 20),
    )

    # As string
    dr = daterange("20241215", "20241220")
    assert dr.interval() == (
        datetime(2024, 12, 15),
        datetime(2024, 12, 20),
    )

    dr = daterange(start="2024-06-30", end="2024-07-05")
    assert dr.interval() == (
        datetime(2024, 6, 30),
        datetime(2024, 7, 5),
    )


def test_daterange_start_end_month():
    dr = daterange("202406", "202408")
    assert dr.interval() == (
        datetime(2024, 6, 1),
        datetime(2024, 9, 1),
    )

    dr = daterange(start="2024-11", end="2025-02")
    assert dr.interval() == (
        datetime(2024, 11, 1),
        datetime(2025, 3, 1),
    )


def test_daterange_start_end_year():
    dr = daterange("2024", "2026")
    assert dr.interval() == (
        datetime(2024, 1, 1),
        datetime(2027, 1, 1),
    )


def test_daterange_start_end_ellipsis():
    dr = daterange(Ellipsis, "2024-06-15")
    assert dr.interval() == (
        datetime(daterange.YEAR_MIN, 1, 1),
        datetime(2024, 6, 15),
    )

    dr = daterange("2024-06-15", Ellipsis)
    assert dr.interval() == (
        datetime(2024, 6, 15),
        datetime(daterange.YEAR_MAX + 1, 1, 1),
    )


# daterange(year, month, day) tests


def test_daterange_year():
    dr = daterange(2024)
    assert dr.interval() == (
        datetime(2024, 1, 1),
        datetime(2025, 1, 1),
    )


def test_daterange_month():
    dr = daterange(2024, 6)
    assert dr.interval() == (
        datetime(2024, 6, 1),
        datetime(2024, 7, 1),
    )


def test_daterange_day():
    dr = daterange(2024, 6, 15)
    assert dr.interval() == (
        datetime(2024, 6, 15),
        datetime(2024, 6, 16),
    )


def test_daterange_year_month_day_with_ellipsis():
    dr = daterange(2024, ..., 15)
    assert dr.interval() == (
        datetime(2024, 1, 15),
        datetime(2024, 12, 16),
    )

    dr = daterange(None, 6, 15)
    assert dr.interval() == (
        datetime(daterange.YEAR_MIN, 6, 15),
        datetime(daterange.YEAR_MAX, 6, 16),
    )

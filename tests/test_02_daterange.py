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


# daterange(year, month, day)


def test_daterange_ymd():
    dr = daterange(2024, 6, 15)
    assert dr.start() == datetime(2024, 6, 15)
    assert dr.end() == datetime(2024, 6, 16)


def test_daterange_ym():
    dr = daterange(2024, 6)
    assert dr.start() == datetime(2024, 6, 1)
    assert dr.end() == datetime(2024, 7, 1)


def test_daterange_yd():
    dr = daterange(2024, ..., 15)
    assert dr.start() == datetime(2024, 1, 15)
    assert dr.end() == datetime(2024, 12, 16)


def test_daterange_y():
    dr = daterange(2024)
    assert dr.start() == datetime(2024, 1, 1)
    assert dr.end() == datetime(2025, 1, 1)


def test_daterange_md():
    dr = daterange(..., 6, 15)
    assert dr.start() == datetime(daterange.YEAR_MIN, 6, 15)
    assert dr.end() == datetime(daterange.YEAR_MAX, 6, 16)


def test_daterange_m():
    dr = daterange(..., 6)
    assert dr.start() == datetime(daterange.YEAR_MIN, 6, 1)
    assert dr.end() == datetime(daterange.YEAR_MAX, 7, 1)

    dr2 = daterange(..., 12)
    assert dr2.start() == datetime(daterange.YEAR_MIN, 12, 1)
    assert dr2.end() == datetime(daterange.YEAR_MAX + 1, 1, 1)


def test_daterange_d():
    dr = daterange(..., ..., 15)
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 15)
    assert dr.end() == datetime(daterange.YEAR_MAX, 12, 16)


def test_daterange_ymd_none():
    dr = daterange(..., ..., ...)
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 1)
    assert dr.end() == datetime(daterange.YEAR_MAX + 1, 1, 1)


# daterange(start, end)


def test_daterange_dt_to_dt():
    dr = daterange(datetime(2024, 6, 15), datetime(2024, 6, 20))
    assert dr.start() == datetime(2024, 6, 15)
    assert dr.end() == datetime(2024, 6, 20)

    # With full strings
    dr2 = daterange("2024-06-15", "20240620")
    assert dr2.start() == datetime(2024, 6, 15)
    assert dr2.end() == datetime(2024, 6, 20)


def test_daterange_dt_to_partialmonth():
    dr = daterange(datetime(2024, 6, 15), "2024-07")
    assert dr.start() == datetime(2024, 6, 15)
    assert dr.end() == datetime(2024, 7, 1)


def test_daterange_dt_to_partialyear():
    dr = daterange(datetime(2024, 6, 15), "2025")
    assert dr.start() == datetime(2024, 6, 15)
    assert dr.end() == datetime(2025, 1, 1)


def test_daterange_dt_to_ellipsis():
    dr = daterange(datetime(2024, 6, 15), ...)
    assert dr.start() == datetime(2024, 6, 15)
    assert dr.end() == datetime(daterange.YEAR_MAX, 1, 1)


def test_daterange_dt_to_none():
    dr = daterange(datetime(2024, 6, 15))
    assert dr.start() == datetime(2024, 6, 15)
    assert dr.end() == datetime(2024, 6, 16)


def test_daterange_partialmonth_to_dt():
    dr = daterange("2024-06", datetime(2024, 7, 15))
    assert dr.start() == datetime(2024, 6, 1)
    assert dr.end() == datetime(2024, 7, 15)


def test_daterange_partialmonth_to_partialmonth():
    dr = daterange("2024-06", "2024-09")
    assert dr.start() == datetime(2024, 6, 1)
    assert dr.end() == datetime(2024, 9, 1)


def test_daterange_partialmonth_to_partialyear():
    dr = daterange("2024-06", "2025")
    assert dr.start() == datetime(2024, 6, 1)
    assert dr.end() == datetime(2025, 1, 1)


def test_daterange_partialmonth_to_ellipsis():
    dr = daterange("2024-06", ...)
    assert dr.start() == datetime(2024, 6, 1)
    assert dr.end() == datetime(daterange.YEAR_MAX, 1, 1)


def test_daterange_partialmonth_to_none():
    dr = daterange("2024-06")
    assert dr.start() == datetime(2024, 6, 1)
    assert dr.end() == datetime(2024, 7, 1)


def test_daterange_partialyear_to_dt():
    dr = daterange("2024", datetime(2025, 3, 15))
    assert dr.start() == datetime(2024, 1, 1)
    assert dr.end() == datetime(2025, 3, 15)


def test_daterange_partialyear_to_partialmonth():
    dr = daterange("2024", "2025-03")
    assert dr.start() == datetime(2024, 1, 1)
    assert dr.end() == datetime(2025, 3, 1)


def test_daterange_partialyear_to_partialyear():
    dr = daterange("2024", "2025")
    assert dr.start() == datetime(2024, 1, 1)
    assert dr.end() == datetime(2025, 1, 1)


def test_daterange_partialyear_to_ellipsis():
    dr = daterange("2024", ...)
    assert dr.start() == datetime(2024, 1, 1)
    assert dr.end() == datetime(daterange.YEAR_MAX, 1, 1)


def test_daterange_partialyear_to_none():
    dr = daterange("2024")
    assert dr.start() == datetime(2024, 1, 1)
    assert dr.end() == datetime(2025, 1, 1)


def test_daterange_ellipsis_to_dt():
    dr = daterange(..., datetime(2024, 6, 15))
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 1)
    assert dr.end() == datetime(2024, 6, 15)


def test_daterange_ellipsis_to_partialmonth():
    dr = daterange(..., "2024-06")
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 1)
    assert dr.end() == datetime(2024, 6, 1)


def test_daterange_ellipsis_to_partialyear():
    dr = daterange(..., "2024")
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 1)
    assert dr.end() == datetime(2024, 1, 1)


def test_daterange_ellipsis_to_ellipsis():
    dr = daterange(..., ...)
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 1)
    assert dr.end() == datetime(daterange.YEAR_MAX, 1, 1)


def test_daterange_ellipsis_to_none():
    dr = daterange(...)
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 1)
    assert dr.end() == datetime(daterange.YEAR_MAX, 1, 1)


def test_daterange_none_to_dt():
    dr = daterange(None, datetime(2024, 6, 15))
    assert dr.start() == datetime(2024, 6, 14)
    assert dr.end() == datetime(2024, 6, 15)


def test_daterange_none_to_partialmonth():
    dr = daterange(None, "2024-06")
    assert dr.start() == datetime(2024, 5, 1)
    assert dr.end() == datetime(2024, 6, 1)


def test_daterange_none_to_partialyear():
    dr = daterange(None, "2024")
    assert dr.start() == datetime(2023, 1, 1)
    assert dr.end() == datetime(2024, 1, 1)


def test_daterange_none_to_ellipsis():
    dr = daterange(None, ...)
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 1)
    assert dr.end() == datetime(daterange.YEAR_MAX, 1, 1)


def test_daterange_none_to_none():
    dr = daterange(None, None)
    assert dr.start() == datetime(daterange.YEAR_MIN, 1, 1)
    assert dr.end() == datetime(daterange.YEAR_MAX, 1, 1)

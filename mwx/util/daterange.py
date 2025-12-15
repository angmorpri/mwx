# 2025/09/10
"""
util.py - Utility functions for the application.
"""
from __future__ import annotations

import calendar
from datetime import datetime
from types import EllipsisType
from typing import Any

from dateutil.relativedelta import relativedelta

from mwx.model import Entry

DateLikeObject = str | datetime | EllipsisType | None
_DATERANGE_INIT_KEYS = ("start", "end", "year", "month", "day")


class PartialDate:
    """Represents a partial date with unknown units."""

    def __init__(
        self, year: int | None = None, month: int | None = None, day: int | None = None
    ) -> None:
        self.year = year
        self.month = month
        self.day = day
        self._postops = []

    @classmethod
    def parse(self, raw: DateLikeObject) -> PartialDate:
        if isinstance(raw, datetime):
            return PartialDate(year=raw.year, month=raw.month, day=raw.day)
        elif isinstance(raw, str):
            raw = raw.strip().replace("-", "")
            if len(raw) == 8:
                dt = datetime.strptime(raw, "%Y%m%d")
                return PartialDate(year=dt.year, month=dt.month, day=dt.day)
            elif len(raw) == 6:
                dt = datetime.strptime(raw, "%Y%m")
                return PartialDate(year=dt.year, month=dt.month)
            elif len(raw) == 4:
                dt = datetime.strptime(raw, "%Y")
                return PartialDate(year=dt.year)
            else:
                raise ValueError(f"Invalid date string format: {raw}")
        elif raw is Ellipsis:
            return PartialDate()
        else:
            raise TypeError(f"Invalid date-like object: {raw}")

    def start(self) -> datetime:
        """Resolves unknown units to a starting datetime."""
        y = self.year if self.year is not None else daterange.YEAR_MIN
        m = self.month if self.month is not None else 1
        d = self.day if self.day is not None else 1
        return self._handle_postops(datetime(y, m, d))

    def end(self) -> datetime:
        """Resolves unknown units to an ending datetime."""
        y = self.year if self.year is not None else daterange.YEAR_MAX
        m = self.month if self.month is not None else 12
        d = self.day if self.day is not None else calendar.monthrange(y, m)[1]
        return self._handle_postops(datetime(y, m, d))

    def add(self, n: int) -> PartialDate:
        """Returns a new PartialDate with 'n' units added.

        Units are added to the first known unit, in the order day -> month ->
        year.

        """
        if self.day is not None:
            self._postops.append(relativedelta(days=+n))
        elif self.month is not None:
            self._postops.append(relativedelta(months=+n))
        elif self.year is not None:
            self._postops.append(relativedelta(years=+n))
        else:
            self._postops.append(relativedelta(days=+n))

    def sub(self, n: int) -> PartialDate:
        """Returns a new PartialDate with 'n' units subtracted.

        Units are subtracted from the first known unit, in the order day ->
        month -> year.

        """
        if self.day is not None:
            self._postops.append(relativedelta(days=-n))
        elif self.month is not None:
            self._postops.append(relativedelta(months=-n))
        elif self.year is not None:
            self._postops.append(relativedelta(years=-n))
        else:
            self._postops.append(relativedelta(days=+n))

    def _handle_postops(self, dt: datetime) -> datetime:
        for op in self._postops:
            dt += op
        return dt


class daterange:
    """Range between two datetimes.

    Provides methods to handle date ranges conveniently, from an inclusive
    start to an exclusive end.

    Main methods are:
    - interval(): returns a tuple (start, end) of datetime objects.
    - walk(step): yields datetime objects from start to end, stepping by
      the given delta `step`.

    Constructor can be one of:
    - daterange(start, end)
    - daterange(year, month, day)

    'start' and 'end' can be datetime objects or strings in 'YYYY-MM-DD' or
    'YYYYMMDD' format, where month and day are optional. If an Ellipsis (...)
    is provided, the period extends from datetime.min (for start) or to
    datetime.max (for end). If it is None, the period will extend through
    whichever value is missing (year, month or day). For example, if a full
    datetime is provided, it will extend through that date, if only the year is
    provided, it will extend through the whole year. Note that if None is
    provided for 'start', the period will start in the past, and if None is
    provided for 'end', the period will extend into the future.

    'year', 'month' and 'day' can be integers or Ellipsis (...). If an Ellipsis
    is provided, the period will extend through the whole range for that unit.
    None is not allowed, to avoid confusion with the other constructor.

    """

    YEAR_MIN = 1900
    YEAR_MAX = 2100

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Check number of arguments
        if len(args) > 3:
            raise ValueError("Invalid number of arguments for daterange constructor.")

        # Infer constructor type
        for i, arg in enumerate(args):
            if arg is None:
                key = "start" if i == 0 else "end"
                kwargs[key] = arg
            elif isinstance(arg, (datetime, str)):
                key = "start" if i == 0 else "end"
                kwargs[key] = arg
            elif isinstance(arg, int):
                key = ["year", "month", "day"][i]
                kwargs[key] = arg

        if not any(key in kwargs for key in _DATERANGE_INIT_KEYS):
            if len(args) == 1:
                kwargs["start"] = PartialDate.parse(args[0])
                kwargs["end"] = None
            elif len(args) == 2:
                kwargs["start"] = PartialDate.parse(args[0])
                kwargs["end"] = PartialDate.parse(args[1])
            elif len(args) == 3:
                kwargs["year"] = args[0]
                kwargs["month"] = args[1]
                kwargs["day"] = args[2]
            else:
                raise ValueError("Invalid arguments for daterange constructor.")

        if "start" in kwargs:
            start = kwargs.get("start", None)
            end = kwargs.get("end", None)
            if start in [None, Ellipsis] and end in [None, Ellipsis]:
                raise ValueError("At least one of 'start' or 'end' must be provided.")
            elif start is None:
                end = PartialDate.parse(end)
                self.dend = end.end()
                self.dstart = end.sub(1).end()
            elif end is None:
                start = PartialDate.parse(start)
                self.dstart = start.start()
                self.dend = start.add(1).start()

        elif any(key in kwargs for key in ("year", "month", "day")):
            year = kwargs.get("year", ...)
            month = kwargs.get("month", ...)
            day = kwargs.get("day", ...)

            if any(v is None for v in (year, month, day)):
                raise ValueError(
                    "'None' is not allowed for 'year', 'month' or 'day' arguments."
                )

            check = lambda x, y: y if x is Ellipsis else x  # noqa

            y0 = check(year, daterange.YEAR_MIN)
            m0 = check(month, 1)
            d0 = check(day, 1)

            y1 = check(year, daterange.YEAR_MAX)
            m1 = check(month, 12)
            d1 = check(day, calendar.monthrange(y1, m1)[1])

            self.dstart = datetime(y0, m0, d0)
            self.dend = datetime(y1, m1, d1) + relativedelta(days=+1)

    def interval(self) -> tuple[datetime, datetime]:
        """Returns the (start, end) datetime interval."""
        return (self.dstart, self.dend)

    def start(self) -> datetime:
        """Returns the start datetime."""
        return self.dstart

    def end(self) -> datetime:
        """Returns the end datetime."""
        return self.dend

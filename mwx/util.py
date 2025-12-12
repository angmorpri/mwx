# 2025/09/10
"""
util.py - Utility functions for the application.
"""

import calendar
from datetime import datetime
from itertools import product
from types import EllipsisType
from typing import Any, Callable, Iterable, TypeVar

import pandas as pd
from dateutil.relativedelta import relativedelta

from mwx.model import Entry

T = TypeVar("T")


def find(seq: Iterable[T], *args: Callable[[T], bool], **kwargs: Any) -> list[T]:
    """Finds items in a sequence `seq` that match given criteria.

    Criteria can be provided in two ways:
    - Positional arguments: must be functions that take an item and return
    either True or False. If multiple functions are provided, all must return
    True for an item to be included in the result.
    - Keyword arguments: must be attribute-value pairs. An item must have the
    specified attributes with the corresponding values to be included in the
    result. If the attribute does not exist on the item, it is considered a
    non-match.

    Returns a list of items that match all provided criteria.

    """
    conds = list(args)

    # Add conditions from keyword arguments
    for attr, value in kwargs.items():
        conds.append(lambda x, attr=attr, value=value: getattr(x, attr, None) == value)

    # Filter the sequence based on all conditions
    res = []
    for item in seq:
        try:
            if all(cond(item) for cond in conds):
                res.append(item)
        except Exception:
            continue
    return res


def find_first(seq: Iterable[T], *args: Callable[[T], bool], **kwargs: Any) -> T | None:
    """Finds the first item in a sequence `seq` that matches given criteria.

    Criteria can be provided in two ways:
    - Positional arguments: must be functions that take an item and return
    either True or False. If multiple functions are provided, all must return
    True for an item to be included in the result.
    - Keyword arguments: must be attribute-value pairs. An item must have the
    specified attributes with the corresponding values to be included in the
    result. If the attribute does not exist on the item, it is considered a
    non-match.

    Returns the first item that matches all provided criteria, or None if no
    such item exists.

    """
    conds = list(args)

    # Add conditions from keyword arguments
    for attr, value in kwargs.items():
        conds.append(lambda x, attr=attr, value=value: getattr(x, attr, None) == value)

    # Find and return the first matching item
    for item in seq:
        if all(cond(item) for cond in conds):
            return item
    return None


def to_frame(
    entries: list[Entry], *, duplicate_on_transfers: bool = True
) -> pd.DataFrame:
    """Converts a list of Entry objects to a pandas DataFrame.

    If `duplicate_on_transfers` is True, the DataFrame will have an 'account'
    and a 'counterpart' column, and will duplicate trasfer entries so that both
    'points of view' are represented.

    If `duplicate_on_transfers` is False, the DataFrame will have a 'source'
    and a 'target' column, and transfer entries will be represented only once.

    """
    if duplicate_on_transfers:
        incomes = find(entries, type=+1)
        expenses = find(entries, type=-1)
        transfers = find(entries, type=0)

        df_incomes = pd.DataFrame(
            {
                "date": [e.date for e in incomes],
                "account": [e.target.repr_name for e in incomes],
                "counterpart": [e.source.repr_name for e in incomes],
                "category": [e.category.repr_name for e in incomes],
                "amount": [e.amount for e in incomes],
                "item": [e.item for e in incomes],
            }
        )
        df_expenses = pd.DataFrame(
            {
                "date": [e.date for e in expenses],
                "account": [e.source.repr_name for e in expenses],
                "counterpart": [e.target.repr_name for e in expenses],
                "category": [e.category.repr_name for e in expenses],
                "amount": [e.amount for e in expenses],
                "item": [e.item for e in expenses],
            }
        )
        df_trans_out = pd.DataFrame(
            {
                "date": [e.date for e in transfers],
                "account": [e.source.repr_name for e in transfers],
                "counterpart": [e.target.repr_name for e in transfers],
                "category": [e.category.repr_name for e in transfers],
                "amount": [e.amount for e in transfers],
                "item": [e.item for e in transfers],
            }
        )
        df_trans_in = pd.DataFrame(
            {
                "date": [e.date for e in transfers],
                "account": [e.target.repr_name for e in transfers],
                "counterpart": [e.source.repr_name for e in transfers],
                "category": [e.category.repr_name for e in transfers],
                "amount": [e.amount for e in transfers],
                "item": [e.item for e in transfers],
            }
        )
        df = pd.concat(
            [df_incomes, df_expenses, df_trans_out, df_trans_in], ignore_index=True
        )
    else:
        df = pd.DataFrame(
            {
                "date": [e.date for e in entries],
                "source": [e.source.repr_name for e in entries],
                "target": [e.target.repr_name for e in entries],
                "category": [e.category.repr_name for e in entries],
                "item": [e.item for e in entries],
                "amount": [e.amount for e in entries],
            }
        )

    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(by="date").reset_index(drop=True)


def dict_product(d: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Generates the Cartesian product of a dictionary of lists.

    Given a dictionary where each key maps to a list of values, this function
    returns a list of dictionaries representing all possible combinations of
    the input values.

    Example:
        Input: {'a': [1, 2], 'b': ['x', 'y']}
        Output: [
            {'a': 1, 'b': 'x'},
            {'a': 1, 'b': 'y'},
            {'a': 2, 'b': 'x'},
            {'a': 2, 'b': 'y'}
        ]

    """
    keys = d.keys()
    values_product = product(*d.values())
    return [dict(zip(keys, values)) for values in values_product]


DateLikeObject = str | datetime | EllipsisType | None
_DATERANGE_INIT_KEYS = ("start", "end", "year", "month", "day")


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

    If providing a start and end, both must be date-like objects, that is:
    - A datetime.datetime object.
    - A string in 'YYYY-MM-DD' or 'YYYYMMDD' format, where month and day are
    optional.
    - An Ellipsis (...) or None, representing datetime.min or datetime.max.

    If providing year, month, day, they can be:
    - An integer.
    - An Ellipsis (...) or None, representing the whole range for that unit.

    """

    YEAR_MIN = 1900
    YEAR_MAX = 2100

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Infer constructor type
        for i, arg in enumerate(args):
            if isinstance(arg, (datetime, str)):
                key = "start" if i == 0 else "end"
                kwargs[key] = arg
            elif isinstance(arg, int):
                key = ["year", "month", "day"][i]
                kwargs[key] = arg

        if not any(key in kwargs for key in _DATERANGE_INIT_KEYS):
            if len(args) == 1:
                kwargs["start"] = args[0]
                kwargs["end"] = args[0] + relativedelta(days=+1)
            elif len(args) == 2:
                kwargs["start"] = args[0]
                kwargs["end"] = args[1]
            elif len(args) == 3:
                kwargs["year"] = args[0]
                kwargs["month"] = args[1]
                kwargs["day"] = args[2]
            else:
                raise ValueError("Invalid arguments for daterange constructor.")

        if "start" in kwargs:
            self.dstart = self.parse_date(kwargs["start"], pos=0)
            self.dend = self.parse_date(
                kwargs.get("end", self.dstart + relativedelta(days=+1)), pos=1
            )

        elif "year" in kwargs:
            year = kwargs.get("year", ...)
            month = kwargs.get("month", ...)
            day = kwargs.get("day", ...)

            check = lambda x, y: y if x is Ellipsis or x is None else x  # noqa

            y0 = check(year, daterange.YEAR_MIN)
            m0 = check(month, 1)
            d0 = check(day, 1)

            y1 = check(year, daterange.YEAR_MAX)
            m1 = check(month, 12)
            d1 = check(day, calendar.monthrange(y1, m1)[1])

            self.dstart = datetime(y0, m0, d0)
            self.dend = datetime(y1, m1, d1) + relativedelta(days=+1)

    def parse_date(self, raw: DateLikeObject, pos: int = 0) -> datetime:
        if isinstance(raw, datetime):
            return raw
        elif isinstance(raw, str):
            raw = raw.strip().replace("-", "")
            if len(raw) == 8:
                return datetime.strptime(raw, "%Y%m%d")
            elif len(raw) == 6:
                dt = datetime.strptime(raw, "%Y%m")
                return dt.replace(
                    day=1 if pos == 0 else calendar.monthrange(dt.year, dt.month)[1]
                )
            elif len(raw) == 4:
                dt = datetime.strptime(raw, "%Y")
                return dt.replace(
                    month=1 if pos == 0 else 12,
                    day=1 if pos == 0 else 31,
                )
            else:
                raise ValueError(f"Invalid date string format: {raw}")
        elif raw is Ellipsis or raw is None:
            return datetime.min if pos == 0 else datetime.max
        else:
            raise TypeError(f"Invalid date-like object: {raw}")

    def interval(self) -> tuple[datetime, datetime]:
        """Returns the (start, end) datetime interval."""
        return (self.dstart, self.dend)

# 2025/09/10
"""
util.py - Utility functions for the application.
"""

from datetime import datetime
from itertools import product
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


DateLikeObject = int | str | datetime | None


def parse_date_range(
    raw: DateLikeObject | tuple[DateLikeObject, DateLikeObject],
) -> tuple[datetime, datetime]:
    """Parses a date range from various input formats.

    Returns a tuple of datetime objects in range [min_date, max_date).

    If a tuple is provided, it is treated as (min_date, max_date). Allowed
    values are:
    - int: Converts to string.
    - str: Interpreted as 'YYYY', 'YYYYMM', 'YYYYMMDD', 'YYYY-MM' or 'YYYY-MM-DD'.
      When no day or month is provided, if min_date, it defaults to the
      earliest possible date; if max_date, it defaults to the latest possible
      date.
    - datetime: Returned as is
    - None: Returns either datetime.min or datetime.max.

    If a single value is provided, allowed values are:
    - int: Converts to string.
    - str: Interpreted as 'YYYY', 'YYYYMM', 'YYYYMMDD', 'YYYY-MM' or 'YYYY-MM-DD'.
      Range is set to the full period represented by the date.
    - datetime: Returned as (date, date + 1 day).
    - None: Returns (datetime.min, datetime.max).

    Raises ValueError for unsupported formats or invalid dates.

    """
    if isinstance(raw, tuple):
        raw_min, raw_max = raw

        # Min date
        if raw_min is None:
            min_date = datetime.min
        elif isinstance(raw_min, datetime):
            min_date = raw_min
        elif isinstance(raw_min, int):
            raw_min = str(raw_min)
        if isinstance(raw_min, str):
            raw_min = raw_min.replace("-", "")
            if len(raw_min) == 4:
                min_date = datetime(int(raw_min), 1, 1)
            elif len(raw_min) == 6:
                min_date = datetime(int(raw_min[:4]), int(raw_min[4:6]), 1)
            elif len(raw_min) == 8:
                min_date = datetime(
                    int(raw_min[:4]), int(raw_min[4:6]), int(raw_min[6:8])
                )
            else:
                raise ValueError(f"Invalid date format: '{raw_min}'")

        # Max date
        if raw_max is None:
            max_date = datetime.max
        elif isinstance(raw_max, datetime):
            max_date = raw_max
        elif isinstance(raw_max, int):
            raw_max = str(raw_max)
        if isinstance(raw_max, str):
            raw_max = raw_max.replace("-", "")
            if len(raw_max) == 4:
                max_date = datetime(int(raw_max), 1, 1)
            elif len(raw_max) == 6:
                max_date = datetime(int(raw_max[:4]), int(raw_max[4:6]), 1)
            elif len(raw_max) == 8:
                max_date = datetime.strptime(raw_max, "%Y%m%d")
            else:
                raise ValueError(f"Invalid date format: '{raw_max}'")

    else:
        raw_date = raw

        if raw_date is None:
            return (datetime.min, datetime.max)
        elif isinstance(raw_date, datetime):
            return (raw_date, raw_date + relativedelta(days=+1))
        elif isinstance(raw_date, int):
            raw_date = str(raw_date)
        if isinstance(raw_date, str):
            raw_date = raw_date.replace("-", "")
            if len(raw_date) == 4:
                year = int(raw_date)
                min_date = datetime(year, 1, 1)
                max_date = datetime(year + 1, 1, 1)
            elif len(raw_date) == 6:
                year = int(raw_date[:4])
                month = int(raw_date[4:6])
                min_date = datetime(year, month, 1)
                if month == 12:
                    max_date = datetime(year + 1, 1, 1)
                else:
                    max_date = datetime(year, month + 1, 1)
            elif len(raw_date) == 8:
                min_date = datetime.strptime(raw_date, "%Y%m%d")
                max_date = min_date + relativedelta(days=+1)
            else:
                raise ValueError(f"Invalid date format: '{raw_date}'")

    return (min_date, max_date)

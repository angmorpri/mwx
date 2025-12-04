# 2025/09/10
"""
util.py - Utility functions for the application.
"""

from typing import Any, Callable, Iterable, TypeVar

import pandas as pd

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
    return [item for item in seq if all(cond(item) for cond in conds)]


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

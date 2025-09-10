# 2025/09/10
"""
util.py - Utility functions for the application.
"""

from typing import Any, Callable, Iterable, TypeVar

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


def first(seq: Iterable[T], *args: Callable[[T], bool], **kwargs: Any) -> T | None:
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

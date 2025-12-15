# 2025/12/15 🎂
"""Utility functions for mwx package"""

from itertools import product
from typing import Any

from .daterange import daterange
from .find import find, find_first


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

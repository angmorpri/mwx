# 2025/11/25
"""Common stuff for ETL modules."""

from collections import namedtuple

MYWALLET_TABLES = [
    "tbl_account",
    "tbl_cat",
    "tbl_notes",
    "tbl_transfer",
    "tbl_trans",
]

MWXNamespace = namedtuple(
    "MWXNamespace",
    [
        "accounts",
        "counterparts",
        "categories",
        "entries",
    ],
)

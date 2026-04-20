# 2025/11/25
"""Common stuff for ETL modules."""

from __future__ import annotations

from collections import namedtuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mwx.wallet import Wallet


# Constants

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


# Capital computation (public: reused by future validate())


def compute_capital(wallet: Wallet) -> tuple[float, dict[str, float]]:
    """Compute total capital and per-account capital for a wallet.

    Uses the wallet's own sum() method, so the semantics are identical
    to what any consumer of the model would see: incomes add, expenses
    subtract, transfers cancel out at the global level.

    Returns
    -------
    (total, per_account):
        total: float, sum of all accounts' capital from the beginning
               of time to the end of time (i.e. the whole ledger),
               rounded to 2 decimals.
        per_account: dict mapping account repr_name → float capital,
                     rounded to 2 decimals.

    Note: returns native floats (not Money) because these values are
    destined for serialization boundaries (Excel, JSON, ...). Money is
    the domain type; float is the export boundary.

    """
    per_account: dict[str, float] = {}
    for acc in wallet.accounts:
        cap = wallet.sum(acc, (None, None))
        # wallet.sum() returns Money; unwrap to float at the export boundary
        per_account[acc.repr_name] = round(float(cap), 2)
    total = round(sum(per_account.values()), 2)
    return total, per_account

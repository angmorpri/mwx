# 2025/08/22
"""
playground.py - Non-pytest testing
"""


from pathlib import Path

from mwx import Wallet
from mwx.util import find

TESTING_DB_PATH = Path(__file__).parent / "tests" / "data" / "Sep_10_2025_ExpensoDB"


if __name__ == "__main__":
    wallet = Wallet(TESTING_DB_PATH)

    cats = set()
    for entry in find(
        wallet.entries,
        lambda e: e.source.repr_name == "@Ingresos",
    ):
        cats.add(entry.category.repr_name)

    print(sorted(cats), "\n")

    for entry in find(
        wallet.entries,
        lambda e: e.category.code == "T12",
        lambda e: e.source.repr_name == "@Ingresos",
    ):
        print(entry)

    wallet.write()

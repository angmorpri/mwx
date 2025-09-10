# 2025/08/22
"""
playground.py - Non-pytest testing
"""

from datetime import datetime
from pathlib import Path

from mwx import etl

TESTING_DB = Path(__file__).parent / "tests" / "Sep_10_2025_ExpensoDB"


if __name__ == "__main__":
    ns = etl.read(TESTING_DB)
    print(f"Accounts: {len(ns.accounts)}")
    for a in sorted(ns.accounts):
        print(f"  {a}")
    print("\n-----------\n")

    print(f"Categories: {len(ns.categories)}")
    for c in sorted(ns.categories):
        print(f"  {c}")
    print("\n-----------\n")

    print(f"Notes: {len(ns.notes)}")
    for n in sorted(ns.notes):
        print(f"  {n}")
    print("\n-----------\n")

    entries = [e for e in ns.entries if e.is_paid]
    print(f"Entries: {len(entries)}")
    for e in list(sorted(entries))[-20:]:
        print(f"  {e}")
    print("\n-----------\n")

# 2025/08/22
"""
playground.py - Non-pytest testing
"""

from datetime import datetime
from pathlib import Path

import mwx

TESTING_DB = Path(__file__).parent / "tests" / "Sep_10_2025_ExpensoDB"


if __name__ == "__main__":
    data = mwx.read(TESTING_DB)

    print(f"Accounts: {len(data.accounts)}")
    for a in sorted(data.accounts):
        print(f"  {a}")
    print("\n-----------\n")

    print(f"Categories: {len(data.categories)}")
    for c in sorted(data.categories):
        print(f"  {c}")
    print("\n-----------\n")

    print(f"Entries: {len(data.entries)}")
    for e in list(sorted(data.entries))[-20:]:
        print(f"  {e}")
    print("\n-----------\n")

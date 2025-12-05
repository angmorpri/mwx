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
    res = wallet.sum(account="@Personales", date="2025-08")
    print(res)

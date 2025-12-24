# 2025/08/22
"""
playground.py - Non-pytest testing
"""

from pathlib import Path

from mwx import Wallet
from mwx.etl import excel

TESTING_DB_PATH = Path(__file__).parent / "tests" / "data" / "Sep_10_2025_ExpensoDB"
OUTPUT_PATH = Path(__file__).parent / "tests" / "data" / "test_wallet_out.xlsx"

if __name__ == "__main__":
    # Load wallet from Excel
    wallet = Wallet(TESTING_DB_PATH)

    print(wallet.budget("@Básicos", "2100-01-01"))

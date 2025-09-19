# 2025/08/22
"""
playground.py - Non-pytest testing
"""


from pathlib import Path

import pandas as pd

import mwx
from mwx.frames import MonthlyFrame

TESTING_DB = Path(__file__).parent / "tests" / "Sep_10_2025_ExpensoDB"
REPORTS_OUTPUT_PATH = Path(__file__).parent / "tests" / "TestReport.csv"


if __name__ == "__main__":
    data = mwx.read(TESTING_DB)
    mf = MonthlyFrame(data)
    print(mf.xs("Personales", level="account").loc["2020-01-01":].tail(24))

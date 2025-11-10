# 2025/08/22
"""
playground.py - Non-pytest testing
"""


from pathlib import Path

from mwx import etl

TESTING_DB = Path(__file__).parent / "tests" / "Sep_10_2025_ExpensoDB"
REPORTS_OUTPUT_PATH = Path(__file__).parent / "tests" / "TestReport.csv"


if __name__ == "__main__":
    data = etl.read(TESTING_DB)
    print("ACCOUNTS")
    for account in data.accounts:
        print(account)
    input()
    print("CATEGORIES")
    for category in data.categories:
        print(category)
    input()
    print("ENTRIES")
    for entry in data.entries:
        print(entry)
    input()
    print("COUNTERPARTS")
    for counterpart in data.counterparts:
        print(counterpart)
    input()

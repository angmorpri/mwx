# 2025/08/22
"""
playground.py - Non-pytest testing
"""


from pathlib import Path

from mwx.etl import read, write
from mwx.util import find_first
from mwx.model import Account

TESTING_DB_PATH = Path(__file__).parent / "tests" / "data" / "Sep_10_2025_ExpensoDB"


if __name__ == "__main__":
    data = read(TESTING_DB_PATH)
    # Modify two accounts
    find_first(data.accounts, name="Básicos").order = 69
    find_first(data.accounts, name="Reserva").name = "MODIFIED"

    # Remove one account
    data.accounts.remove(find_first(data.accounts, name="Personales"))

    # Add one new account
    new_account = Account(mwid=-1, name="NEW")
    data.accounts.append(new_account)

    # Add one account with non-existing mwid
    invalid_account = Account(mwid=9999, name="InvalidAccount")
    data.accounts.append(invalid_account)

    # Write to a new database
    new_db_path = write(TESTING_DB_PATH, data)

# 2025/08/22
"""
test_12_write.py - Tests for writing MyWallet data.

All tests behave the same, for each entity/table:
- Change, in two different entities, some fields that will be updated.
- Remove one entity that exists in the database.
- Add one new entity with 'mwid' == -1.
- Add one entity with a non-existing 'mwid' that should be skipped and check
a warning is printed to the console.

"""

from pathlib import Path

import pytest

from mwx.etl import MWXNamespace, read, write
from mwx.model import Account, Category, Counterpart, Entry
from mwx.util import find_first

TESTING_DB_PATH = Path(__file__).parent / "data" / "Sep_10_2025_ExpensoDB"


@pytest.fixture
def mwx_data() -> MWXNamespace:
    """Reads the base data from the testing database."""
    return read(TESTING_DB_PATH)


def test_write_accounts(mwx_data: MWXNamespace) -> None:
    """Tests writing accounts."""
    data = mwx_data

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
    with pytest.warns(UserWarning):
        new_db_path = write(TESTING_DB_PATH, data)

    # Read back the data
    new_data = read(new_db_path)

    # Verify changes
    assert find_first(new_data.accounts, name="Básicos").order == 69
    assert find_first(new_data.accounts, name="MODIFIED") is not None
    assert find_first(new_data.accounts, name="Personales") is None
    assert find_first(new_data.accounts, name="NEW") is not None

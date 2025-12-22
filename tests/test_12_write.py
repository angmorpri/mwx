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

from datetime import datetime
from pathlib import Path

import pytest

from mwx.etl import MWXNamespace, read, write
from mwx.model import Account, Category, Counterpart, Entry
from mwx.util import Money, find_first

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
        new_db_path = write(
            TESTING_DB_PATH,
            data,
            new_db_name="ACCS_{}.sqlite",
            safe_delete=False,
            overwrite=True,
        )

    # Read back the data
    new_data = read(new_db_path)

    # Verify changes
    assert find_first(new_data.accounts, name="Básicos").order == 69
    assert find_first(new_data.accounts, name="MODIFIED") is not None
    assert find_first(new_data.accounts, name="Personales") is None
    assert find_first(new_data.accounts, name="NEW") is not None


def test_write_categories(mwx_data: MWXNamespace) -> None:
    """Tests writing standard categories."""
    data = mwx_data

    # Modify categories
    find_first(data.categories, name="Impuestos").code = "X11"
    find_first(data.categories, code="B10").name = "MODIFIED"
    find_first(data.categories, repr_name="B20. Supermercados").repr_name = (
        "X12. OTHER MODIFIED"
    )

    # Remove one category
    data.categories.remove(find_first(data.categories, name="Alcohol"))

    # Add one new category
    new_category = Category(mwid=-1, repr_name="X50. New Category", cat_type=1)
    data.categories.append(new_category)

    # Add one category with non-existing mwid
    invalid_category = Category(
        mwid=9999, repr_name="X20. Invalid Category", cat_type=1
    )
    data.categories.append(invalid_category)

    # Write to a new database
    with pytest.warns(UserWarning):
        new_db_path = write(
            TESTING_DB_PATH,
            data,
            new_db_name="CATS_{}.sqlite",
            safe_delete=False,
            overwrite=True,
        )

    # Read back the data
    new_data = read(new_db_path)

    # Verify changes
    assert find_first(new_data.categories, name="Impuestos").code == "X11"
    assert find_first(new_data.categories, code="B10").name == "MODIFIED"
    assert find_first(new_data.categories, repr_name="X12. OTHER MODIFIED") is not None
    assert find_first(new_data.categories, name="Alcohol") is None
    assert find_first(new_data.categories, repr_name="X50. New Category") is not None


def test_write_trans_categories(mwx_data: MWXNamespace) -> None:
    """Tests writing categories used in tranfers (notes)."""
    data = mwx_data

    # Modify categories
    find_first(data.categories, code="T11").name = "MODIFIED"
    find_first(data.categories, name="Reserva").code = "T99"

    # Remove one category
    data.categories.remove(find_first(data.categories, code="T13"))

    # Add one new category
    new_category = Category(mwid=-1, repr_name="T50. New Transfer Category", cat_type=0)
    data.categories.append(new_category)

    # Write to a new database
    new_db_path = write(
        TESTING_DB_PATH,
        data,
        new_db_name="TCAT_{}.sqlite",
        safe_delete=False,
        overwrite=True,
    )

    # Read back the data
    new_data = read(new_db_path)

    # Verify changes
    assert find_first(new_data.categories, code="T11").name == "MODIFIED"
    assert find_first(new_data.categories, name="Reserva").code == "T99"
    assert find_first(new_data.categories, code="T13") is None
    assert (
        find_first(new_data.categories, repr_name="T50. New Transfer Category")
        is not None
    )


def test_write_incomes_expenses(mwx_data: MWXNamespace) -> None:
    """Tests writing incomes and expenses."""
    data = mwx_data

    # Modify entries - generic
    find_first(data.entries, mwid=5332).amount = 1_000_000.123456789
    find_first(data.entries, mwid=5331).date = datetime(2001, 1, 1)
    find_first(data.entries, mwid=5330).item = "MODIFIED"
    find_first(data.entries, mwid=5329).details = "MODIFIED\nDETAILS"

    # Modify entries - with new categories, accounts
    new_acc = Account(mwid=-1, name="TestingAccount")
    data.accounts.append(new_acc)
    new_cat = Category(mwid=-1, repr_name="X99. TestingCategory", cat_type=-1)
    data.categories.append(new_cat)

    entry = find_first(data.entries, mwid=5328)
    entry.source = new_acc
    entry.target = Counterpart("TESTING COUNTERPART")
    entry.category = new_cat

    # Remove one entry
    data.entries.remove(find_first(data.entries, mwid=5327))

    # Add one new entry
    new_entry = Entry(
        mwid=-1,
        amount=69.69,
        date=datetime(2025, 12, 15),
        ent_type=+1,
        source=Counterpart("TESTING NEW SOURCE"),
        target=find_first(data.accounts, name="Inversión"),
        category=find_first(data.categories, code="A99"),
    )
    data.entries.append(new_entry)

    # Add one entry with non-existing mwid
    invalid_entry = Entry(
        mwid=9999,
        amount=100.0,
        date=datetime(2025, 1, 1),
        ent_type=-1,
        source=find_first(data.accounts, name="Básicos"),
        target=Counterpart("INVALID ENTRY TARGET"),
        category=find_first(data.categories, code="B10"),
    )
    data.entries.append(invalid_entry)

    # Write to a new database
    with pytest.warns(UserWarning):
        new_db_path = write(
            TESTING_DB_PATH,
            data,
            new_db_name="INEX_{}.sqlite",
            safe_delete=False,
            overwrite=True,
        )

    # Read back the data
    new_data = read(new_db_path)

    # Verify changes
    assert find_first(new_data.entries, mwid=5332).amount == Money(1_000_000.12)
    assert find_first(new_data.entries, mwid=5331).date == datetime(2001, 1, 1)
    assert find_first(new_data.entries, mwid=5330).item == "MODIFIED"
    assert find_first(new_data.entries, mwid=5329).details == "MODIFIED\nDETAILS"
    assert find_first(new_data.entries, mwid=5328).source.name == "TestingAccount"
    assert find_first(new_data.entries, mwid=5328).target.name == "TESTING COUNTERPART"
    assert find_first(new_data.entries, mwid=5328).category.code == "X99"
    assert find_first(new_data.entries, mwid=5327) is None
    entry = find_first(new_data.entries, mwid=5333)
    assert entry is not None
    assert entry.amount == Money(69.69)
    assert entry.item == "Sin concepto"
    assert entry.details == ""


def test_write_transfers(mwx_data: MWXNamespace) -> None:
    """Tests writing transfer entries."""
    data = mwx_data

    # Modify transfers - generic
    find_first(data.entries, type=0, mwid=1018).amount = Money(420.69)
    find_first(data.entries, type=0, mwid=1017).date = datetime(1996, 12, 15)
    find_first(data.entries, type=0, mwid=1016).item = "MODIFIED TRANSFER"
    find_first(data.entries, type=0, mwid=1015).details = "MODIFIED\nTRANSFER\nDETAILS"

    # Modify transfers - with new accounts and categories
    new_source = Account(mwid=-1, name="TransferSourceAccount")
    new_target = Account(mwid=-1, name="TransferTargetAccount")
    data.accounts.append(new_source)
    data.accounts.append(new_target)
    new_cat = Category(mwid=-1, repr_name="T99. Transfer Testing Category", cat_type=0)
    data.categories.append(new_cat)

    transfer = find_first(data.entries, type=0, mwid=1014)
    transfer.source = new_source
    transfer.target = new_target
    transfer.category = new_cat

    # Remove one transfer
    data.entries.remove(find_first(data.entries, type=0, mwid=1013))

    # Add one new transfer
    new_transfer = Entry(
        mwid=-1,
        amount=69.69,
        date=datetime(2025, 12, 15),
        ent_type=0,
        source=find_first(data.accounts, name="Básicos"),
        target=find_first(data.accounts, name="Inversión"),
        category=find_first(data.categories, code="T14"),
    )
    data.entries.append(new_transfer)

    # Add one transfer with non-existing mwid
    invalid_transfer = Entry(
        mwid=9999,
        amount=100.0,
        date=datetime(2025, 1, 1),
        ent_type=0,
        source=find_first(data.accounts, name="Básicos"),
        target=find_first(data.accounts, name="Inversión"),
        category=find_first(data.categories, code="T14"),
    )
    data.entries.append(invalid_transfer)

    # Write to a new database
    new_db_path = write(
        TESTING_DB_PATH,
        data,
        new_db_name="TRNS_{}.sqlite",
        safe_delete=False,
        overwrite=True,
    )

    # Read back the data
    new_data = read(new_db_path)

    # Verify changes
    assert find_first(new_data.entries, type=0, mwid=1018).amount == Money(420.69)
    assert find_first(new_data.entries, type=0, mwid=1017).date == datetime(
        1996, 12, 15
    )
    assert find_first(new_data.entries, type=0, mwid=1016).item == "MODIFIED TRANSFER"
    assert find_first(new_data.entries, type=0, mwid=1015).details == (
        "MODIFIED\nTRANSFER\nDETAILS"
    )
    assert (
        find_first(new_data.entries, type=0, mwid=1014).source.name
        == "TransferSourceAccount"
    )
    assert (
        find_first(new_data.entries, type=0, mwid=1014).target.name
        == "TransferTargetAccount"
    )
    assert (
        find_first(new_data.entries, type=0, mwid=1014).category.repr_name
        == "T99. Transfer Testing Category"
    )
    assert find_first(new_data.entries, type=0, mwid=1013) is None
    entry = find_first(new_data.entries, type=0, mwid=1019)
    assert entry is not None
    assert entry.item == "Sin concepto"
    assert entry.details == ""

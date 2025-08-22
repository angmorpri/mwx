# 2025/08/22
"""
test_11_datamodel.py - Tests for the data model layer
"""

from datetime import datetime

import pytest

from mwx.model import Account, Category, Counterpart, Entry


@pytest.fixture(autouse=True)
def clean_account_global_order():
    Account.HIGHEST_ORDER = 0


# Account


def test_account_bad_name():
    with pytest.raises(ValueError):
        Account(-1, "Mi Cuenta", 10)


def test_account_bad_color():
    with pytest.raises(ValueError):
        Account(-1, "MiCuenta", 10, color="green")


def test_account_min_args():
    acc = Account(-1, "MiCuenta")
    assert acc.mwid == -1
    assert acc.name == "MiCuenta"
    assert acc.order == 1
    assert acc.color == "#000000"


def test_account_multiple():
    """Create multiple accounts with and without specific order to
    check it is correctly handled.

    """
    acc1 = Account(-1, "MiCuenta1")
    acc2 = Account(-2, "MiCuenta2", 10)
    acc3 = Account(-3, "MiCuenta3")
    assert acc1.order == 1
    assert acc2.order == 10
    assert acc3.order == 11


def test_account_sorting():
    # Account - Account
    accs = [Account(-1, "B", 1), Account(-1, "A", 2)]
    accs.sort()
    assert accs[0].name == "B"
    assert accs[1].name == "A"

    # Account - Counterpart
    accs = [Counterpart("Payer"), Account(-1, "Z", 1000)]
    accs.sort()
    assert accs[0].name == "Z"
    assert accs[1].name == "Payer"


# Category


def test_category_transfer():
    """Create a transfer category and check the MWID appears negative"""
    cat = Category(10, "X99. Mi Categoria", 0)
    assert cat.mwid == -10
    assert cat.type == 0
    assert cat.color == "#000000"


def test_category_bad_name():
    with pytest.raises(ValueError):
        Category(10, "Mi Categoria", 0)


def test_category_bad_color():
    with pytest.raises(ValueError):
        Category(10, "X99. Mi Categoria", 0, color="invalid_color")


def test_category_modify_code():
    cat = Category(-1, "X99. Mi Categoria", 1)
    assert cat.code == "X99"

    cat.code = "Z00"
    assert cat.name == "Z00. Mi Categoria"

    with pytest.raises(ValueError):
        cat.code = "99X"


def test_category_modify_title():
    cat = Category(-1, "X99. Mi Categoria", 1)
    assert cat.title == "Mi Categoria"

    cat.title = "Alternativa"
    assert cat.name == "X99. Alternativa"


def test_category_modify_type():
    cat = Category(-1, "X99. Mi Categoria", 1)
    assert cat.type == 1

    with pytest.raises(AttributeError):
        cat.type = -1


def test_category_sorting():
    cats = [Category(-1, "X99. Mi Categoria", 1), Category(-2, "X98. Mi Categoria", 1)]
    cats.sort()
    assert cats[0].name == "X98. Mi Categoria"
    assert cats[1].name == "X99. Mi Categoria"


# Entry


def test_entry_transfer():
    """Create a transfer entry and check the MWID appears negative"""
    acc = Account(-1, "MiCuenta", 10)
    cat = Category(10, "X99. Mi Categoria", 0)
    entry = Entry(10, 100.00, datetime.today(), 0, acc, acc, cat, "Item")
    assert entry.mwid == -10
    assert entry.amount == 100.00
    assert entry.type == 0


def test_entry_bad_category():
    acc = Account(-1, "MiCuenta", 10)
    cat = Category(10, "X99. Mi Categoria", 1)
    with pytest.raises(ValueError, match="cannot have category of type"):
        Entry(10, 100.00, datetime.today(), 0, acc, acc, cat, "Item")


def test_entry_bad_source_target():
    """Checking <source>/<target>/<type>"""
    acc = Account(-1, "MiCuenta", 10)
    cpy = Counterpart("Payer")
    scp = "Payee"
    cats = [
        Category(-30, "Z50. Transfer", 0),
        Category(10, "X50. In", 1),
        Category(20, "Y50. Out", -1),
    ]

    # str / Account / +1 --> OK, source casted to Counterpart
    s, d, t = scp, acc, +1
    entry = Entry(10, 100.00, datetime.today(), t, s, d, cats[t], "Item")
    assert entry.type == +1
    assert isinstance(entry.source, Counterpart)

    # Account / Counterpart / -1 --> OK
    s, d, t = acc, cpy, -1
    entry = Entry(10, 100.00, datetime.today(), t, s, d, cats[t], "Item")
    assert entry.type == -1
    assert isinstance(entry.source, Account)

    # Account / Account / 0 --> OK
    s, d, t = acc, acc, 0
    entry = Entry(10, 100.00, datetime.today(), t, s, d, cats[t], "Item")
    assert entry.type == 0
    assert isinstance(entry.source, Account)

    # Counterpart / Counterpart / 0 --> ValueError
    s, d, t = cpy, cpy, 0
    with pytest.raises(ValueError, match="must have an Account"):
        Entry(10, 100.00, datetime.today(), t, s, d, cats[t], "Item")

    # Account / Counterpart / 0 --> ValueError
    s, d, t = acc, cpy, 0
    with pytest.raises(ValueError, match="must have an Account"):
        Entry(10, 100.00, datetime.today(), t, s, d, cats[t], "Item")

    # str / Account / 0 --> ValueError
    s, d, t = scp, acc, 0
    with pytest.raises(ValueError, match="must have an Account"):
        Entry(10, 100.00, datetime.today(), t, s, d, cats[t], "Item")


def test_entry_no_item():
    acc = Account(-1, "MiCuenta", 10)
    cat = Category(10, "X99. Mi Categoria", 0)
    entry = Entry(10, 100.00, datetime.today(), 0, acc, acc, cat)
    assert entry.item == cat.title


def test_entry_modify_type():
    acc = Account(-1, "MiCuenta", 10)
    cat = Category(10, "X99. Mi Categoria", 0)
    entry = Entry(10, 100.00, datetime.today(), 0, acc, acc, cat)
    assert entry.type == 0

    with pytest.raises(AttributeError):
        entry.type = -1


def test_entry_modify_source_target():
    """Test with account, counterpart and string"""
    # Baseline
    acc = Account(-1, "MiCuenta", 10)
    cpy = Counterpart("Payee")
    cat = Category(10, "X99. Mi Categoria", -1)
    entry = Entry(10, 100.00, datetime.today(), -1, acc, cpy, cat)
    assert entry.source == acc

    # With string
    # - Source --> ValueError, must be Account
    with pytest.raises(ValueError, match="must have an Account"):
        entry.source = "Someone"
    # - Target --> OK, with cast to Counterpart
    entry.target = "Someone"
    assert isinstance(entry.target, Counterpart)
    assert entry.target.name == "Someone"

    # With Counterpart
    new_counterpart = Counterpart("Someone Else")
    # - Source --> ValueError, must be Account
    with pytest.raises(ValueError, match="must have an Account"):
        entry.source = new_counterpart
    # - Target --> OK
    entry.target = new_counterpart
    assert entry.target.name == "Someone Else"

    # With Account
    new_account = Account(50, "OtraCuenta")
    # - Source --> OK
    entry.source = new_account
    assert entry.source.name == "OtraCuenta"
    # - Target --> ValueError, must be Counterpart
    with pytest.raises(ValueError, match="must have a Counterpart"):
        entry.target = new_account


def test_entry_id_and_sorting():
    """Create multiple entries for different days and check IDs"""
    # Baseline
    acc1 = Account(-1, "MiCuenta", 10)
    acc2 = Account(-2, "OtraCuenta", 20)
    tcat = Category(10, "X99. Mi Categoria", 0)
    ocat = Category(20, "Y99. Otra Categoria", -1)
    icat = Category(30, "Z99. Salida", +1)

    # Entries
    e1 = Entry(10, 100.00, datetime(2025, 1, 1), 0, acc1, acc1, tcat)
    e2 = Entry(11, 200.00, datetime(2025, 1, 2), 0, acc2, acc2, tcat)
    e3 = Entry(12, 300.00, datetime(2025, 1, 1), -1, acc1, "output", ocat)
    e4 = Entry(13, 400.00, datetime(2025, 1, 1), +1, "inpt", acc2, icat)
    e5 = Entry(14, 500.00, datetime(2025, 1, 2), 0, acc2, acc1, tcat)

    # Check
    assert e1.id == "202501010001"
    assert e2.id == "202501020001"
    assert e3.id == "202501010002"
    assert e4.id == "202501010003"
    assert e5.id == "202501020002"

    # Sorting
    entries = [e1, e2, e3, e4, e5]
    entries.sort()
    assert entries[0].id == "202501010001"
    assert entries[-1].id == "202501020002"

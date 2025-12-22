# 2025/08/22
"""
test_11_datamodel.py - Tests for the data model layer
"""

from datetime import datetime

import pytest

from mwx.model import Account, Category, Counterpart, Entry
from mwx.util import Money


@pytest.fixture(autouse=True)
def clean_account_global_order():
    Account._GLOBAL_ORDER = 100


# Account


def test_account_bad_attributes():
    # Name with whitespace
    with pytest.raises(ValueError):
        Account(-1, "Mi Cuenta", 10)

    # Order higher than 999
    with pytest.raises(ValueError):
        Account(-1, "MiCuenta", 1000)

    # Non-hex color
    with pytest.raises(ValueError):
        Account(-1, "MiCuenta", 10, color="green")


def test_account_defaults():
    acc = Account(-1, "MiCuenta")
    assert acc.mwid == -1
    assert acc.name == "MiCuenta"
    assert acc.order == 100
    assert acc.color == "#000000"


def test_account_multiple_order():
    """Create multiple accounts with and without specific order to
    check it is correctly handled.

    """
    acc1 = Account(-1, "MiCuenta1")
    acc2 = Account(-1, "MiCuenta2", 10)
    acc3 = Account(-1, "MiCuenta3")
    assert acc1.order == 100
    assert acc2.order == 10
    assert acc3.order == 101


def test_account_counterpart_sorting():
    # Account - Account
    accs = [Account(-1, "B", 1), Account(-1, "A", 2)]
    accs.sort()
    assert accs[0].name == "B"
    assert accs[1].name == "A"

    # Account - Counterpart
    accs = [Counterpart("Payer"), Account(-1, "Z", 888)]
    accs.sort()
    assert accs[0].name == "Z"
    assert accs[1].name == "Payer"


def test_account_to_dict():
    acc = Account(-1, "MiCuenta", 10, color="#123456")
    d = acc.to_dict()
    assert d == {
        "mwid": -1,
        "name": "MiCuenta",
        "order": 10,
        "color": "#123456",
        "is_visible": True,
        "is_legacy": False,
    }


def test_account_str():
    acc = Account(123, "MiCuenta", 10, is_legacy=True)
    assert str(acc) == "[00123] @MiCuenta (10, #000000) [LEGACY]"


# Counterpart


def test_counterpart_ok():
    cpy = Counterpart("Mi Contraparte")
    assert cpy.mwid == 0
    assert cpy.name == "Mi Contraparte"


def test_counterpart_str():
    cpy = Counterpart("Mi Contraparte")
    assert str(cpy) == "[00000] Mi Contraparte"


# Category


def test_category_bad_attributes():
    # Name without format
    with pytest.raises(ValueError):
        Category(-1, "Mi Categoria", 0)

    # Only wrong code format
    with pytest.raises(ValueError):
        Category(-1, "99X. Mi Categoria", 0)

    # Type not in [-1, 0, 1]
    with pytest.raises(ValueError):
        Category(-1, "X99. Mi Categoria", 2)

    # Icon ID out of range
    with pytest.raises(ValueError):
        Category(-1, "X99. Mi Categoria", 0, icon_id=1000)

    # Invalid color
    with pytest.raises(ValueError):
        Category(-1, "X99. Mi Categoria", 0, color="invalid_color")


def test_category_modify_code_and_name():
    cat = Category(-1, "X99. Mi Categoria", 1)
    assert cat.code == "X99"
    assert cat.name == "Mi Categoria"
    assert cat.repr_name == "X99. Mi Categoria"

    cat.code = "Z00"
    assert cat.repr_name == "Z00. Mi Categoria"

    cat.name = "Alternativa"
    assert cat.repr_name == "Z00. Alternativa"

    cat.repr_name = "Y50. Nueva Categoria"
    assert cat.code == "Y50"
    assert cat.name == "Nueva Categoria"

    with pytest.raises(ValueError):
        cat.repr_name = "BadFormatName"


def test_category_modify_type():
    """Type must be immutable after creation"""
    cat = Category(-1, "X99. Mi Categoria", 1)
    assert cat.type == 1

    with pytest.raises(AttributeError):
        cat.type = -1


def test_category_sorting():
    cats = [Category(-1, "X99. Alfa", 1), Category(1, "X98. Beta", 1)]
    cats.sort()
    assert cats[0].repr_name == "X98. Beta"
    assert cats[1].repr_name == "X99. Alfa"


def test_category_to_dict():
    cat = Category(-1, "X99. Mi Categoria", -1, icon_id=10, color="#654321")
    d = cat.to_dict()
    assert d == {
        "mwid": -1,
        "code": "X99",
        "name": "Mi Categoria",
        "type": -1,
        "icon_id": 10,
        "color": "#654321",
        "is_legacy": False,
    }


def test_category_str():
    cat = Category(
        123, "X99. Mi Categoria", -1, icon_id=10, color="#654321", is_legacy=True
    )
    assert str(cat) == "[00123] X99. Mi Categoria (-1, 10, #654321) [LEGACY]"


# Entry


def test_entry_ok():
    src = Account(10, "MiCuenta", 10)
    dst = Counterpart("Payee")
    cat = Category(30, "X99. Mi Categoria", -1)

    entry = Entry(-1, -1234.567891011, datetime.today(), -1, src, dst, cat)
    assert entry.amount == Money(1234.57)
    assert entry.source.mwid == 10
    assert entry.target.mwid == 0
    assert entry.category.mwid == 30
    assert entry.item == "Sin concepto"
    assert entry.details == ""


def test_entry_bad_source_target():
    """Checking <source>/<target>/<type>"""
    acc1 = Account(-1, "MiCuenta", 10)
    acc2 = Account(-1, "OtraCuenta", 20)
    cpy = Counterpart("Payer")
    cats = [
        Category(30, "Z50. Transfer", 0),
        Category(10, "X50. In", 1),
        Category(20, "Y50. Out", -1),
    ]

    # Category type 0, source and target must be Account
    with pytest.raises(ValueError):
        Entry(-1, 100.00, datetime.today(), 0, acc1, cpy, cats[0])
    with pytest.raises(ValueError):
        Entry(-1, 100.00, datetime.today(), 0, cpy, acc2, cats[0])
    entry = Entry(-1, 100.00, datetime.today(), 0, acc1, acc2, cats[0])
    assert entry.source.name == "MiCuenta"
    assert entry.target.name == "OtraCuenta"

    # Category type +1, source must be Counterpart, target Account
    with pytest.raises(ValueError):
        Entry(-1, 100.00, datetime.today(), +1, acc1, acc2, cats[1])
    with pytest.raises(ValueError):
        Entry(-1, 100.00, datetime.today(), +1, acc1, cpy, cats[1])
    entry = Entry(-1, 100.00, datetime.today(), +1, cpy, acc2, cats[1])
    assert entry.source.name == "Payer"
    assert entry.target.name == "OtraCuenta"

    # Category type -1, source must be Account, target Counterpart
    with pytest.raises(ValueError):
        Entry(-1, 100.00, datetime.today(), -1, acc1, acc2, cats[2])
    with pytest.raises(ValueError):
        Entry(-1, 100.00, datetime.today(), -1, cpy, acc2, cats[2])
    entry = Entry(-1, 100.00, datetime.today(), -1, acc1, cpy, cats[2])
    assert entry.source.name == "MiCuenta"
    assert entry.target.name == "Payer"

    # Accounts cannot be equal
    with pytest.raises(ValueError):
        Entry(-1, 100.00, datetime.today(), 0, acc1, acc1, cats[0])


def test_entry_modify_type():
    src = Account(-1, "MiCuenta", 10)
    dst = Account(-1, "OtraCuenta", 20)
    cat = Category(10, "X99. Mi Categoria", 0)
    entry = Entry(10, 100.00, datetime.today(), 0, src, dst, cat)
    assert entry.type == 0
    with pytest.raises(AttributeError):
        entry.type = -1


def test_entry_modify_source_target_category():
    """Test with account, counterpart and string"""
    acc1 = Account(-1, "MiCuenta", 10)
    acc2 = Account(-1, "OtraCuenta", 20)
    cpy = Counterpart("Payer")
    cats = [
        Category(30, "Z50. Transfer", 0),
        Category(10, "X50. In", 1),
        Category(20, "Y50. Out", -1),
    ]

    # Transfer entry
    entry = Entry(-1, 100.00, datetime.today(), 0, acc1, acc2, cats[0])
    # Source cannot be changed to Counterpart
    with pytest.raises(ValueError):
        entry.source = cpy
    # Target cannot be changed to Counterpart
    with pytest.raises(ValueError):
        entry.target = cpy
    # Category type mismatch
    with pytest.raises(ValueError):
        entry.category = cats[1]
    # Valid changes
    entry.category = Category(99, "X99. New Cat", 0)
    assert entry.category.mwid == 99

    # Income entry
    entry = Entry(-1, 100.00, datetime.today(), +1, cpy, acc2, cats[1])
    # Source cannot be changed to Account
    with pytest.raises(ValueError):
        entry.source = acc1
    # Target cannot be changed to Counterpart
    with pytest.raises(ValueError):
        entry.target = cpy
    # Category type mismatch
    with pytest.raises(ValueError):
        entry.category = cats[2]
    # Valid changes
    entry.source = Counterpart("New Payer")
    assert entry.source.name == "New Payer"

    # Expense entry
    entry = Entry(-1, 100.00, datetime.today(), -1, acc1, cpy, cats[2])
    # Source cannot be changed to Counterpart
    with pytest.raises(ValueError):
        entry.source = cpy
    # Target cannot be changed to Account
    with pytest.raises(ValueError):
        entry.target = acc2
    # Category type mismatch
    with pytest.raises(ValueError):
        entry.category = cats[0]
    # Valid changes
    entry.source = Account(99, "NewAccount", 50)
    assert entry.source.mwid == 99


def test_entry_has_account():
    acc1 = Account(-1, "MiCuenta", 10)
    acc2 = Account(-1, "OtraCuenta", 20)
    cpy = Counterpart("Payer")
    cat = Category(10, "X99. Mi Categoria", 0)

    entry1 = Entry(-1, 100.00, datetime.today(), 0, acc1, acc2, cat)
    entry2 = Entry(
        -1, 100.00, datetime.today(), +1, cpy, acc2, Category(11, "X98. In", 1)
    )
    entry3 = Entry(
        -1, 100.00, datetime.today(), -1, acc1, cpy, Category(12, "Y98. Out", -1)
    )

    assert entry1.has_account(acc1) is True
    assert entry1.has_account(acc2) is True
    assert entry1.has_account(Account(-1, "OtraCuenta", 30)) is False

    assert entry2.has_account(acc2) is True
    assert entry2.has_account(acc1) is False

    assert entry3.has_account(acc1) is True
    assert entry3.has_account(acc2) is False


def test_entry_flow():
    acc1 = Account(-1, "MiCuenta", 10)
    acc2 = Account(-1, "OtraCuenta", 20)
    cpy = Counterpart("Payer")
    cat = Category(10, "X99. Mi Categoria", 0)

    entry1 = Entry(-1, 100.00, datetime.today(), 0, acc1, acc2, cat)
    entry2 = Entry(
        -1, 100.00, datetime.today(), +1, cpy, acc2, Category(11, "X98. In", 1)
    )
    entry3 = Entry(
        -1, 100.00, datetime.today(), -1, acc1, cpy, Category(12, "Y98. Out", -1)
    )

    assert entry1.flow(acc1) == -1
    assert entry1.flow(acc2) == +1

    assert entry2.flow(acc2) == +1
    assert entry2.flow(acc1) == 0

    assert entry3.flow(acc1) == -1
    assert entry3.flow(acc2) == 0


def test_entry_sorting():
    """Create multiple entries for different days and check IDs"""
    # Baseline
    acc1 = Account(-1, "MiCuenta", 10)
    acc2 = Account(-1, "OtraCuenta", 20)
    cpy = Counterpart("Payer")
    tcat = Category(10, "X99. Mi Categoria", 0)
    ocat = Category(20, "Y99. Otra Categoria", -1)
    icat = Category(30, "Z99. Salida", +1)

    # Entries
    e1 = Entry(10, 100.00, datetime(2025, 1, 1), 0, acc1, acc2, tcat)
    e2 = Entry(11, 200.00, datetime(2025, 1, 2), 0, acc2, acc1, tcat)
    e3 = Entry(12, 300.00, datetime(2025, 1, 1), -1, acc1, cpy, ocat)
    e4 = Entry(13, 400.00, datetime(2025, 1, 1), +1, cpy, acc2, icat)
    e5 = Entry(14, 500.00, datetime(2025, 1, 2), 0, acc2, acc1, tcat)

    # Sorting
    entries = [e1, e2, e3, e4, e5]
    entries.sort()
    assert entries[0].date.day == 1
    assert entries[-1].date.day == 2


def test_entry_to_dict():
    src = Account(10, "MiCuenta", 10)
    dst = Counterpart("Payee")
    cat = Category(30, "X99. Mi Categoria", -1)

    entry = Entry(
        -1,
        -1234.567891011,
        datetime(2025, 8, 22),
        -1,
        src,
        dst,
        cat,
        item="Test Item",
        details="Some details",
    )
    d = entry.to_dict()
    assert d == {
        "mwid": -1,
        "amount": 1234.57,
        "date": "2025-08-22T00:00:00",
        "type": -1,
        "source": {
            "mwid": 10,
            "name": "MiCuenta",
            "order": 10,
            "color": "#000000",
            "is_visible": True,
            "is_legacy": False,
        },
        "target": {
            "mwid": 0,
            "name": "Payee",
        },
        "category": {
            "mwid": 30,
            "code": "X99",
            "name": "Mi Categoria",
            "type": -1,
            "icon_id": 0,
            "color": "#000000",
            "is_legacy": False,
        },
        "item": "Test Item",
        "details": "Some details",
        "is_bill": False,
    }


def test_entry_str():
    src = Account(10, "MiCuenta", 10)
    dst = Counterpart("Payee")
    cat = Category(30, "X99. Mi Categoria", -1)

    entry = Entry(
        123,
        -1234.56,
        datetime(2025, 8, 22),
        -1,
        src,
        dst,
        cat,
        item="Test Item",
        details="Some details",
    )
    assert (
        str(entry)
        == "[00123] 2025-08-22: +    1.234,56 € <X99> (@MiCuenta -> Payee), 'Test Item'"
    )

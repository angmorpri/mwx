# 2025/12/05
"""
test_13_wallet_find.py - Tests for 'find' method of Wallet class.

"""

from datetime import datetime
from pathlib import Path

import pytest

from mwx import Wallet
from mwx.model import Account, Category, Entry
from mwx.util import find

TESTING_DB_PATH = Path(__file__).parent / "data" / "Sep_10_2025_ExpensoDB"


@pytest.fixture
def wallet() -> Wallet:
    return Wallet(TESTING_DB_PATH)


# Basic tests


def test_get_basic_param(wallet):
    res = wallet.find(name="Personales")
    assert len(res) == 1
    assert isinstance(res[0], Account)
    assert res[0].repr_name == "@Personales"


def test_get_basic_param_not_found(wallet):
    res = wallet.find(false_param="nope")
    assert len(res) == 0


def test_get_basic_func(wallet):
    res = wallet.find(lambda x: x.code == "T11")
    assert len(res) == 1
    assert isinstance(res[0], Category)


def test_get_basic_func_not_found(wallet):
    res = wallet.find(lambda x: x.false_attr == "NOPE")
    assert len(res) == 0


def test_get_basic_param_and_func(wallet):
    res = wallet.find(
        lambda x: x.date >= datetime(2024, 1, 1),
        item="Compra semanal",
    )
    assert len(res) > 2
    assert all(isinstance(e, Entry) for e in res)


# Complex tests


def test_get_entities(wallet):
    res = wallet.find(entity="account", name="Impuestos")
    assert len(res) == 0

    res = wallet.find(entity="category", name="Impuestos")
    assert len(res) == 1
    assert isinstance(res[0], Category)

    res = wallet.find(entity="income", item="Compra semanal")
    assert len(res) == 0

    res = wallet.find(entity="expense", item="Compra semanal")
    assert len(res) > 2

    res = wallet.find(entity="entry", item="Compra semanal")
    assert len(res) > 2


def test_get_amount_range(wallet):
    res = wallet.find(amount=(None, None))
    assert len(res) == len(wallet.entries)

    res = wallet.find(amount=(500_000, None))
    assert len(res) == 0

    res = wallet.find(amount=(1000, 3000))
    assert len(res) > 0
    assert all(1000 <= e.amount < 3000 for e in res)

    res = wallet.find(amount=(None, 1.0))
    assert all(e.amount < 1.0 for e in res)


def test_get_date(wallet):
    res = wallet.find(date="2024")
    cmp = find(wallet.entries, lambda e: e.date.year == 2024)
    assert len(res) == len(cmp)

    res = wallet.find(date="202410")
    cmp = find(
        wallet.entries,
        lambda e: e.date.year == 2024 and e.date.month == 10,
    )
    assert len(res) == len(cmp)

    res = wallet.find(date="20241015")
    cmp = find(
        wallet.entries,
        lambda e: e.date.year == 2024 and e.date.month == 10 and e.date.day == 15,
    )
    assert len(res) == len(cmp)

    res = wallet.find(date="2024-10-15")
    assert len(res) == len(cmp)

    res = wallet.find(date=datetime(2024, 10, 15))
    assert len(res) == len(cmp)


def test_get_date_range(wallet):
    res = wallet.find(date=(None, None))
    assert len(res) == len(wallet.entries)

    res = wallet.find(date=(None, "20240101"))
    cmp = find(wallet.entries, lambda e: e.date == datetime(2023, 12, 31))
    assert len(res) == len(cmp)

    res = wallet.find(date=("2022", None))
    cmp = find(
        wallet.entries, lambda e: datetime(2022, 1, 1) <= e.date < datetime(2023, 1, 1)
    )
    assert len(res) == len(cmp)

    res = wallet.find(date=("20240101", "20240630"))
    cmp = find(
        wallet.entries, lambda e: datetime(2024, 1, 1) <= e.date < datetime(2024, 6, 30)
    )
    assert len(res) == len(cmp)


def test_get_year_month_day(wallet):
    res = wallet.find(year=2022)
    cmp = wallet.find(date="2022")
    assert len(res) == len(cmp)

    res = wallet.find(year=2024, month=10)
    cmp = wallet.find(date="202410")
    assert len(res) == len(cmp)

    res = wallet.find(year=2024, month=10, day=15)
    cmp = wallet.find(date="2024-10-15")
    assert len(res) == len(cmp)


def test_get_source(wallet):
    # By MWID
    res = wallet.find(source=8)
    assert len(res) > 0
    assert all(e.source.repr_name == "@Personales" for e in res)

    # By repr_name for Account
    res = wallet.find(source="@Personales")
    assert len(res) > 0
    assert all(e.source.mwid == 8 for e in res)

    # By repr_name for Counterpart
    res = wallet.find(source="Telefónica")
    assert len(res) > 0

    # By Account object
    account = find(wallet.accounts, lambda a: a.mwid == 8)[0]
    res = wallet.find(source=account)
    assert len(res) > 0
    assert all(e.source.mwid == 8 for e in res)

    # By Counterpart object
    counterpart = find(wallet.counterparts, lambda c: c.repr_name == "Telefónica")[0]
    res = wallet.find(source=counterpart)
    assert len(res) > 0


def test_get_target(wallet):
    # By MWID
    res = wallet.find(target=8)
    assert len(res) > 0
    assert all(e.target.repr_name == "@Personales" for e in res)

    # By repr_name for Account
    res = wallet.find(target="@Personales")
    assert len(res) > 0
    assert all(e.target.mwid == 8 for e in res)

    # By repr_name for Counterpart
    res = wallet.find(target="Mercadona")
    assert len(res) > 0

    # By Account object
    account = find(wallet.accounts, lambda a: a.mwid == 8)[0]
    res = wallet.find(target=account)
    assert len(res) > 0
    assert all(e.target.mwid == 8 for e in res)

    # By Counterpart object
    counterpart = find(wallet.counterparts, lambda c: c.repr_name == "Mercadona")[0]
    res = wallet.find(target=counterpart)
    assert len(res) > 0


def test_get_account(wallet):
    # By MWID
    res = wallet.find(account=8)
    cmp1 = find(wallet.entries, lambda e: e.source.mwid == 8)
    cmp2 = find(wallet.entries, lambda e: e.target.mwid == 8)
    assert len(res) == len(cmp1) + len(cmp2)

    # By repr_name
    res = wallet.find(account="@Personales")
    assert len(res) == len(cmp1) + len(cmp2)

    # By Account object
    account = find(wallet.accounts, lambda a: a.mwid == 8)[0]
    res = wallet.find(account=account)
    assert len(res) == len(cmp1) + len(cmp2)
    assert all((e.source.mwid == 8 or e.target.mwid == 8) for e in res)


def test_get_counterpart(wallet):
    # By repr_name
    res = wallet.find(counterpart="Hacienda")
    assert len(res) > 0

    # By Counterpart object
    counterpart = find(wallet.counterparts, lambda c: c.repr_name == "Hacienda")[0]
    res = wallet.find(counterpart=counterpart)
    assert len(res) > 0


def test_get_category(wallet):
    # By MWID
    res = wallet.find(category=11)
    assert len(res) > 0
    assert all(e.category.code == "B80" for e in res)

    # By repr_name
    res = wallet.find(category="T11")
    assert len(res) > 0
    assert all(e.category.name == "Cuotas mensuales" for e in res)

    # By Category object
    category = find(wallet.categories, lambda c: c.mwid == 11)[0]
    res = wallet.find(category=category)
    assert len(res) > 0
    assert all(e.category.code == "B80" for e in res)


# Product


def test_get_product_simple(wallet):
    res = wallet.find(mwid=[5332, 5331, 5330])
    assert len(res) == 3

    res = wallet.find(mwid=[5555, 6666])
    assert len(res) == 0


def test_get_product_multiple(wallet):
    res = wallet.find(entity=["account", "category"], mwid=[10, 8])
    assert len(res) == 2


def test_get_product_complex(wallet):
    res = wallet.find(
        account=["@Personales", "@Básicos", "@Reserva"],
        category=["T11", "B01"],
        date=("2023", "2025"),
    )
    assert len(res) > 0
    assert all(2023 <= e.date.year < 2025 for e in res)
    assert all(e.category.code in ("T11", "B01") for e in res)

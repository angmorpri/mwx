# 2025/08/21
"""
read.py - Reading MyWallet data.

Defines function 'read', to load data from a SQLite database with MyWallet
backup format.

"""

import sqlite3 as sqlite
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import Any

from mwx.etl.common import MYWALLET_TABLES, MWXNamespace
from mwx.model import Account, Category, Counterpart, Entry
from mwx.util import find_first

TBLCAT_TO_CAT = [-1, +1]  # 0 --> -1 expense, +1 --> +1 income
TBLNOTES_TO_NOTES = [-1, +1, 0]  # 0 --> -1 payee, +1 --> +1 payer, -1 --> 0 neutral
TBLTRANS_TO_ENTRY = [-1, +1]  # 0 --> -1 expense, +1 --> +1 income


def read(path: str | Path) -> MWXNamespace:
    """Reads data from a MyWallet SQLite database"""
    # Collect tables from the database
    data = {}
    with sqlite.connect(path) as conn:
        conn.row_factory = _namedtuple_row_factory
        cursor = conn.cursor()
        for table in MYWALLET_TABLES:
            cursor.execute(f"SELECT * FROM {table}")
            data[table] = cursor.fetchall()

    # Accounts
    accounts = []
    for row in data["tbl_account"]:
        account = Account(
            mwid=row.acc_id,
            name=row.acc_name,
            order=row.acc_order,
            color=row.acc_color,
            is_visible=not bool(row.acc_is_closed),
        )
        accounts.append(account)

    # Categories -- From 'tbl_cat'
    categories = []
    for row in data["tbl_cat"]:
        category = Category(
            mwid=row.category_id,
            repr_name=row.category_name,
            cat_type=TBLCAT_TO_CAT[row.category_is_inc],
            color=row.category_color,
            icon_id=row.category_icon,
        )
        categories.append(category)

    # Categories -- From 'tbl_notes' where 'note_payee_payer == -1'
    # and 'note_text' starts with '[' and ends with ']'
    for row in data["tbl_notes"]:
        if (
            row.note_payee_payer == -1
            and row.note_text.startswith("[")
            and row.note_text.endswith("]")
        ):
            category = Category(
                mwid=row.notey_id,
                repr_name=row.note_text[1:-1],
                cat_type=0,
            )
            categories.append(category)

    # Entries - Transactions -- From 'tbl_trans'
    entries = []
    counterparts = []
    for row in data["tbl_trans"]:
        if row.exp_is_paid == 0:
            continue  # Skip unpaid entries
        entry_type = TBLTRANS_TO_ENTRY[row.exp_is_debit]
        counterpart = find_first(counterparts, name=row.exp_payee_name)
        if counterpart is None:
            counterpart = Counterpart(row.exp_payee_name)
            counterparts.append(counterpart)
        source, target = _get_source_target(
            entry_type, row.exp_acc_id, counterpart, accounts
        )
        category = _get_category(entry_type, row.exp_cat, categories)
        item, details = _itemize(row.exp_note)
        entry = Entry(
            mwid=row.exp_id,
            amount=row.exp_amount,
            date=datetime.strptime(row.exp_date, "%Y%m%d"),
            ent_type=entry_type,
            source=source,
            target=target,
            category=category,
            item=item,
            details=details,
            is_bill=bool(row.exp_is_bill),
        )
        entries.append(entry)

    # Entries - Transfers -- From 'tbl_transfer'
    for row in data["tbl_transfer"]:
        source = _get_source_target(0, row.trans_from_id, None, accounts)[0]
        target = _get_source_target(0, row.trans_to_id, None, accounts)[0]
        raw_category, _notes = _itemize(row.trans_note)
        category = _get_category(0, raw_category[1:-1], categories)
        item, details = _itemize(_notes)
        entry = Entry(
            mwid=row.trans_id,
            amount=row.trans_amount,
            date=datetime.strptime(row.trans_date, "%Y%m%d"),
            ent_type=0,
            source=source,
            target=target,
            category=category,
            item=item,
            details=details,
            is_bill=False,
        )
        entries.append(entry)

    return MWXNamespace(
        accounts=list(sorted(accounts)),
        counterparts=list(sorted(counterparts)),
        categories=list(sorted(categories)),
        entries=list(sorted(entries)),
    )


# Auxiliary functions


def _namedtuple_row_factory(
    cursor: sqlite.Cursor, row: tuple[tuple[str, Any]]
) -> namedtuple:
    fields = [col[0] for col in cursor.description]
    cls = namedtuple("Row", fields)
    return cls._make(row)


def _get_source_target(
    entry_type: int,
    acc_mwid: int,
    counterpart: Counterpart | None,
    accounts: list[Account],
) -> tuple[Account | Counterpart, Account | Counterpart]:
    """Finds the source and target of a transaction based on its type.

    Gets the account item by its MyWallet ID, creating a legacy one if it
    does not exist.

    """
    account = find_first(accounts, mwid=acc_mwid)
    if account is None:
        account = Account(
            mwid=acc_mwid,
            name=f"LEGACY{acc_mwid:02d}",
            is_legacy=True,
        )
        accounts.append(account)
    if entry_type in (0, -1):
        return account, counterpart
    else:
        return counterpart, account


def _get_category(
    entry_type: int,
    cat_id: int | str,
    categories: list[Category],
) -> Category:
    """Finds a category by its MyWallet ID or its name, creating a legacy
    one if it does not exist.

    """
    if isinstance(cat_id, int):
        category = find_first(categories, mwid=cat_id)
        if category is None:
            category = Category(
                mwid=cat_id,
                repr_name=f"X{cat_id:02d}. LEGACY {cat_id}",
                cat_type=entry_type,
                is_legacy=True,
            )
            categories.append(category)
    elif isinstance(cat_id, str):
        category = find_first(categories, repr_name=cat_id)
        if category is None:
            category = Category(
                mwid=0,
                repr_name="X00. LEGACY",
                cat_type=entry_type,
                is_legacy=True,
            )
            categories.append(category)
    return category


def _itemize(text: str) -> tuple[str, str]:
    """Extracts item and details from a note text."""
    item, *detail_list = text.split("\n")
    details = "\n".join(detail_list).strip()
    return item.strip(), details

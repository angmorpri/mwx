# 2025/08/21
"""
etl.py - Reading and writing MyWallet data.

Defines functions 'load' and 'write' for MyWallet data from or to SQLite
databases. 'MWXNamespace' is a namedtuple defined to handle the collections of
items: 'accounts', 'categories', 'entries', 'notes' and 'counterparts'.

"""

import sqlite3 as sqlite
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import Any

from mwx.model import Account, Category, Counterpart, Entry, Note
from mwx.util import find_first

MWXNamespace = namedtuple(
    "MWXNamespace", ["accounts", "categories", "entries", "notes", "counterparts"]
)

MYWALLET_TABLES = [
    "tbl_account",
    "tbl_cat",
    "tbl_notes",
    "tbl_transfer",
    "tbl_trans",
]

TBLCAT_TO_CAT = [-1, +1]  # 0 --> -1 expense, +1 --> +1 income
CAT_TO_TBLCAT = [None, +1, 0]  # -1 --> 0 expense, +1 --> +1 income
TBLNOTES_TO_NOTES = [-1, +1, 0]  # 0 --> -1 payee, +1 --> +1 payer, -1 --> 0 neutral
NOTES_TO_TBLNOTES = [-1, +1, 0]  # 0 --> -1 neutral, +1 --> +1 payer, -1 --> 0 payee
TBLTRANS_TO_ENTRY = [-1, +1]  # 0 --> -1 expense, +1 --> +1 income
ENTRY_TO_TBLTRANS = [None, +1, 0]  # +1 --> +1 income, -1 --> 0 expense


# Main functions


def read(path: str | Path) -> None:
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
            is_visible=bool(row.acc_is_closed),
        )
        accounts.append(account)

    # Categories -- From 'tbl_cat'
    categories = []
    for row in data["tbl_cat"]:
        category = Category(
            mwid=row.category_id,
            name=row.category_name,
            _type=TBLCAT_TO_CAT[row.category_is_inc],
            color=row.category_color,
            icon_id=row.category_icon,
        )
        categories.append(category)

    # Categories -- From 'tbl_notes' where 'note_payee_payer == -1'
    # and 'note_text' starts with '[' and ends with ']'
    # Notes -- From 'tbl_notes' where else
    notes = []
    for row in data["tbl_notes"]:
        if (
            row.note_payee_payer == -1
            and row.note_text.startswith("[")
            and row.note_text.endswith("]")
        ):
            category = Category(
                mwid=-row.notey_id,
                name=row.note_text[1:-1],
                _type=0,
            )
            categories.append(category)
        else:
            note = Note(
                mwid=row.notey_id,
                text=row.note_text,
                _type=TBLNOTES_TO_NOTES[row.note_payee_payer],
            )
        notes.append(note)

    # Entries - Transactions -- From 'tbl_trans'
    entries = []
    counterparts = []
    for row in data["tbl_trans"]:
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
            _type=entry_type,
            _source=source,
            _target=target,
            category=category,
            item=item,
            details=details,
            is_paid=bool(row.exp_is_paid),
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
            mwid=-row.trans_id,
            amount=row.trans_amount,
            date=datetime.strptime(row.trans_date, "%Y%m%d"),
            _type=0,
            _source=source,
            _target=target,
            category=category,
            item=item,
            details=details,
            is_paid=True,
            is_bill=False,
        )
        entries.append(entry)

    return MWXNamespace(
        accounts=list(sorted(accounts)),
        categories=list(sorted(categories)),
        notes=notes,
        entries=list(sorted(entries)),
        counterparts=counterparts,
    )


def write(path: str | Path) -> None:
    pass


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
            name=f"_LEGACY{acc_mwid:02d}_",
            legacy=True,
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
                name=f"_LEGACY{cat_id:02d}_",
                _type=entry_type,
                legacy=True,
            )
            categories.append(category)
    elif isinstance(cat_id, str):
        category = find_first(categories, name=cat_id)
        if category is None:
            _aux = len([c for c in categories if c.mwid >= 900])
            category = Category(
                mwid=999 - _aux,
                name=f"_LEGACY_{cat_id}_",
                _type=entry_type,
                legacy=True,
            )
            categories.append(category)
    return category


def _itemize(text: str) -> tuple[str, str]:
    """Extracts item and details from a note text."""
    item, *detail_list = text.split("\n")
    details = "\n".join(detail_list).strip()
    return item.strip(), details

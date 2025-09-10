# 2025/08/21
"""
etl.py - Defines the read and write operations for the application.

Read extracts data from MyWallet SQLite databases, and transforms it into MWX
data models (defined in model.py).
Write serializes MWX data models back into a MyWallet SQLite database.

"""

import sqlite3 as sqlite
from collections import namedtuple
from datetime import datetime
from pathlib import Path

from mwx.model import Account, Category, Counterpart, Entry, Note
from mwx.util import first

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

MWXNamespace = namedtuple(
    "MWXNamespace",
    ["accounts", "categories", "notes", "entries"],
)


def read(path: str | Path) -> MWXNamespace:
    """Reads data from a MyWallet SQLite database, and transforms it into MWX
    data models.

    Returns a 'MWXNamespace', an object that contains lists of models:
    'accounts', 'categories', 'notes' and 'entries'.

    """

    # Custom namedtuple row factory
    def _namedtuple_row_factory(cursor, row):
        fields = [col[0] for col in cursor.description]
        cls = namedtuple("Row", fields)
        return cls._make(row)

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
    for row in data["tbl_trans"]:
        entry_type = TBLTRANS_TO_ENTRY[row.exp_is_debit]
        source, target = _get_source_target(
            entry_type, row.exp_acc_id, row.exp_payee_name, accounts
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
        source = _get_source_target(0, row.trans_from_id, "", accounts)[0]
        target = _get_source_target(0, row.trans_to_id, "", accounts)[0]
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
        accounts=accounts,
        categories=categories,
        notes=notes,
        entries=entries,
    )


def write(data: MWXNamespace, path: str | Path) -> None:
    pass


# Auxiliar functions


def _get_source_target(
    entry_type: int, acc_mwid: int, counterpart_name: str, accounts: list[Account]
) -> tuple[Account | Counterpart, Account | Counterpart]:
    """Identifies the source and target of a transaction based on its type.

    Finds the accounts by their MyWallet ID, and, if they do not exist, creates
    legacy ones.

    """
    # Find or create the account
    account = first(accounts, mwid=acc_mwid)
    if account is None:
        account = Account(
            mwid=acc_mwid,
            name=f"_LEGACY{acc_mwid:02d}_",
            legacy=True,
        )
        accounts.append(account)

    # Return based on the entry's type
    if entry_type in (0, -1):
        return account, Counterpart(counterpart_name)
    else:
        return Counterpart(counterpart_name), account


def _get_category(
    entry_type: int, cat_id: int | str, categories: list[Category]
) -> Category:
    """Finds a category by its MyWallet ID or its name, creating a legacy one
    if necessary.

    """
    if isinstance(cat_id, int):
        category = first(categories, mwid=cat_id)
        if category is None:
            category = Category(
                mwid=cat_id,
                name=f"_LEGACY{cat_id:02d}_",
                _type=entry_type,
                legacy=True,
            )
            categories.append(category)
    elif isinstance(cat_id, str):
        category = first(categories, name=cat_id)
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

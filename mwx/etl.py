# 2025/08/21
"""
etl.py - Defines the read and write operations for the application.

Read extracts data from MyWallet SQLite databases, and transforms it into MWX
data models (defined in model.py).
Write serializes MWX data models back into a MyWallet SQLite database.

"""

import sqlite3 as sqlite
from datetime import datetime
from pathlib import Path

from mwx.model import Account, Category, Counterpart, Entry, Note

MYWALLET_TABLES = [
    "tbl_account",
    "tbl_cat",
    "tbl_notes",
    "tbl_transfer",
    "tbl_trans",
]

TBLCAT_TO_CAT = [+1, -1]  # 0 --> +1 income, +1 --> -1 expense
CAT_TO_TBLCAT = [None, 0, +1]  # +1 --> 0 income, -1 --> +1 expense
TBLNOTES_TO_NOTES = [-1, +1]  # 0 --> -1 payee, +1 --> +1 payer
NOTES_TO_TBLNOTES = [None, +1, 0]  # +1 --> +1 payer, -1 --> 0 payee
TBLTRANS_TO_ENTRY = [-1, +1]  # 0 --> -1 expense, +1 --> +1 income
ENTRY_TO_TBLTRANS = [None, +1, 0]  # +1 --> +1 income, -1 --> 0 expense


def read(path: str | Path) -> MWXNamespace:
    """Reads data from a MyWallet SQLite database, and transforms it into MWX
    data models.

    Returns a 'MWXNamespace', an object that contains the Registries
    'accounts', 'categories', 'notes' and 'entries'.

    """
    # Collect tables from the database
    data = {}
    with sqlite.connect(path) as conn:
        conn.row_factory = sqlite.Row
        cursor = conn.cursor()
        for table in MYWALLET_TABLES:
            cursor.execute(f"SELECT * FROM {table}")
            data[table] = cursor.fetchall()

    # Accounts
    accounts = Registry()
    for row in data["tbl_account"]:
        account = Account(
            mwid=row.acc_id,
            name=row.acc_name,
            order=row.acc_order,
            color=row.acc_color,
            is_visible=bool(row.acc_is_closed),
        )
        accounts.add(account)

    # Categories -- From 'tbl_cat'
    categories = Registry()
    for row in data["tbl_cat"]:
        category = Category(
            mwid=row.category_id,
            name=row.category_name,
            _type=TBLCAT_TO_CAT[row.category_is_inc],
            color=row.category_color,
            icon_id=row.category_icon,
        )
        categories.add(category)

    # Categories -- From 'tbl_notes' where 'note_payee_payer == -1'
    # Notes -- From 'tbl_notes' where 'note_payee_payer != -1'
    notes = Registry()
    for row in data["tbl_notes"]:
        if row.note_payee_payer == -1:
            category = Category(
                mwid=-row.notey_id,
                name=row.note_text,
                _type=0,
            )
            categories.add(category)
        else:
            note = Note(
                mwid=row.notey_id,
                text=row.note_text,
                type=TBLNOTES_TO_NOTES[row.note_payee_payer],
            )
            notes.add(note)

    # Entries -- From 'tbl_trans', transactions
    entries = Registry()
    for row in data["tbl_trans"]:
        entry_type = TBLTRANS_TO_ENTRY[row.exp_is_debit]
        source, target = _get_source_target(
            entry_type, row.exp_acc_id, row.exp_payee_name, accounts
        )
        item, details = _itemize(row.exp_note)
        entry = Entry(
            mwid=row.exp_id,
            amount=row.exp_amount,
            date=datetime.strftime(row.exp_date, "%Y%m%d"),
            _type=entry_type,
            _source=source,
            _target=target,
            category=_get_category(entry_type, row.exp_cat, categories),
            item=item,
            details=details,
            is_paid=bool(row.exp_is_paid),
            is_bill=bool(row.exp_is_bill),
        )
        entries.add(entry)

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
    entry_type: int, acc_mwid: int, counterpart_name: str, accounts: Registry[Account]
) -> tuple[Account | Counterpart, Account | Counterpart]:
    """Identifies the source and target of a transaction based on its type.

    Finds the accounts by their MyWallet ID, and, if they do not exist, creates
    legacy ones.

    """
    # Find or create the account
    account = accounts.find(mwid=acc_mwid)
    if account is None:
        account = Account(
            mwid=acc_mwid,
            name=f"_LEGACY{acc_mwid:02d}_",
            legacy=True,
        )
        accounts.add(account)

    # Return based on the entry's type
    if entry_type in (0, -1):
        return account, Counterpart(counterpart_name)
    else:
        return Counterpart(counterpart_name), account


def _get_category(
    entry_type: int, cat_mwid: int, categories: Registry[Category]
) -> Category:
    """Finds a category by its MyWallet ID, creating a legacy one if necessary."""
    category = categories.find(mwid=cat_mwid)
    if category is None:
        category = Category(
            mwid=cat_mwid,
            name=f"_LEGACY{cat_mwid:02d}_",
            _type=entry_type,
            legacy=True,
        )
        categories.add(category)
    return category


def _itemize(text: str) -> tuple[str, str]:
    """Extracts item and details from a note text."""
    item, *detail_list = text.split("\n")
    details = "\n".join(detail_list).strip()
    return item.strip(), details

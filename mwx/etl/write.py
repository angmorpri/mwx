# 2025/11/25
"""
write.py - Writing MyWallet data.

Defines function 'write', to save data to a SQLite database with MyWallet
backup format.

"""

import shutil
import sqlite3 as sqlite
import warnings
from datetime import datetime
from pathlib import Path

from mwx.etl.common import MWXNamespace
from mwx.util import find


def write(path: str | Path, data: MWXNamespace) -> Path:
    """Writes data to a MyWallet SQLite database

    `path` must point to a writable MyWallet backup database file, which will
    serve as a template for the new database.

    All entities in `data` will be written to the database, replacing any
    existing data. The behavior will be the following:
    - If an entity's 'mwid' matches an existing entity, it will be updated.
    - If an entity's 'mwid' does not match any existing entity, it will raise
    a warning and skip that entity.
    - If an entity exists in the database but not in `data`, it will be deleted.
    - If an entity's 'mwid' is -1, it will be treated as a new entity and
    assigned a new 'mwid'.

    Returns the path to the new database file.

    """
    # Create a copy of the template database to write to
    orig_path = Path(path)
    # target_path = orig_path.parent / f"MWX_{orig_path.name}"
    target_path = (
        orig_path.parent
        / f"MWX_{datetime.now().strftime('%Y%m%d%H%M%S')}_{orig_path.name}"
    )
    shutil.copy(orig_path, target_path)

    # Write data to the database
    pipeline = []
    with sqlite.connect(target_path) as conn:
        cursor = conn.cursor()

        # 1. Collect basic info
        # Accounts
        cursor.execute("SELECT acc_id FROM tbl_account")
        pipeline.append(
            (
                data.accounts,
                "tbl_account",
                "acc_id",
                {row[0] for row in cursor.fetchall()},
            )
        )

        # Categories -- From 'tbl_cat'
        cursor.execute("SELECT category_id FROM tbl_cat")
        pipeline.append(
            (
                find(data.categories, lambda x: x.type != 0),
                "tbl_cat",
                "category_id",
                {row[0] for row in cursor.fetchall()},
            )
        )

        # Categories -- From 'tbl_notes'
        cursor.execute("SELECT notey_id, note_text FROM tbl_notes")
        pipeline.append(
            (
                find(data.categories, lambda x: x.type == 0),
                "tbl_notes",
                "notey_id",
                {
                    row[0]
                    for row in cursor.fetchall()
                    if (row[1].startswith("[") and row[1].endswith("]"))
                },
            )
        )

        # Entries -- From 'tbl_trans'
        cursor.execute("SELECT exp_id, exp_is_paid FROM tbl_trans")
        pipeline.append(
            (
                find(data.entries, lambda x: x.type != 0),
                "tbl_trans",
                "exp_id",
                {row[0] for row in cursor.fetchall() if row[1] == 1},
            )
        )

        # Entries -- From 'tbl_transfer'
        cursor.execute("SELECT trans_id FROM tbl_transfer")
        pipeline.append(
            (
                find(data.entries, lambda x: x.type == 0),
                "tbl_transfer",
                "trans_id",
                {row[0] for row in cursor.fetchall()},
            )
        )

        # 2. Process each table
        for entities, table, table_id, existing_mwids in pipeline:
            to_update = []
            for entity in entities:
                # Ignore legacy entities
                if entity.is_legacy:
                    continue

                table_columns, table_values = zip(*entity.to_mywallet().items())

                # New entity
                if entity.mwid == -1:
                    cursor.execute(
                        f"""
                        INSERT INTO {table} ({', '.join(table_columns)})
                        VALUES ({', '.join(['?'] * len(table_columns))})
                        """,
                        table_values,
                    )
                    entity.mwid = cursor.lastrowid
                    conn.commit()

                # Existing entity (to bulk update later)
                else:
                    if entity.mwid in existing_mwids:
                        to_update.append((entity.mwid, table_values))
                        existing_mwids.remove(entity.mwid)
                    else:
                        warnings.warn(
                            f"Entity with ID {entity.mwid} not found in table "
                            f"'{table}'. It will be skipped.",
                            UserWarning,
                        )

            # Non-existing entities (to bulk delete later)
            to_delete = []
            for mwid in existing_mwids:
                to_delete.append(mwid)

            # Bulk update
            if to_update:
                update_placeholders = ", ".join([f"{col} = ?" for col in table_columns])
                cursor.executemany(
                    f"""
                    UPDATE {table}
                    SET {update_placeholders}
                    WHERE {table_id} = ?
                    """,
                    [(*vals, mwid) for mwid, vals in to_update],
                )
                conn.commit()

            # Bulk delete
            if to_delete:
                delete_placeholders = ", ".join(["?"] * len(to_delete))
                cursor.execute(
                    f"""
                    DELETE FROM {table}
                    WHERE {table_id} IN ({delete_placeholders})
                    """,
                    to_delete,
                )
                conn.commit()

    return target_path

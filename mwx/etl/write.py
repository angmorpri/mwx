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


def write(
    base_db_path: str | Path,
    data: MWXNamespace,
    *,
    new_db_name: str = "MWX_{now}_{stem}.sqlite",
    unsafe: bool = False,
) -> Path:
    """Writes data to a MyWallet SQLite database

    `base_db_path` must point to a writable MyWallet backup database file,
    which will serve as a template for the new database. The new database will
    be stored at the same path, with name `new_db_name`, which can include the
    following placeholders:
    - `{now}`: Current date and time in 'YYYYMMDDHHMMSS' format.
    - `{name}` or `{}`: Original database file name with extension.
    - `{stem}`: Original database file name without extension.
    - `{ext}`: Original database file extension.

    If `unsafe` is True, it will override existing files at `new_db_name`
    without warning. Otherwise, it will raise an error if the target file
    exists.

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
    target_path = process_path(base_db_path, new_db_name, unsafe)

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


def process_path(
    base_db_path: str | Path,
    new_db_name: str,
    unsafe: bool = False,
) -> Path:
    """Process the new database path with placeholders."""
    orig_path = Path(base_db_path)

    # Name
    new_db_name = new_db_name.replace("{}", "{name}")
    new_db_name = new_db_name.format(
        now=datetime.now().strftime("%Y%m%d%H%M%S"),
        name=orig_path.name,
        stem=orig_path.stem,
        ext=orig_path.suffix,
    )

    # Path
    target_path = orig_path.parent / new_db_name

    # Check existence
    if target_path.exists() and not unsafe:
        raise FileExistsError(
            f"Target database '{target_path}' already exists. "
            "Use 'unsafe=True' to overwrite."
        )

    # Copy and return target path
    shutil.copy(orig_path, target_path)
    return target_path

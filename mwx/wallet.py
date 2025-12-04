# 2025/11/10
"""
wallet.py - Class to handle entities and common operations.

Defines Wallet.

"""
from __future__ import annotations

from pathlib import Path

from mwx import etl


class Wallet:
    """Represents a wallet containing various financial entities.

    Provides lists to access MWX entities:
    - accounts: List of all Account objects.
    - categories: List of all Category objects.
    - counterparts: List of all Counterpart objects.
    - entries: List of all Entry objects.
    - incomes: Filtered list of income Entry objects.
    - expenses: Filtered list of expense Entry objects.
    - transfers: Filtered list of transfer Entry objects.

    Methods to read and write wallet data from/to a MyWallet database:
    - read()
    - write()

    And comfort methods for common operations:
    - get(): Retrieve an entity by its parameters in a smart way.
    - sum(): Sum amounts of entries with optional filters.

    Constructor may receive a path to a MyWallet database, in which case it
    will call 'read()' automatically.

    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.accounts = []
        self.categories = []
        self.counterparts = []
        self.entries = []

        self.source_path = None
        self.target_path = None

        if db_path:
            self.read(db_path)

    # ETL

    def read(self, path: str | Path) -> None:
        """Reads wallet data from a MyWallet database."""
        self.source_path = Path(path)
        data = etl.read(self.source_path)
        self.accounts = data.accounts
        self.categories = data.categories
        self.counterparts = data.counterparts
        self.entries = data.entries

    def write(
        self,
        path: str | Path | None = None,
        *,
        new_db_name: str = "MWX_{now}_{stem}.sqlite",
        overwrite: bool = False,
        safe_delete: bool = False,
        verbose: int = 2,
    ) -> Path:
        """Writes wallet data to a MyWallet database.

        If `path` is None, it will try to use an existing `target_path`, in
        case the wallet was written before. If no `target_path` exists, it
        will use the original `source_path` from which the wallet was read.

        See `mwx.etl.write()` for details on parameters.

        Returns the path to the new database file, and stores it in
        `target_path`.

        """
        if path is None:
            if self.target_path is not None:
                path = self.target_path
            elif self.source_path is not None:
                path = self.source_path
            else:
                raise ValueError(
                    "No target path specified, and no source or previous "
                    "target path available."
                )

        self.target_path = etl.write(
            base_db_path=path,
            data=etl.MWXNamespace(
                accounts=self.accounts,
                categories=self.categories,
                counterparts=self.counterparts,
                entries=self.entries,
            ),
            new_db_name=new_db_name,
            overwrite=overwrite,
            safe_delete=safe_delete,
            verbose=verbose,
        )
        return self.target_path

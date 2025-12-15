# 2025/11/10
"""
wallet.py - Class to handle entities and common operations.

Defines Wallet.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from mwx import etl
from mwx.model import Account, WalletEntity
from mwx.util import dict_product, find


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

    # Extra entities

    @property
    def incomes(self) -> list[WalletEntity]:
        return find(self.entries, type=+1)

    @property
    def expenses(self) -> list[WalletEntity]:
        return find(self.entries, type=-1)

    @property
    def transfers(self) -> list[WalletEntity]:
        return find(self.entries, type=0)

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

    # Convenience methods

    def get(
        self, *funcs: Callable[[WalletEntity], bool], **params: Any
    ) -> list[WalletEntity]:
        """Retrieves entities matching given criteria.

        Criteria can be provided in two ways:
        - Positional arguments: must be functions that take an entity and
        return either True or False. If multiple functions are provided, all
        must return True for an entity to be included in the result.
        - Keyword arguments: must be attribute-value pairs. An entity must have
        the specified attributes with the corresponding values to be included
        in the result. If the attribute does not exist on the entity, it is
        considered a non-match.

        You can specify which entities to search in with param 'entity', which
        needs to be one of 'account', 'category', 'counterpart', 'entry',
        'income', 'expense', 'transfer'. If not specified, all entities will be
        searched.

        Dates can be specified using 'date' parameter, which can be:
        - An integer, will be converted to a string.
        - A string, with either "YYYY", "YYYYMM", "YYYYMMDD", "YYYY-MM" or
          "YYYY-MM-DD" formats.
        - A datetime.date or datetime.datetime object.
        You can also directly provide 'year', 'month' and 'day' parameters.

        Both 'date' and 'amount' can also receive a tuple of two values, which
        will be treated as a range [min, max). If any is None, it will be
        treated as unbounded on that side.

        'source', 'target', and 'category' parameters for entries allow
        entities, names, repr_names, codes or MWIDs.

        'account' and 'counterpart' parameters search both in 'source' and
        'target' fields of entries.

        If any of the **parms is a list, this function will be called per each
        value, and the results will be concatenated. If multiple parameters are
        lists, a Cartesian product will be performed. Duplicate results will
        not be removed.

        Returns a list of entities that match all provided criteria.

        """
        # Performing Cartesian product for list parameters
        params = {
            param: [value] if not isinstance(value, list) else value
            for param, value in params.items()
        }
        res = []
        for param_set in dict_product(params):
            res += self._get(*funcs, **param_set)
        return res

    def _get(
        self, *funcs: Callable[[WalletEntity], bool], **params: Any
    ) -> list[WalletEntity]:
        funcs = list(funcs)

        # Entities
        entity_type = params.pop("entity", None)
        if entity_type == "account":
            entities = self.accounts
        elif entity_type == "category":
            entities = self.categories
        elif entity_type == "counterpart":
            entities = self.counterparts
        elif entity_type == "entry":
            entities = self.entries
        elif entity_type == "income":
            entities = self.incomes
        elif entity_type == "expense":
            entities = self.expenses
        elif entity_type == "transfer":
            entities = self.transfers
        else:
            entities = (
                self.accounts + self.categories + self.counterparts + self.entries
            )

        # Amount range
        amount = params.pop("amount", None)
        if amount and isinstance(amount, tuple):
            min_amount, max_amount = amount
            min_amount = -1_000_000.0 if min_amount is None else min_amount
            max_amount = +1_000_000.0 if max_amount is None else max_amount
            funcs.append(
                lambda x, mina=min_amount, maxa=max_amount: (mina <= x.amount < maxa)
            )

        # Date and date range
        date = params.pop("date", None)
        if date:
            min_date, max_date = parse_date_range(date)
            funcs.append(
                lambda x, mind=min_date, maxd=max_date: (mind <= x.date < maxd)
            )

        # Year, month, day
        for date_part in ("year", "month", "day"):
            if date_part in params:
                value = params.pop(date_part)
                funcs.append(
                    lambda x, date_part=date_part, value=value: getattr(
                        x.date, date_part
                    )
                    == value
                )

        # Source, target, category resolution
        for param in ("source", "target", "category"):
            if param in params:
                value = params.pop(param)
                if isinstance(value, WalletEntity):
                    funcs.append(lambda x, p=param, v=value: getattr(x, p) == v)
                elif isinstance(value, int):
                    funcs.append(lambda x, p=param, v=value: getattr(x, p).mwid == v)
                elif isinstance(param, str) and param in ("source", "target"):
                    funcs.append(
                        lambda x, p=param, v=value: (getattr(x, p).repr_name == v)
                    )
                elif isinstance(param, str) and param == "category":  # category
                    funcs.append(
                        lambda x, p=param, v=value: (
                            getattr(x, p).repr_name == v
                            or getattr(x, p).code == v
                            or getattr(x, p).name == v
                        )
                    )

        # Account resolution
        account = params.pop("account", None)
        if account is not None:
            if isinstance(account, WalletEntity):
                funcs.append(lambda x, v=account: (x.source == v or x.target == v))
            elif isinstance(account, int):
                funcs.append(
                    lambda x, v=account: (x.source.mwid == v or x.target.mwid == v)
                )
            elif isinstance(account, str):
                funcs.append(
                    lambda x, v=account: (
                        x.source.repr_name == v or x.target.repr_name == v
                    )
                )

        # Counterpart resolution
        counterpart = params.pop("counterpart", None)
        if counterpart is not None:
            if isinstance(counterpart, WalletEntity):
                funcs.append(lambda x, v=counterpart: (x.source == v or x.target == v))
            elif isinstance(counterpart, str):
                funcs.append(
                    lambda x, v=counterpart: (
                        x.source.repr_name == v or x.target.repr_name == v
                    )
                )

        # Details param matches any substring in details
        details = params.pop("details", None)
        if details is not None:
            funcs.append(lambda x, v=details: (v in x.details))

        # Final filtering
        return find(entities, *funcs, **params)

    def sum(
        self,
        account: str | Account,
        *funcs: Callable[[WalletEntity], bool],
        **params: Any,
    ) -> float:
        """Sums amounts of entries for an account matching given criteria.

        Criteria are the same as in `get()` method.

        If 'date' is provided and it's not a tuple, it will be treated as a
        maximum date (exclusive).

        Returns the sum of amounts of matching entries.

        """
        # Fix account param
        params["account"] = account

        # Fix date
        date = params.get("date", None)
        if date is not None and not isinstance(date, tuple):
            params["date"] = (None, date)

        # Get entries
        entries = self.get(*funcs, **params)
        return round(
            sum(entry.amount * entry.flow(params["account"]) for entry in entries), 2
        )

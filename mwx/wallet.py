# 2025/11/10
"""
wallet.py - Class to handle entities and common operations.

Defines Wallet.

"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import EllipsisType
from typing import Any, Callable

from mwx import etl
from mwx.model import Account, WalletEntity
from mwx.util import daterange, dict_product, find

DateLikeObject = str | datetime | EllipsisType | None
DaterangeLikeObject = daterange | tuple[DateLikeObject, DateLikeObject]


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

    def find(
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
        - A datetime.datetime.
        - A string with format 'YYYY-MM-DD' or 'YYYYMMDD', where month and day
        are optional, in which case they will define a range.
        - A mwx.util.daterange object, or a tuple of two dates defining a range
        [min, max).

        You can also directly provide 'year', 'month' and 'day' parameters.

        Both 'date' and 'amount' can also receive a tuple of two values, which
        will be treated as a range [min, max). If any is None, it will be
        treated as unbounded on that side.

        'source', 'target', and 'category' parameters for entries allow
        entities, names, repr_names, codes or MWIDs.

        'account' and 'counterpart' parameters search both in 'source' and
        'target' fields of entries.

        'flow' can be used to filter entries by their flow with respect to a
        given account. If no account is provided, 'flow' will be ignored.

        'item' and 'details' parameters match any lowercase substring in the
        respective fields. If the value starts with '!', it will match the
        exact value instead.

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
            if isinstance(date, (datetime, str)):
                drange = daterange(date)
            elif isinstance(date, tuple):
                drange = daterange(date[0], date[1])
            elif isinstance(date, daterange):
                drange = date
            funcs.append(lambda x, dr=drange: (dr.start() <= x.date < dr.end()))

        # Year, month, day
        if any(k in params for k in ("year", "month", "day")):
            parts = {
                "year": params.pop("year", ...),
                "month": params.pop("month", ...),
                "day": params.pop("day", ...),
            }
            drange = daterange(**parts)
            funcs.append(lambda x, dr=drange: (dr.start() <= x.date < dr.end()))

        # Source, target resolution
        for param in ("source", "target"):
            if param in params:
                acc = params.pop(param)
                if isinstance(acc, WalletEntity):
                    funcs.append(lambda x, p=param, v=acc: getattr(x, p) == v)
                elif isinstance(acc, int):
                    funcs.append(lambda x, p=param, v=acc: getattr(x, p).mwid == v)
                elif isinstance(acc, str):
                    funcs.append(lambda x, p=param, v=acc: getattr(x, p).repr_name == v)

                if "flow" in params:
                    flow = params.pop("flow")
                    funcs.append(lambda x, acc=acc, f=flow: x.flow(acc) == f)

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
            if "flow" in params:
                flow = params.pop("flow")
                funcs.append(lambda x, acc=account, f=flow: x.flow(acc) == f)

        # Category resolution
        if "category" in params:
            acc = params.pop("category")
            if isinstance(acc, WalletEntity):
                funcs.append(lambda x, v=acc: x.category == v)
            elif isinstance(acc, int):
                funcs.append(lambda x, v=acc: x.category.mwid == v)
            elif isinstance(acc, str):
                funcs.append(
                    lambda x, v=acc: (
                        x.category.repr_name == v
                        or x.category.code == v
                        or x.category.name == v
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

        # Item and Details param matches any lowercase substring
        item = params.pop("item", None)
        if item is not None:
            if item.startswith("!"):
                funcs.append(lambda x, v=item[1:]: v == x.item)
            else:
                funcs.append(lambda x, v=item: (v.lower() in x.item.lower()))

        details = params.pop("details", None)
        if details is not None:
            if details.startswith("!"):
                funcs.append(lambda x, v=details[1:]: v == x.details)
            else:
                funcs.append(lambda x, v=details: (v.lower() in x.details.lower()))

        # Final filtering
        return find(entities, *funcs, **params)

    def sum(
        self,
        account: str | Account,
        date: DaterangeLikeObject | DateLikeObject,
        *funcs: Callable[[WalletEntity], bool],
        **params: Any,
    ) -> float:
        """Sums amounts of entries from the POV of an 'account' in a period
        of time defined by 'date'.

        'date' must be a mwx.util.daterange object, or a tuple of date-like
        objects defining a range [min, max). If a single date-like object is
        provided, it will be treated as (date, None).

        Optional filters can be provided just like in 'find()' method.

        """
        # Fix account param
        if not isinstance(account, (str, Account)):
            raise ValueError("'account' parameter must be either str or Account.")
        params["account"] = account

        # Fix date
        if not isinstance(date, (daterange, tuple)):
            date = (date, None)
        params["date"] = date

        # Get entries
        entries = self.find(*funcs, **params)
        total = sum(entry.amount * entry.flow(params["account"]) for entry in entries)
        return round(total, 2)

    def budget(
        self,
        account: str | Account,
        date: DateLikeObject,
        *funcs: Callable[[WalletEntity], bool],
        **params: Any,
    ) -> float:
        """Sums amounts of entries from the POV of an 'account' since available
        to the given 'date' (exclusive).

        'date' must be a date-like object.

        Optional filters can be provided just like in 'find()' method.

        Roughly equivalent to sum(account, daterange(None, date), ...).

        """
        return self.sum(
            account,
            daterange(..., date),
            *funcs,
            **params,
        )

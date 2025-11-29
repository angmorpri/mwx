# 2025/11/10
"""
model.py - Model definitions for MWX entities.

Defines Account, Counterpart, Category and Entry.

"""

from __future__ import annotations

import random
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

RGB_REGEX = re.compile(r"^#([0-9a-fA-F]{6})$")
CATEGORY_FULL_REGEX = re.compile(r"^[A-Za-z]\d{2}\. .+$")
CATEGORY_CODE_REGEX = re.compile(r"^[A-Za-z]\d{2}$")

CAT_TO_TBLCAT = [None, +1, 0]  # -1 --> 0 expense, +1 --> +1 income
NOTES_TO_TBLNOTES = [-1, +1, 0]  # 0 --> -1 neutral, +1 --> +1 payer, -1 --> 0 payee
ENTRY_TO_TBLTRANS = [None, +1, 0]  # +1 --> +1 income, -1 --> 0 expense


class _MWXBaseModel(ABC):
    """Base class for MWX models.

    Defines:
    - mwid attribute, for identification of entities in MyWallet app.
    - Comparison methods '__eq__' and '__lt__' based on abstract property
    'sorting_key'.
    - Representation method '__repr__'.

    Requires subclasses to implement:
    - 'sorting_key' property, for comparison operations.
    - 'to_dict()' method, for serialization to dictionary.
    - 'to_mywallet()' method, for conversion to MyWallet format.

    """

    def __init__(self, mwid: int) -> None:
        self.mwid = mwid
        if self.mwid < -1:
            raise ValueError("MWID must be -1 (new entity) or non-negative integer.")
        self.str_mwid = f"{self.mwid:05d}" if self.mwid != -1 else "-----"

    @property
    @abstractmethod
    def sorting_key(self) -> tuple[Any, ...]:
        """Abstract property for sorting key."""
        pass

    def __eq__(self, other: _MWXBaseModel) -> bool:
        if not isinstance(other, _MWXBaseModel):
            return NotImplemented
        return self.sorting_key == other.sorting_key

    def __lt__(self, other: _MWXBaseModel) -> bool:
        if not isinstance(other, _MWXBaseModel):
            return NotImplemented
        return self.sorting_key < other.sorting_key

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} mwid={self.mwid}>"


# Entities


class Account(_MWXBaseModel):
    """Account entity."""

    _GLOBAL_ORDER = 100

    def __init__(
        self,
        mwid: int,
        name: str,
        order: int = -1,
        color: str = "#000000",
        is_visible: bool = True,
        is_legacy: bool = False,
    ) -> None:
        super().__init__(mwid)
        self._name = None
        self._order = None
        self._color = None
        self.is_visible = is_visible
        self.is_legacy = is_legacy

        self.name = name
        self.order = order
        self.color = color

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Must not have spaces and first letter capitalized."""
        if " " in value:
            raise ValueError(
                f"Account name cannot contain spaces, '{value}' introduced."
            )
        self._name = value[0].upper() + value[1:]

    @property
    def repr_name(self) -> str:
        return "@" + self._name

    @property
    def order(self) -> int:
        return self._order

    @order.setter
    def order(self, value: int) -> None:
        """Must be in [0, 999], or -1 for auto-assignment."""
        if value < 0:
            self._order = Account._GLOBAL_ORDER
            Account._GLOBAL_ORDER += 1
        elif value > 999:
            raise ValueError(f"Account order must be between 0 and 999, not '{value}'.")
        else:
            self._order = value
            Account._GLOBAL_ORDER = max(Account._GLOBAL_ORDER, value + 1)

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        """Must be a valid hex color code."""
        if not RGB_REGEX.match(value):
            raise ValueError(
                f"Account color must be a valid hex color code, not '{value}'."
            )
        self._color = value

    @property
    def sorting_key(self) -> tuple[Any, ...]:
        return ("A", self.order, self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mwid": self.mwid,
            "name": self.name,
            "order": self.order,
            "color": self.color,
            "is_visible": self.is_visible,
            "is_legacy": self.is_legacy,
        }

    def to_mywallet(self) -> dict[str, Any]:
        return {
            "acc_name": self.name,
            "acc_initial": 0.0,
            "acc_order": self.order,
            "acc_is_closed": int(not self.is_visible),
            "acc_color": self.color,
            "acc_min_limit": 0.0,
        }

    def __str__(self) -> str:
        legacy = " [LEGACY]" if self.is_legacy else ""
        return (
            f"[{self.str_mwid}] {self.repr_name} ({self.order}, {self.color}){legacy}"
        )


class Counterpart(_MWXBaseModel):
    """Counterpart entity, either payer or payee."""

    def __init__(self, name: str) -> None:
        super().__init__(0)
        self.name = name
        self.is_legacy = False  # Counterparts are never legacy

    @property
    def repr_name(self) -> str:
        return self.name

    @property
    def sorting_key(self) -> tuple[Any, ...]:
        return ("A", 999, self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mwid": self.mwid,
            "name": self.name,
        }

    def to_mywallet(self) -> dict[str, Any]:
        return {}  # Counterparts are not stored as entities in MyWallet

    def __str__(self) -> str:
        return f"[{self.str_mwid}] {self.repr_name}"


class Category(_MWXBaseModel):
    """Category entity."""

    def __init__(
        self,
        mwid: int,
        repr_name: str,
        cat_type: int,
        icon_id: int = 0,
        color: str = "#000000",
        is_legacy: bool = False,
    ) -> None:
        super().__init__(mwid)
        self._code = None
        self._name = None
        self._type = None
        self._icon_id = None
        self._color = None
        self.is_legacy = is_legacy

        self.repr_name = repr_name
        self.icon_id = icon_id
        self.color = color

        # 'type' must be immutable after creation
        if cat_type not in (-1, 0, 1):
            raise ValueError(
                f"Category type must be -1 (expense), 0 (transfer), or +1 (income), not '{cat_type}'."
            )
        self._type = cat_type

    @property
    def code(self) -> str:
        return self._code

    @code.setter
    def code(self, value: str) -> None:
        """Must match CATEGORY_REGEX."""
        if not CATEGORY_CODE_REGEX.match(value):
            raise ValueError(f"Category code must match pattern 'Xnn', not '{value}'.")
        self._code = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Must have first letter capitalized."""
        self._name = value[0].upper() + value[1:]

    @property
    def repr_name(self) -> str:
        return f"{self._code}. {self._name}"

    @repr_name.setter
    def repr_name(self, value: str) -> None:
        """Must be '<code>. <name>'"""
        if not CATEGORY_FULL_REGEX.match(value):
            raise ValueError(
                f"Category repr_name must match pattern 'Xnn. Name', not '{value}'."
            )
        code_part, name_part = value.split(". ", 1)
        self.code = code_part
        self.name = name_part

    @property
    def type(self) -> int:
        return self._type

    @property
    def icon_id(self) -> int:
        return self._icon_id

    @icon_id.setter
    def icon_id(self, value: int) -> None:
        """Must be in [0, 999]."""
        if not (0 <= value <= 999):
            raise ValueError(
                f"Category icon_id must be between 0 and 999, not '{value}'."
            )
        self._icon_id = value

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        """Must be a valid hex color code."""
        if not RGB_REGEX.match(value):
            raise ValueError(
                f"Category color must be a valid hex color code, not '{value}'."
            )
        self._color = value

    @property
    def sorting_key(self) -> tuple[Any, ...]:
        return (
            "C",
            self.code,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mwid": self.mwid,
            "code": self.code,
            "name": self.name,
            "type": self.type,
            "icon_id": self.icon_id,
            "color": self.color,
            "is_legacy": self.is_legacy,
        }

    def to_mywallet(self) -> dict[str, Any]:
        if self.type == 0:
            # 'tbl_note' category
            return {
                "note_text": f"[{self.repr_name}]",
                "note_payee_payer": -1,
            }
        else:
            # 'tbl_cat' category
            return {
                "category_name": self.repr_name,
                "category_color": self.color,
                "category_is_inc": CAT_TO_TBLCAT[self.type],
                "category_icon": self.icon_id,
            }

    def __str__(self) -> str:
        legacy = " [LEGACY]" if self.is_legacy else ""
        return f"[{self.str_mwid}] {self.repr_name} ({self.type}, {self.icon_id}, {self.color}){legacy}"


class Entry(_MWXBaseModel):
    """Entry entity, either income, expense or transfer between accounts."""

    def __init__(
        self,
        mwid: int,
        amount: float,
        date: datetime,
        ent_type: int,
        source: Account | Counterpart,
        target: Account | Counterpart,
        category: Category,
        item: str = "",
        details: str = "",
        is_bill: bool = False,
    ) -> None:
        super().__init__(mwid)
        self._amount = None
        self.date = date
        self._type = None
        self._source = None
        self._target = None
        self._category = None
        self._item = None
        self.details = details
        self.is_bill = is_bill
        self.is_legacy = False  # Entries are never legacy

        # 'type' must be immutable after creation
        if ent_type not in (-1, 0, 1):
            raise ValueError(
                f"Entry type must be -1 (expense), 0 (transfer), or +1 (income), not '{ent_type}'."
            )
        self._type = ent_type

        self.amount = amount
        self.source = source
        self.target = target
        self.category = category
        self.item = item

    @property
    def amount(self) -> float:
        return self._amount

    @amount.setter
    def amount(self, value: float) -> None:
        """Amount must be positive, and gets rounded to 2 decimal places."""
        self._amount = abs(round(value, 2))

    @property
    def type(self) -> int:
        return self._type

    @property
    def source(self) -> Account | Counterpart:
        return self._source

    @source.setter
    def source(self, value: Account | Counterpart) -> None:
        """Checks source alignes with entry type.

        If type is expense (-1) or transfer (0), source must be an Account.
        If type is income (+1), source must be a Counterpart.
        Source cannot be the same as target.

        """
        if self.type in (-1, 0) and not isinstance(value, Account):
            raise ValueError(
                f"Entry source must be an Account for expense or transfer entries, not '{type(value)}'."
            )
        if self.type == 1 and not isinstance(value, Counterpart):
            raise ValueError(
                f"Entry source must be a Counterpart for income entries, not '{type(value)}'."
            )
        if value == self.target:
            raise ValueError("Entry source cannot be the same as target.")
        self._source = value

    @property
    def target(self) -> Account | Counterpart:
        return self._target

    @target.setter
    def target(self, value: Account | Counterpart) -> None:
        """Checks target alignes with entry type.

        If type is income (+1) or transfer (0), target must be an Account.
        If type is expense (-1), target must be a Counterpart.
        Target cannot be the same as source.

        """
        if self.type in (1, 0) and not isinstance(value, Account):
            raise ValueError(
                f"Entry target must be an Account for income or transfer entries, not '{type(value)}'."
            )
        if self.type == -1 and not isinstance(value, Counterpart):
            raise ValueError(
                f"Entry target must be a Counterpart for expense entries, not '{type(value)}'."
            )
        if value == self.source:
            raise ValueError("Entry target cannot be the same as source.")
        self._target = value

    @property
    def category(self) -> Category:
        return self._category

    @category.setter
    def category(self, cat: Category) -> None:
        """Category type must align with entry type."""
        if cat.type != self.type:
            raise ValueError(
                f"Entry category type '{cat.type}' does not match entry type '{self.type}'."
            )
        self._category = cat

    @property
    def item(self) -> str:
        return self._item

    @item.setter
    def item(self, value: str | None) -> None:
        """If empty or None, set to 'Sin concepto'"""
        self._item = "Sin concepto" if not value else value

    def has_account(self, account: Account | str) -> bool:
        """Checks if the entry involves the given account."""
        if isinstance(account, str):
            return account in (self.source.repr_name, self.target.repr_name)
        elif isinstance(account, Account):
            return account in (self.source, self.target)
        else:
            raise ValueError(
                "'account' argument must be an Account instance or an account name."
            )

    def flow(self, account: Account | str) -> int:
        """Returns the flow of money from the point of view of the
        given account.

        If it receives money, return +1; if it sends money, return -1. If the
        account is not involved, return 0.

        """
        if isinstance(account, str):
            acc_name = account
            if self.source.repr_name == acc_name:
                return -1
            elif self.target.repr_name == acc_name:
                return +1
            else:
                return 0
        elif isinstance(account, Account):
            acc = account
            if self.source == acc:
                return -1
            elif self.target == acc:
                return +1
            else:
                return 0
        else:
            raise ValueError(
                "'account' argument must be an Account instance or an account name."
            )

    @property
    def sorting_key(self) -> tuple[Any, ...]:
        return ("T", self.date, self.mwid, random.random())

    def to_dict(self) -> dict[str, Any]:
        return {
            "mwid": self.mwid,
            "amount": self.amount,
            "date": self.date.isoformat(),
            "type": self.type,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "category": self.category.to_dict(),
            "item": self.item,
            "details": self.details,
            "is_bill": self.is_bill,
        }

    def to_mywallet(self) -> dict[str, Any]:
        if self.type == 0:
            # 'tbl_transfer' entry
            return {
                "trans_from_id": self.source.mwid,
                "trans_to_id": self.target.mwid,
                "trans_amount": self.amount,
                "trans_date": f"{self.date:%Y%m%d}",
                "trans_note": (self.item + "\n" + self.details).strip(),
            }
        else:
            # 'tbl_trans' entry
            return {
                "exp_amount": self.amount,
                "exp_cat": self.category.mwid,
                "exp_acc_id": self.source.mwid if self.type == -1 else self.target.mwid,
                "exp_payee_name": (
                    self.source.name if self.type == +1 else self.target.name
                ),
                "exp_date": f"{self.date:%Y%m%d}",
                "exp_month": f"{self.date:%Y%m}",
                "exp_is_debit": ENTRY_TO_TBLTRANS[self.type],
                "exp_note": (self.item + "\n" + self.details).strip(),
                "exp_is_paid": 1,
                "exp_is_bill": int(self.is_bill),
            }

    def __str__(self) -> str:
        return f"[{self.str_mwid}] {self.date:%Y-%m-%d}: {self.amount:8.2f} € <{self.category.code}> ({self.source.repr_name} -> {self.target.repr_name}), '{self.item}'"

# 2025/08/21
"""
model.py - Defines the data model for the application.

Includes Account, Category, Entry and Note.

"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

RGB_REGEX = re.compile(r"^#([0-9A-Fa-f]{6})$")
WHITESPACE_REGEX = re.compile(r"\s")
CATEGORY_NAME_REGEX = re.compile(r"^[A-Za-z]\d{2}\. .+$")

CATEGORY_TYPES = {-1: "Expense", 0: "Transfer", 1: "Income"}


@dataclass
class Account:
    """Account

    'mwid' is the ID the accounts has in MyWallet.
    'name' cannot contain whitespaces.
    'order' defaults to the highest order found +1.
    'color' is checked to ensure it has '#RRGGBB' format.
    'legacy' is used for accounts that no longer exist, but still appear in
    some entries.

    """

    mwid: int
    name: str
    order: int = -1
    color: str = "#000000"
    is_visible: bool = True
    legacy: bool = False

    HIGHEST_ORDER: ClassVar[int] = 0

    def __post_init__(self) -> None:
        """Adjust and validate the account data."""
        # Name check
        if WHITESPACE_REGEX.search(self.name):
            raise ValueError(
                f"Attempt to create an Account with a name that contains whitespaces: {self.name}"
            )

        # Color check
        if not RGB_REGEX.match(self.color):
            raise ValueError(
                f"Attempt to create an Account with invalid color format: {self.color}"
            )

        # Order adjustments
        if self.order == -1:
            Account.HIGHEST_ORDER += 1
            self.order = Account.HIGHEST_ORDER
        Account.HIGHEST_ORDER = max(Account.HIGHEST_ORDER, self.order)

    # Comparison

    def __eq__(self, other: Account | Counterpart | str) -> bool:
        """
        Two accounts are equal if they have the same name.
        Can be compared to Counterparts or strings, will always return False.

        """
        if isinstance(other, Account):
            return self.name == other.name
        elif isinstance(other, (Counterpart, str)):
            return False
        return NotImplemented

    def __lt__(self, other: Account | Counterpart | str) -> bool:
        """
        Accounts are compared by their orders.
        When compared against counterparts, accounts should always come first.
        """
        if isinstance(other, Account):
            return self.order < other.order
        elif isinstance(other, (Counterpart, str)):
            return True
        return NotImplemented

    # Representation

    def __str__(self) -> str:
        """String representation of the account."""
        s = f"Account[{self.mwid:0>4}]('{self.name}', '{self.color}', {self.order}, {int(self.is_visible)})"
        if self.legacy:
            s = "Legacy" + s
        return s

    @property
    def repr_name(self) -> str:
        """Name used for representation"""
        return "@" + self.name


@dataclass
class Counterpart:
    """Counterpart

    Analogue of Account, used to allow both Account and Counterpart to be used
    indistinctly in sources and targets of Entries.

    """

    name: str

    # Comparison

    def __eq__(self, other: Account | Counterpart | str) -> bool:
        """
        Two counterparts or strings are equal if they have the same name.
        Can be compared to Accounts, will always return False.

        """
        if isinstance(other, Counterpart):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        elif isinstance(other, Account):
            return False
        return NotImplemented

    def __lt__(self, other: Account | Counterpart | str) -> bool:
        """
        Compares counterparts or strings based on their names.
        When compared against accounts, counterparts should always come last.
        """
        if isinstance(other, Counterpart):
            return self.name < other.name
        elif isinstance(other, str):
            return self.name < other
        elif isinstance(other, Account):
            return False
        return NotImplemented

    # Representation

    def __str__(self) -> str:
        return f"Counterpart('{self.name}')"

    @property
    def repr_name(self) -> str:
        return self.name


@dataclass
class Category:
    """Category

    'mwid' is the ID the category has in MyWallet. It'll be positive for
    transaction categories, and negative for transfer categories.
    'name' needs to follow the format "X##. Category Name", where 'X' can be
    any letter, and '#' must be digits.
    'type' is the type of the category, one of -1=Expense, +1=Income, or
    0=Transfer.
    'color' is checked to ensure it has '#RRGGBB' format.
    'legacy' is used for categories that no longer exist, but still appear in
    some entries.

    """

    mwid: int
    name: str
    _type: int  # Cannot change
    color: str = "#000000"
    icon_id: int = 0
    legacy: bool = False

    def __post_init__(self) -> None:
        """Adjust and validate the category data."""
        # MWID check
        if self._type == 0:
            self.mwid = -abs(self.mwid)

        # Name check
        if not CATEGORY_NAME_REGEX.match(self.name):
            raise ValueError(
                f"Attempt to create a Category with invalid name format: {self.name}"
            )

        # Color check
        if not RGB_REGEX.match(self.color):
            raise ValueError(
                f"Attempt to create a Category with invalid color format: {self.color}"
            )

    @property
    def code(self) -> str:
        """Get the category code."""
        return self.name.split(".")[0]

    @code.setter
    def code(self, value: str) -> None:
        """Set the category code."""
        new_name = f"{value}. {self.title}"
        # Validate new name
        if not CATEGORY_NAME_REGEX.match(new_name):
            raise ValueError(
                f"Attempt to set category code with invalid name format: {new_name}"
            )
        self.name = new_name

    @property
    def title(self) -> str:
        """Get the category title."""
        return self.name.split(". ")[1]

    @title.setter
    def title(self, value: str) -> None:
        """Set the category title."""
        new_name = f"{self.code}. {value}"
        # Validate new name
        if not CATEGORY_NAME_REGEX.match(new_name):
            raise ValueError(
                f"Attempt to set category title with invalid name format: {new_name}"
            )
        self.name = new_name

    @property
    def type(self) -> int:
        return self._type

    # Comparison

    def __eq__(self, other: Category) -> bool:
        """Two categories are equal if they have the same name."""
        if not isinstance(other, Category):
            return NotImplemented
        return self.name == other.name

    def __lt__(self, other: Category) -> bool:
        """Two categories are less than each other if their names are lexicographically ordered."""
        if not isinstance(other, Category):
            return NotImplemented
        return self.name < other.name

    # Representation

    def __str__(self) -> str:
        s = f"Category[{self.mwid:0>4}]('{self.name}', {CATEGORY_TYPES[self.type]}, '{self.color}', {self.icon_id})"
        if self.legacy:
            s = "Legacy" + s
        return s


@dataclass
class Note:
    """Notes that can be attached to entries.

    'type' can be +1=Payer, -1=Payee.

    """

    mwid: int
    text: str
    _type: int  # Cannot change

    def __str__(self) -> str:
        return f"Note[{self.mwid:0>4}]('{self.text}', {self.type})"

    @property
    def type(self) -> int:
        return self._type


@dataclass
class Entry:
    """Entry in the record.

    Entries can be either transactions (incomes or expenses) or transfers.

    'id' is a unique identifier for the entry.
    'mwid' is the ID the entry has in MyWallet. It'll be positive for
    transactions and negative for transfers.

    'type' indicates the type of the entry, either income (1), expense (-1),
    or transfer (0).

    'source' and 'target' can either be (Account, Counterpart), for expenses;
    (Counterpart, Account), for incomes; and (Account, Account) for transfers.
    This must align with the entry's type, and must not change during the
    entry lifecycle. Using strings for either 'source' or 'target' will convert
    them into Counterpart objects.

    'category' type must match entries type.

    'item' will default to the category title if empty.

    'in_day_order' is the amount of entries in that day when this entry
    arrived.

    """

    mwid: int
    amount: float
    date: datetime
    _type: int  # Cannot change
    _source: Account | Counterpart | str  # Cannot change
    _target: Account | Counterpart | str  # Cannot change
    category: Category
    item: str = ""
    details: str = ""
    is_paid: bool = True
    is_bill: bool = False
    in_day_order: int = -1

    DAY_TOTALS: ClassVar[dict[datetime, int]] = {}

    def __post_init__(self) -> None:
        """Adjust and validate the entry data."""
        # MWID check
        if self._type == 0:
            self.mwid = -abs(self.mwid)

        # Round amount
        self.amount = round(self.amount, 2)

        # Convert string sources/targets to Counterpart objects
        self._source = (
            Counterpart(self._source) if isinstance(self._source, str) else self._source
        )
        self._target = (
            Counterpart(self._target) if isinstance(self._target, str) else self._target
        )

        # Check source and target against type
        if self._type == 0:
            if not isinstance(self._source, Account):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"an Account as source"
                )
            if not isinstance(self._target, Account):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"an Account as target"
                )
        elif self._type == +1:
            if not isinstance(self._source, Counterpart):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"a Counterpart as source"
                )
            if not isinstance(self._target, Account):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"an Account as target"
                )
        elif self._type == -1:
            if not isinstance(self._source, Account):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"an Account as source"
                )
            if not isinstance(self._target, Counterpart):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"a Counterpart as target"
                )

        # Check category's type matches this type
        if self.category.type != self._type:
            raise ValueError(
                f"Entry of type {CATEGORY_TYPES[self._type]} cannot have "
                f"category of type {CATEGORY_TYPES[self.category.type]}"
            )

        # Adjust item
        if not self.item:
            self.item = self.category.title

        # Setup day order
        self.in_day_order = Entry.DAY_TOTALS.get(self.date, 0) + 1
        Entry.DAY_TOTALS[self.date] = self.in_day_order

    @property
    def type(self) -> int:
        return self._type

    @property
    def source(self) -> Account | Counterpart:
        return self._source

    @source.setter
    def source(self, value: Account | Counterpart | str) -> None:
        value = Counterpart(value) if isinstance(value, str) else value
        if self._type in (0, -1):
            if not isinstance(value, Account):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"an Account as source"
                )
        if self._type == +1:
            if not isinstance(value, Counterpart):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"a Counterpart as source"
                )
        self._source = value

    @property
    def target(self) -> Account | Counterpart:
        return self._target

    @target.setter
    def target(self, value: Account | Counterpart | str) -> None:
        value = Counterpart(value) if isinstance(value, str) else value
        if self._type in (0, +1):
            if not isinstance(value, Account):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"an Account as target"
                )
        if self._type == -1:
            if not isinstance(value, Counterpart):
                raise ValueError(
                    f"Entry of type {CATEGORY_TYPES[self._type]} must have "
                    f"a Counterpart as target"
                )
        self._target = value

    @property
    def id(self) -> str:
        return f"{self.date:%Y%m%d}{self.in_day_order:0>4}"

    # Comparison

    def __eq__(self, other: Entry) -> bool:
        """Two entries are equal if their IDs match."""
        if not isinstance(other, Entry):
            return NotImplemented
        return self.id == other.id

    def __lt__(self, other: Entry) -> bool:
        """Two entries are less than each other based on their IDs."""
        if not isinstance(other, Entry):
            return NotImplemented
        return self.id < other.id

    # Representation

    def __str__(self) -> str:
        s = f"Entry[{self.mwid:0>4}]"
        s += f"({self.amount:+>8.2f} {self.date:%Y-%m-%d} {self.source.repr_name} --> {self.target.repr_name} [{self.category.code}] '{self.item}')"
        return s

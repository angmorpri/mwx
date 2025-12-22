# 2025/12/19
"""
money.py - MWX money utilities
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext
from typing import Any, TypeAlias, Union

getcontext().prec = 28

Number: TypeAlias = Union[int, float, Decimal, "Money"]


class Money:
    __slots__ = ("_amount",)

    _QUANT = Decimal("0.01")

    def __init__(self, amount: Number) -> None:
        self._amount = self._to_decimal(amount)

    @staticmethod
    def _to_decimal(value: Number) -> Decimal:
        if isinstance(value, Money):
            value = value._amount
        elif isinstance(value, float):
            value = Decimal(str(value))
        else:
            value = Decimal(value)
        return value.quantize(Money._QUANT, rounding=ROUND_HALF_UP)

    # Properties

    @property
    def amount(self) -> Decimal:
        return self._amount

    # Arithmetic operations

    def __add__(self, other: Number) -> Money:
        return Money(self._amount + self._to_decimal(other))

    def __sub__(self, other: Number) -> Money:
        return Money(self._amount - self._to_decimal(other))

    def __mul__(self, other: int | float | Decimal) -> Money:
        return Money(self._amount * Decimal(str(other)))

    def __truediv__(self, other: int | float | Decimal) -> Money:
        return Money(self._amount / Decimal(str(other)))

    def __neg__(self) -> Money:
        return Money(-self._amount)

    def __abs__(self) -> Money:
        return Money(abs(self._amount))

    def __radd__(self, other: Number) -> Money:
        return self.__add__(other)

    def __rsub__(self, other: Number) -> Money:
        return Money(self._to_decimal(other) - self._amount)

    def __rmul__(self, other: int | float | Decimal) -> Money:
        return self.__mul__(other)

    def __rtruediv__(self, other: int | float | Decimal) -> Money:
        return Money(self._to_decimal(other) / self._amount)

    # Extra arithmetic operations

    def reldiff(self, other: Money) -> Decimal:
        if self._amount == Decimal("0"):
            raise ValueError("Cannot compute relative difference with zero amount")
        return (other._amount - self._amount) / abs(self._amount)

    def __matmul__(self, other: Money) -> Decimal:
        return self.reldiff(other)

    # Comparison operations

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self._amount == other._amount
        elif isinstance(other, (int, float, Decimal)):
            return self._amount == float(other)
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self._amount < other._amount
        elif isinstance(other, (int, float, Decimal)):
            return self._amount < self._to_decimal(other)
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self._amount <= other._amount
        elif isinstance(other, (int, float, Decimal)):
            return self._amount <= self._to_decimal(other)
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self._amount > other._amount
        elif isinstance(other, (int, float, Decimal)):
            return self._amount > self._to_decimal(other)
        return NotImplemented

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self._amount >= other._amount
        elif isinstance(other, (int, float, Decimal)):
            return self._amount >= self._to_decimal(other)
        return NotImplemented

    # String representation

    def __str__(self) -> str:
        sign = "+" if self._amount >= 0 else "-"
        value = (
            f"{abs(self._amount):12,.2f}".replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        )
        return f"{sign}{value} €"

    def __repr__(self) -> str:
        return f"Money({self._amount})"

    # Conversions

    def to_float(self) -> float:
        return float(self._amount)

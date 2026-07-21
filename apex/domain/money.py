"""Money value type (Book II 29.5).

Exact Decimal arithmetic, currency-safe: amounts in different
currencies never combine silently.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Self

from apex.core.exceptions import ValidationError
from apex.core.validation import ensure_finite, ensure_not_empty


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """An exact amount of one currency. May be negative (PnL, fees)."""

    currency: str
    amount: Decimal

    def __post_init__(self) -> None:
        ensure_not_empty(self.currency, "currency")
        if self.currency != self.currency.upper():
            raise ValidationError(
                "currency code must be uppercase",
                code="VAL-080",
                details={"currency": self.currency},
            )
        if not isinstance(self.amount, Decimal):
            raise ValidationError(
                "Money requires Decimal; use Money.parse()",
                code="VAL-081",
                details={"amount": repr(self.amount)},
            )
        ensure_finite(self.amount, "amount")

    @classmethod
    def parse(cls, currency: str, raw: str | int | Decimal) -> Self:
        """Build from an exact representation (float rejected)."""
        if isinstance(raw, (bool, float)):
            raise ValidationError(
                "Money.parse rejects float; pass str or Decimal",
                code="VAL-082",
                details={"amount": repr(raw)},
            )
        try:
            return cls(currency=currency, amount=Decimal(raw))
        except InvalidOperation as exc:
            raise ValidationError(
                "Money could not parse amount",
                code="VAL-083",
                details={"amount": str(raw)},
            ) from exc

    @classmethod
    def zero(cls, currency: str) -> Self:
        """The zero amount of a currency."""
        return cls(currency=currency, amount=Decimal(0))

    def _same_currency(self, other: "Money", operation: str) -> None:
        if not isinstance(other, Money) or other.currency != self.currency:
            raise ValidationError(
                f"cannot {operation} different currencies",
                code="VAL-084",
                details={
                    "left": self.currency,
                    "right": getattr(other, "currency", repr(other)),
                },
            )

    def __add__(self, other: "Money") -> "Money":
        self._same_currency(other, "add")
        return Money(currency=self.currency, amount=self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        self._same_currency(other, "subtract")
        return Money(currency=self.currency, amount=self.amount - other.amount)

    def __neg__(self) -> "Money":
        return Money(currency=self.currency, amount=-self.amount)

    def scale(self, factor: Decimal | int) -> "Money":
        """Scale by an exact dimensionless factor."""
        if isinstance(factor, bool) or not isinstance(factor, (Decimal, int)):
            raise ValidationError(
                "scale factor must be Decimal or int",
                code="VAL-085",
                details={"factor": repr(factor)},
            )
        return Money(currency=self.currency, amount=self.amount * Decimal(factor))

    @property
    def is_negative(self) -> bool:
        """Whether the amount is below zero."""
        return self.amount < 0

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

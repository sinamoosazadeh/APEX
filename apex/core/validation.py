"""Validation framework.

Book II 4.18: every object validates itself; invalid state is
unrepresentable. These helpers raise :class:`ValidationError` with
stable error codes and machine-readable details, and centrally enforce
the numerical stability policy (Constitution 3.26): NaN and infinity
never enter the platform.
"""

import math
from collections.abc import Sized
from decimal import Decimal

from apex.core.constants import SYMBOL_PATTERN
from apex.core.exceptions import ValidationError


def ensure(condition: bool, message: str, *, code: str = "VAL-001") -> None:
    """Raise :class:`ValidationError` unless ``condition`` holds."""
    if not condition:
        raise ValidationError(message, code=code)


def ensure_finite(value: float | Decimal, name: str) -> None:
    """Reject NaN and infinity (Constitution 3.26)."""
    finite = value.is_finite() if isinstance(value, Decimal) else math.isfinite(value)
    if not finite:
        raise ValidationError(
            f"{name} must be finite",
            code="VAL-002",
            details={"field": name, "value": str(value)},
        )


def ensure_in_range(
    value: float,
    lower: float,
    upper: float,
    name: str,
) -> None:
    """Require ``lower <= value <= upper`` (and finiteness)."""
    ensure_finite(value, name)
    if not lower <= value <= upper:
        raise ValidationError(
            f"{name} must be within [{lower}, {upper}]",
            code="VAL-003",
            details={"field": name, "value": value, "lower": lower, "upper": upper},
        )


def ensure_positive(value: float | Decimal, name: str) -> None:
    """Require a strictly positive, finite value."""
    ensure_finite(value, name)
    if value <= 0:
        raise ValidationError(
            f"{name} must be strictly positive",
            code="VAL-004",
            details={"field": name, "value": str(value)},
        )


def ensure_non_negative(value: float | Decimal, name: str) -> None:
    """Require a non-negative, finite value."""
    ensure_finite(value, name)
    if value < 0:
        raise ValidationError(
            f"{name} must be non-negative",
            code="VAL-005",
            details={"field": name, "value": str(value)},
        )


def ensure_not_empty(value: str | Sized, name: str) -> None:
    """Require a non-empty string or collection."""
    if len(value) == 0:
        raise ValidationError(
            f"{name} must not be empty",
            code="VAL-006",
            details={"field": name},
        )


def ensure_symbol(value: str) -> None:
    """Require canonical instrument symbol format (e.g. ``BTCUSDT``)."""
    if not SYMBOL_PATTERN.match(value):
        raise ValidationError(
            "symbol does not match canonical format",
            code="VAL-007",
            details={"symbol": value},
        )


def safe_divide(numerator: float, denominator: float, name: str) -> float:
    """Division with an explicit divide-by-zero contract violation."""
    ensure_finite(numerator, f"{name}.numerator")
    ensure_finite(denominator, f"{name}.denominator")
    if denominator == 0:
        raise ValidationError(
            f"{name}: division by zero",
            code="VAL-008",
            details={"field": name, "numerator": numerator},
        )
    result = numerator / denominator
    ensure_finite(result, f"{name}.result")
    return result

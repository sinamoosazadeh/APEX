"""Primitive value types.

Book II 4.4/4.5: no raw ``float`` crosses a module boundary. Each
concept gets its own wrapper type so that ``price + confidence`` is a
type error, not a silent bug. All wrappers are frozen, validate on
construction (NaN/infinity rejected centrally) and only permit
arithmetic within the same concept plus scalar scaling.

Market magnitudes (:class:`Price`, :class:`Volume`) are Decimal-based
for exactness (Constitution 3.26); analytical magnitudes are float-based
with explicit bounds.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import ClassVar, Self

from apex.core.exceptions import ValidationError
from apex.core.validation import ensure_finite


@dataclass(frozen=True, slots=True, order=True)
class FloatValue:
    """Base for float-backed concept types. Same-type arithmetic only."""

    value: float

    _MIN: ClassVar[float | None] = None
    _MAX: ClassVar[float | None] = None
    _MIN_EXCLUSIVE: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise ValidationError(
                f"{type(self).__name__} requires a numeric value",
                code="VAL-030",
                details={"value": repr(self.value)},
            )
        object.__setattr__(self, "value", float(self.value))
        ensure_finite(self.value, type(self).__name__)
        self._check_bounds()

    def _check_bounds(self) -> None:
        name = type(self).__name__
        minimum, maximum = type(self)._MIN, type(self)._MAX
        if minimum is not None:
            below = self.value <= minimum if type(self)._MIN_EXCLUSIVE else self.value < minimum
            if below:
                raise ValidationError(
                    f"{name} below permitted minimum {minimum}",
                    code="VAL-031",
                    details={"value": self.value, "minimum": minimum},
                )
        if maximum is not None and self.value > maximum:
            raise ValidationError(
                f"{name} above permitted maximum {maximum}",
                code="VAL-032",
                details={"value": self.value, "maximum": maximum},
            )

    def _same(self, other: object, operation: str) -> "FloatValue":
        if type(other) is not type(self):
            raise ValidationError(
                f"cannot {operation} {type(self).__name__} "
                f"with {type(other).__name__}",
                code="VAL-033",
            )
        assert isinstance(other, FloatValue)
        return other

    def __add__(self, other: object) -> Self:
        peer = self._same(other, "add")
        return type(self)(self.value + peer.value)

    def __sub__(self, other: object) -> Self:
        peer = self._same(other, "subtract")
        return type(self)(self.value - peer.value)

    def scale(self, factor: float) -> Self:
        """Return this value scaled by a dimensionless factor."""
        ensure_finite(factor, "factor")
        return type(self)(self.value * factor)

    def ratio_to(self, other: Self) -> float:
        """Dimensionless ratio ``self / other`` (same concept only)."""
        peer = self._same(other, "divide")
        if peer.value == 0:
            raise ValidationError(
                f"division by zero {type(self).__name__}",
                code="VAL-034",
            )
        return self.value / peer.value

    def __str__(self) -> str:
        return f"{self.value:g}"


# --- Bounded analytical concepts ---------------------------------------------


@dataclass(frozen=True, slots=True, order=True)
class Probability(FloatValue):
    """Probability in [0, 1] (Book II 4.18)."""

    _MIN: ClassVar[float | None] = 0.0
    _MAX: ClassVar[float | None] = 1.0

    def complement(self) -> "Probability":
        """Return ``1 - p``."""
        return Probability(1.0 - self.value)


@dataclass(frozen=True, slots=True, order=True)
class Confidence(FloatValue):
    """Model confidence in [0, 1]. Distinct concept from probability."""

    _MIN: ClassVar[float | None] = 0.0
    _MAX: ClassVar[float | None] = 1.0


@dataclass(frozen=True, slots=True, order=True)
class Reliability(FloatValue):
    """Source reliability in [0, 1] (feature contract, Book II 5.8)."""

    _MIN: ClassVar[float | None] = 0.0
    _MAX: ClassVar[float | None] = 1.0


@dataclass(frozen=True, slots=True, order=True)
class QualityScore(FloatValue):
    """Data quality score in [0, 1] (bar contract, Book II 5.6)."""

    _MIN: ClassVar[float | None] = 0.0
    _MAX: ClassVar[float | None] = 1.0


@dataclass(frozen=True, slots=True, order=True)
class RiskScore(FloatValue):
    """Normalized risk magnitude in [0, 1] (risk contract, Book II 5.10)."""

    _MIN: ClassVar[float | None] = 0.0
    _MAX: ClassVar[float | None] = 1.0


@dataclass(frozen=True, slots=True, order=True)
class Drawdown(FloatValue):
    """Drawdown as a fraction of equity in [0, 1]."""

    _MIN: ClassVar[float | None] = 0.0
    _MAX: ClassVar[float | None] = 1.0


@dataclass(frozen=True, slots=True, order=True)
class Weight(FloatValue):
    """Non-negative combination weight. Not a probability."""

    _MIN: ClassVar[float | None] = 0.0


@dataclass(frozen=True, slots=True, order=True)
class Score(FloatValue):
    """Unbounded model score. Not a probability, not a weight."""


@dataclass(frozen=True, slots=True, order=True)
class Entropy(FloatValue):
    """Non-negative information entropy (probability contract, 5.9)."""

    _MIN: ClassVar[float | None] = 0.0


@dataclass(frozen=True, slots=True, order=True)
class Volatility(FloatValue):
    """Non-negative volatility measure."""

    _MIN: ClassVar[float | None] = 0.0


@dataclass(frozen=True, slots=True, order=True)
class Atr(FloatValue):
    """Non-negative average true range in price units."""

    _MIN: ClassVar[float | None] = 0.0


@dataclass(frozen=True, slots=True, order=True)
class Spread(FloatValue):
    """Non-negative bid/ask spread in price units."""

    _MIN: ClassVar[float | None] = 0.0


@dataclass(frozen=True, slots=True, order=True)
class Latency(FloatValue):
    """Non-negative latency in milliseconds."""

    _MIN: ClassVar[float | None] = 0.0


@dataclass(frozen=True, slots=True, order=True)
class Leverage(FloatValue):
    """Strictly positive leverage multiple."""

    _MIN: ClassVar[float | None] = 0.0
    _MIN_EXCLUSIVE: ClassVar[bool] = True


@dataclass(frozen=True, slots=True, order=True)
class FundingRate(FloatValue):
    """Signed perpetual funding rate (fraction per interval)."""


@dataclass(frozen=True, slots=True, order=True)
class ExpectedReturn(FloatValue):
    """Signed expected return as a fraction (signal contract, 5.5)."""


@dataclass(frozen=True, slots=True, order=True)
class RiskReward(FloatValue):
    """Strictly positive reward-to-risk multiple (signal contract, 5.5)."""

    _MIN: ClassVar[float | None] = 0.0
    _MIN_EXCLUSIVE: ClassVar[bool] = True


# --- Decimal-backed market magnitudes ----------------------------------------


@dataclass(frozen=True, slots=True, order=True)
class DecimalValue:
    """Base for exact market magnitudes. Same-type arithmetic only."""

    value: Decimal

    _MIN: ClassVar[Decimal | None] = None
    _MIN_EXCLUSIVE: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise ValidationError(
                f"{type(self).__name__} requires Decimal; use {type(self).__name__}.parse()",
                code="VAL-035",
                details={"value": repr(self.value)},
            )
        ensure_finite(self.value, type(self).__name__)
        minimum = type(self)._MIN
        if minimum is not None:
            below = self.value <= minimum if type(self)._MIN_EXCLUSIVE else self.value < minimum
            if below:
                raise ValidationError(
                    f"{type(self).__name__} below permitted minimum {minimum}",
                    code="VAL-036",
                    details={"value": str(self.value)},
                )

    @classmethod
    def parse(cls, raw: str | int | Decimal) -> Self:
        """Build from an exact representation (float is rejected)."""
        if isinstance(raw, (bool, float)):
            raise ValidationError(
                f"{cls.__name__}.parse rejects float; pass str or Decimal",
                code="VAL-037",
                details={"value": repr(raw)},
            )
        try:
            return cls(Decimal(raw))
        except InvalidOperation as exc:
            raise ValidationError(
                f"{cls.__name__} could not parse value",
                code="VAL-038",
                details={"value": str(raw)},
            ) from exc

    def _same(self, other: object, operation: str) -> "DecimalValue":
        if type(other) is not type(self):
            raise ValidationError(
                f"cannot {operation} {type(self).__name__} with {type(other).__name__}",
                code="VAL-033",
            )
        assert isinstance(other, DecimalValue)
        return other

    def __add__(self, other: object) -> Self:
        peer = self._same(other, "add")
        return type(self)(self.value + peer.value)

    def __sub__(self, other: object) -> Self:
        peer = self._same(other, "subtract")
        return type(self)(self.value - peer.value)

    def scale(self, factor: Decimal | int) -> Self:
        """Return this magnitude scaled by an exact dimensionless factor."""
        if isinstance(factor, bool) or not isinstance(factor, (Decimal, int)):
            raise ValidationError(
                "scale factor must be Decimal or int",
                code="VAL-039",
                details={"factor": repr(factor)},
            )
        return type(self)(self.value * Decimal(factor))

    def ratio_to(self, other: Self) -> Decimal:
        """Dimensionless exact ratio ``self / other``."""
        peer = self._same(other, "divide")
        if peer.value == 0:
            raise ValidationError(
                f"division by zero {type(self).__name__}",
                code="VAL-034",
            )
        return self.value / peer.value

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True, order=True)
class Price(DecimalValue):
    """Strictly positive instrument price."""

    _MIN: ClassVar[Decimal | None] = Decimal(0)
    _MIN_EXCLUSIVE: ClassVar[bool] = True


@dataclass(frozen=True, slots=True, order=True)
class Volume(DecimalValue):
    """Non-negative traded volume."""

    _MIN: ClassVar[Decimal | None] = Decimal(0)


@dataclass(frozen=True, slots=True, order=True)
class Quantity(DecimalValue):
    """Strictly positive order/position quantity."""

    _MIN: ClassVar[Decimal | None] = Decimal(0)
    _MIN_EXCLUSIVE: ClassVar[bool] = True

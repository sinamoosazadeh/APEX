"""Signal contract (Book II 5.5).

A signal is an immutable, versioned, fully traceable decision product.
Fields that require engines from later phases (liquidity context,
market regime, feature vector reference, optimizer version) are
explicitly optional *by contract* until those phases land; the core
decision fields are mandatory.
"""

import uuid
from dataclasses import dataclass

from apex.core.base import BaseObject
from apex.core.enums import Direction, Timeframe
from apex.core.exceptions import ValidationError
from apex.core.types import (
    Confidence,
    ExpectedReturn,
    Price,
    Probability,
    RiskReward,
    RiskScore,
)
from apex.core.validation import ensure_not_empty, ensure_symbol


@dataclass(frozen=True, slots=True, kw_only=True)
class PriceZone:
    """An inclusive price band (entry, stop or target zone)."""

    lower: Price
    upper: Price

    def __post_init__(self) -> None:
        if self.lower.value > self.upper.value:
            raise ValidationError(
                "zone lower bound above upper bound",
                code="SIG-010",
                details={"lower": str(self.lower), "upper": str(self.upper)},
            )

    def contains(self, price: Price) -> bool:
        """Whether ``price`` lies inside the zone (inclusive)."""
        return self.lower.value <= price.value <= self.upper.value

    @property
    def midpoint(self) -> Price:
        """Arithmetic middle of the zone."""
        return Price((self.lower.value + self.upper.value) / 2)


@dataclass(frozen=True, slots=True, kw_only=True)
class Signal(BaseObject):
    """A directional trading signal (signal contract, Book II 5.5)."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    direction: Direction
    probability: Probability
    confidence: Confidence
    entry_zone: PriceZone
    stop_zone: PriceZone
    target_zones: tuple[PriceZone, ...]
    expected_return: ExpectedReturn | None = None
    expected_risk: RiskScore | None = None
    risk_reward: RiskReward | None = None
    expected_holding_bars: int | None = None
    market_regime: str | None = None
    liquidity_context_id: uuid.UUID | None = None
    feature_vector_id: uuid.UUID | None = None
    optimizer_version: str | None = None
    risk_profile: str | None = None
    execution_policy: str | None = None

    def _validate(self) -> None:
        ensure_not_empty(self.exchange, "exchange")
        ensure_symbol(self.symbol)
        if self.direction is Direction.NEUTRAL:
            raise ValidationError(
                "a tradeable signal cannot be neutral",
                code="SIG-001",
            )
        if not self.target_zones:
            raise ValidationError(
                "signal requires at least one target zone",
                code="SIG-002",
            )
        if self.expected_holding_bars is not None and self.expected_holding_bars < 1:
            raise ValidationError(
                "expected_holding_bars must be >= 1",
                code="SIG-003",
                details={"expected_holding_bars": self.expected_holding_bars},
            )
        self._validate_geometry()

    def _validate_geometry(self) -> None:
        """Stop must sit on the loss side of entry for the direction."""
        entry_mid = self.entry_zone.midpoint.value
        stop_mid = self.stop_zone.midpoint.value
        if self.direction is Direction.LONG and stop_mid >= entry_mid:
            raise ValidationError(
                "long signal requires stop below entry",
                code="SIG-004",
                details={"entry_mid": str(entry_mid), "stop_mid": str(stop_mid)},
            )
        if self.direction is Direction.SHORT and stop_mid <= entry_mid:
            raise ValidationError(
                "short signal requires stop above entry",
                code="SIG-005",
                details={"entry_mid": str(entry_mid), "stop_mid": str(stop_mid)},
            )

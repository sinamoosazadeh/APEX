"""Market data contracts: Bar and Tick (Book II 5.6/5.7).

Bars and ticks are pure data records with natural identity
(exchange, symbol, timeframe, time), not UUID-bearing entities.

Non-repainting guarantee: a :class:`Bar` knows whether it is closed.
Decision engines are contractually bound to confirmed bars only
(Master Prompt 3.2) - ``require_closed`` is their enforcement hook.
"""

from dataclasses import dataclass

from apex.core.enums import OrderSide, Timeframe
from apex.core.exceptions import ValidationError
from apex.core.serialization import JsonValue, content_hash, to_canonical
from apex.core.time.timestamp import Timestamp
from apex.core.types import FundingRate, Price, QualityScore, Quantity, Spread, Volume
from apex.core.validation import ensure_not_empty, ensure_symbol

_FULL_QUALITY = QualityScore(1.0)


@dataclass(frozen=True, slots=True, kw_only=True)
class Bar:
    """One OHLCV bar following the market bar contract (Book II 5.6)."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    open_time: Timestamp
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Volume
    is_closed: bool
    trade_count: int | None = None
    vwap: Price | None = None
    spread: Spread | None = None
    funding_rate: FundingRate | None = None
    open_interest: Volume | None = None
    quality: QualityScore = _FULL_QUALITY

    def __post_init__(self) -> None:
        ensure_not_empty(self.exchange, "exchange")
        ensure_symbol(self.symbol)
        if self.high.value < self.low.value:
            raise ValidationError(
                "bar high below low",
                code="DAT-001",
                details={"high": str(self.high), "low": str(self.low)},
            )
        for name in ("open", "close"):
            price: Price = getattr(self, name)
            if not self.low.value <= price.value <= self.high.value:
                raise ValidationError(
                    f"bar {name} outside [low, high]",
                    code="DAT-002",
                    details={name: str(price), "low": str(self.low), "high": str(self.high)},
                )
        if self.trade_count is not None and self.trade_count < 0:
            raise ValidationError(
                "trade_count must be non-negative",
                code="DAT-003",
                details={"trade_count": self.trade_count},
            )

    @property
    def close_time(self) -> Timestamp:
        """Exclusive end of the bar interval."""
        return self.open_time.add_ms(self.timeframe.duration_ms)

    def require_closed(self) -> "Bar":
        """Return self if closed; raise otherwise (non-repainting gate)."""
        if not self.is_closed:
            raise ValidationError(
                "operation requires a confirmed (closed) bar",
                code="DAT-004",
                details={"symbol": self.symbol, "open_time": str(self.open_time)},
            )
        return self

    @property
    def is_bullish(self) -> bool:
        """Whether the bar closed above its open."""
        return self.close.value > self.open.value

    def natural_key(self) -> str:
        """Deterministic identity of this bar."""
        return (
            f"{self.exchange}:{self.symbol}:{self.timeframe.value}:{self.open_time.epoch_ms}"
        )

    def to_dict(self) -> dict[str, JsonValue]:
        """Canonical serialized form."""
        result = to_canonical(self)
        assert isinstance(result, dict)
        return result

    def content_hash(self) -> str:
        """Stable content hash for audit and caching."""
        return content_hash(self.to_dict())


@dataclass(frozen=True, slots=True, kw_only=True)
class Tick:
    """One executed market trade print (Book II 5.7)."""

    exchange: str
    symbol: str
    occurred_at: Timestamp
    price: Price
    quantity: Quantity
    aggressor: OrderSide

    def __post_init__(self) -> None:
        ensure_not_empty(self.exchange, "exchange")
        ensure_symbol(self.symbol)

    def to_dict(self) -> dict[str, JsonValue]:
        """Canonical serialized form."""
        result = to_canonical(self)
        assert isinstance(result, dict)
        return result

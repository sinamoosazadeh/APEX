"""Context objects.

Book II 4.12/4.13: functions receive a context object instead of long
parameter lists. Contexts are immutable snapshots of ambient state.
"""

import uuid
from dataclasses import dataclass

from apex.core.enums import Environment, RunMode, Timeframe
from apex.core.exceptions import ValidationError
from apex.core.time.timestamp import Timestamp
from apex.core.types import Latency, Spread, Volatility
from apex.core.validation import ensure_not_empty, ensure_symbol


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionContext:
    """Identity of one operating session of the platform."""

    session_id: uuid.UUID
    environment: Environment
    run_mode: RunMode
    started_at: Timestamp
    config_hash: str

    def __post_init__(self) -> None:
        ensure_not_empty(self.config_hash, "config_hash")


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketContext:
    """Ambient market state for a symbol/timeframe (Book II 4.12).

    Regime and liquidity classification enums are owned by the Market
    Intelligence engines (Phase 4+); until those exist this context
    carries the measured quantities only.
    """

    symbol: str
    timeframe: Timeframe
    as_of: Timestamp
    volatility: Volatility | None = None
    spread: Spread | None = None

    def __post_init__(self) -> None:
        ensure_symbol(self.symbol)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionContext:
    """Ambient state for one execution attempt (Book II 4.13)."""

    execution_id: uuid.UUID
    correlation_id: uuid.UUID
    signal_id: uuid.UUID | None
    exchange: str
    symbol: str
    requested_at: Timestamp
    observed_latency: Latency | None = None

    def __post_init__(self) -> None:
        ensure_not_empty(self.exchange, "exchange")
        ensure_symbol(self.symbol)
        if self.exchange != self.exchange.lower():
            raise ValidationError(
                "exchange identifier must be lowercase",
                code="VAL-060",
                details={"exchange": self.exchange},
            )

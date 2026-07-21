"""Canonical enumerations.

Constitution 3.6: no string literal may appear in business logic; every
categorical concept is an enum. Book II 4.28: no raw booleans for status
concepts (health is a four-state enum, not ``healthy=True``).
"""

from enum import Enum, IntEnum, unique

from apex.core.constants import (
    MILLISECONDS_PER_DAY,
    MILLISECONDS_PER_HOUR,
    MILLISECONDS_PER_MINUTE,
)


@unique
class Environment(Enum):
    """Deployment environment (Book II 3.34 build layout)."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@unique
class RunMode(Enum):
    """Operating mode of the platform."""

    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"
    RESEARCH = "research"


@unique
class Direction(Enum):
    """Directional bias of a signal or position."""

    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@unique
class OrderSide(Enum):
    """Side of an order."""

    BUY = "buy"
    SELL = "sell"


@unique
class OrderType(Enum):
    """Order execution type."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


@unique
class TimeInForce(Enum):
    """Order time-in-force policy."""

    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
    POST_ONLY = "post_only"


@unique
class OrderStatus(Enum):
    """Exchange lifecycle status of an order."""

    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@unique
class PositionStatus(Enum):
    """Lifecycle status of a position."""

    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


@unique
class LiquidityRole(Enum):
    """Whether a fill added or removed book liquidity."""

    MAKER = "maker"
    TAKER = "taker"


@unique
class Timeframe(Enum):
    """Bar timeframe. Value is the canonical exchange notation."""

    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H2 = "2h"
    H4 = "4h"
    H6 = "6h"
    H12 = "12h"
    D1 = "1d"
    W1 = "1w"

    @property
    def duration_ms(self) -> int:
        """Length of one bar of this timeframe in milliseconds."""
        return _TIMEFRAME_DURATION_MS[self]


_TIMEFRAME_DURATION_MS: dict[Timeframe, int] = {
    Timeframe.M1: MILLISECONDS_PER_MINUTE,
    Timeframe.M3: 3 * MILLISECONDS_PER_MINUTE,
    Timeframe.M5: 5 * MILLISECONDS_PER_MINUTE,
    Timeframe.M15: 15 * MILLISECONDS_PER_MINUTE,
    Timeframe.M30: 30 * MILLISECONDS_PER_MINUTE,
    Timeframe.H1: MILLISECONDS_PER_HOUR,
    Timeframe.H2: 2 * MILLISECONDS_PER_HOUR,
    Timeframe.H4: 4 * MILLISECONDS_PER_HOUR,
    Timeframe.H6: 6 * MILLISECONDS_PER_HOUR,
    Timeframe.H12: 12 * MILLISECONDS_PER_HOUR,
    Timeframe.D1: MILLISECONDS_PER_DAY,
    Timeframe.W1: 7 * MILLISECONDS_PER_DAY,
}


@unique
class Lifecycle(Enum):
    """Universal object lifecycle (Book II 4.17)."""

    CREATED = "created"
    VALIDATED = "validated"
    ACTIVATED = "activated"
    RUNNING = "running"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    DELETED = "deleted"


@unique
class HealthState(Enum):
    """Component health (Book II 5.22). Never a raw boolean."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"

    @property
    def severity(self) -> int:
        """Numeric severity; higher is worse. Used for aggregation."""
        return _HEALTH_SEVERITY[self]


_HEALTH_SEVERITY: dict[HealthState, int] = {
    HealthState.HEALTHY: 0,
    HealthState.WARNING: 1,
    HealthState.CRITICAL: 2,
    HealthState.OFFLINE: 3,
}


@unique
class EventCategory(Enum):
    """Event taxonomy (Book II 5.28)."""

    MARKET = "market"
    SIGNAL = "signal"
    RISK = "risk"
    EXECUTION = "execution"
    PORTFOLIO = "portfolio"
    OPTIMIZER = "optimizer"
    RESEARCH = "research"
    HEALTH = "health"
    SYSTEM = "system"
    SECURITY = "security"


@unique
class EventPriority(IntEnum):
    """Event priority (Book II 5.29). Lower value dispatches first."""

    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@unique
class StabilityLevel(Enum):
    """Interface stability (Book II 5.36)."""

    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


@unique
class ClockSourceType(Enum):
    """Origin of time readings (Book II 4.15)."""

    SYSTEM = "system"
    MANUAL = "manual"
    REPLAY = "replay"
    SIMULATION = "simulation"
    EXCHANGE = "exchange"
    HISTORICAL = "historical"


@unique
class ModuleState(Enum):
    """Kernel module lifecycle state."""

    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@unique
class RiskMode(Enum):
    """Operating posture of the risk platform (Book II 5.10)."""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    HALTED = "halted"


@unique
class PluginKind(Enum):
    """Plugin taxonomy (Book II 3.23)."""

    INDICATOR = "indicator"
    FILTER = "filter"
    FEATURE = "feature"
    STRATEGY = "strategy"
    OPTIMIZER = "optimizer"
    EXECUTION_POLICY = "execution_policy"
    RISK_POLICY = "risk_policy"
    PORTFOLIO_POLICY = "portfolio_policy"
    EXCHANGE_CONNECTOR = "exchange_connector"
    REPORT_GENERATOR = "report_generator"
    SERVICE = "service"

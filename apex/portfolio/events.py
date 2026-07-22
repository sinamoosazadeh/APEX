"""Portfolio platform event catalog (Book II 29.7)."""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class PortfolioEvent(Enum):
    """Canonical portfolio-platform event types."""

    POSITION_OPENED = "portfolio.position.opened"
    POSITION_CLOSED = "portfolio.position.closed"
    SIGNAL_REJECTED = "portfolio.signal.rejected"
    REBUILT = "portfolio.rebuilt"
    FAILED = "portfolio.failed"


_PRIORITY: dict[PortfolioEvent, EventPriority] = {
    PortfolioEvent.POSITION_OPENED: EventPriority.HIGH,
    PortfolioEvent.POSITION_CLOSED: EventPriority.HIGH,
    PortfolioEvent.SIGNAL_REJECTED: EventPriority.MEDIUM,
    PortfolioEvent.REBUILT: EventPriority.MEDIUM,
    PortfolioEvent.FAILED: EventPriority.CRITICAL,
}


def portfolio_event(
    kind: PortfolioEvent,
    *,
    occurred_at: Timestamp,
    source: str,
    payload: EventPayload | None = None,
) -> Event:
    """Build a catalog event with its canonical category and priority."""
    return Event(
        event_type=kind.value,
        category=EventCategory.SYSTEM,
        priority=_PRIORITY[kind],
        occurred_at=occurred_at,
        source=source,
        payload=dict(payload or {}),
    )

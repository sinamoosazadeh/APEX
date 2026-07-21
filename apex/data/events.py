"""Market data event catalog.

Book II 29.7: engine layers declare their event types - never inline
strings at call sites. These are the facts the data platform publishes.
"""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class MarketEvent(Enum):
    """Canonical data-platform event types."""

    BARS_INGESTED = "market.bars.ingested"
    GAP_DETECTED = "market.gap.detected"
    INGESTION_FAILED = "market.ingestion.failed"


_PRIORITY: dict[MarketEvent, EventPriority] = {
    MarketEvent.BARS_INGESTED: EventPriority.MEDIUM,
    MarketEvent.GAP_DETECTED: EventPriority.HIGH,
    MarketEvent.INGESTION_FAILED: EventPriority.CRITICAL,
}


def market_event(
    kind: MarketEvent,
    *,
    occurred_at: Timestamp,
    source: str,
    payload: EventPayload | None = None,
) -> Event:
    """Build a catalog event with its canonical category and priority."""
    return Event(
        event_type=kind.value,
        category=EventCategory.MARKET,
        priority=_PRIORITY[kind],
        occurred_at=occurred_at,
        source=source,
        payload=dict(payload or {}),
    )

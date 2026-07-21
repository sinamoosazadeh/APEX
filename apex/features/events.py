"""Feature platform event catalog (Book II 29.7)."""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class FeatureEvent(Enum):
    """Canonical feature-platform event types."""

    FEATURES_COMPUTED = "market.features.computed"
    FEATURES_FAILED = "market.features.failed"


_PRIORITY: dict[FeatureEvent, EventPriority] = {
    FeatureEvent.FEATURES_COMPUTED: EventPriority.MEDIUM,
    FeatureEvent.FEATURES_FAILED: EventPriority.CRITICAL,
}


def feature_event(
    kind: FeatureEvent,
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

"""Probability platform event catalog (Book II 29.7)."""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class ProbabilityEvent(Enum):
    """Canonical probability-platform event types."""

    ASSESSED = "probability.assessed"
    FAILED = "probability.failed"


_PRIORITY: dict[ProbabilityEvent, EventPriority] = {
    ProbabilityEvent.ASSESSED: EventPriority.MEDIUM,
    ProbabilityEvent.FAILED: EventPriority.CRITICAL,
}


def probability_event(
    kind: ProbabilityEvent,
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

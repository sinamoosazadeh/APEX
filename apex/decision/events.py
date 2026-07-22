"""Decision platform event catalog (Book II 29.7)."""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class DecisionEvent(Enum):
    """Canonical decision-platform event types."""

    SIGNAL_FIRED = "decision.signal.fired"
    DECIDED = "decision.completed"
    FAILED = "decision.failed"


_PRIORITY: dict[DecisionEvent, EventPriority] = {
    DecisionEvent.SIGNAL_FIRED: EventPriority.HIGH,
    DecisionEvent.DECIDED: EventPriority.MEDIUM,
    DecisionEvent.FAILED: EventPriority.CRITICAL,
}


def decision_event(
    kind: DecisionEvent,
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

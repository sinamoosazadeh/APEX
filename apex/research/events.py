"""Research platform event catalog (Book II 29.7)."""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class ResearchEvent(Enum):
    """Canonical research-platform event types."""

    STUDIED = "research.study.completed"
    JOB_COMPLETED = "research.job.completed"
    VERSION_ACTIVATED = "research.version.activated"
    PROMOTION_EVALUATED = "research.promotion.evaluated"
    PROMOTED = "research.promotion.promoted"
    PROMOTION_REJECTED = "research.promotion.rejected"
    ROLLED_BACK = "research.version.rolled_back"
    FAILED = "research.failed"


_PRIORITY: dict[ResearchEvent, EventPriority] = {
    ResearchEvent.STUDIED: EventPriority.MEDIUM,
    ResearchEvent.JOB_COMPLETED: EventPriority.MEDIUM,
    ResearchEvent.VERSION_ACTIVATED: EventPriority.HIGH,
    ResearchEvent.PROMOTION_EVALUATED: EventPriority.MEDIUM,
    ResearchEvent.PROMOTED: EventPriority.HIGH,
    ResearchEvent.PROMOTION_REJECTED: EventPriority.HIGH,
    ResearchEvent.ROLLED_BACK: EventPriority.CRITICAL,
    ResearchEvent.FAILED: EventPriority.CRITICAL,
}


def research_event(
    kind: ResearchEvent,
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

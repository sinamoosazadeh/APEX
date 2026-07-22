"""Execution platform event catalog (Book II 29.7)."""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class ExecutionEvent(Enum):
    """Canonical execution-platform event types."""

    FILLED = "execution.order.filled"
    UNFILLED = "execution.order.unfilled"
    REJECTED = "execution.rejected"
    RECONCILED = "execution.reconciled"
    FAILED = "execution.failed"


_PRIORITY: dict[ExecutionEvent, EventPriority] = {
    ExecutionEvent.FILLED: EventPriority.HIGH,
    ExecutionEvent.UNFILLED: EventPriority.MEDIUM,
    ExecutionEvent.REJECTED: EventPriority.MEDIUM,
    ExecutionEvent.RECONCILED: EventPriority.MEDIUM,
    ExecutionEvent.FAILED: EventPriority.CRITICAL,
}


def execution_event(
    kind: ExecutionEvent,
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

"""Security platform event catalog (Book II 29.7)."""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class SecurityEvent(Enum):
    """Canonical security-platform event types."""

    SECRET_UPDATED = "security.secret.updated"
    CONFIG_SEALED = "security.config.sealed"
    PREFLIGHT_COMPLETED = "security.preflight.completed"


_PRIORITY: dict[SecurityEvent, EventPriority] = {
    SecurityEvent.SECRET_UPDATED: EventPriority.HIGH,
    SecurityEvent.CONFIG_SEALED: EventPriority.MEDIUM,
    SecurityEvent.PREFLIGHT_COMPLETED: EventPriority.HIGH,
}


def security_event(
    kind: SecurityEvent,
    *,
    occurred_at: Timestamp,
    source: str,
    payload: EventPayload | None = None,
) -> Event:
    """Build a catalog event with its canonical category and priority.

    Payloads carry secret NAMES at most - never values (13.7).
    """
    return Event(
        event_type=kind.value,
        category=EventCategory.SYSTEM,
        priority=_PRIORITY[kind],
        occurred_at=occurred_at,
        source=source,
        payload=dict(payload or {}),
    )

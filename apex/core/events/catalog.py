"""System event catalog.

Book II 29.7: events are defined before the bus. This catalog owns the
``system.*`` and ``health.*`` event types emitted by the kernel and
foundation. Engine layers register their own catalogs in their phases;
event types are never invented inline at call sites.
"""

from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class SystemEvent(Enum):
    """Canonical kernel/foundation event types."""

    KERNEL_BOOTING = "system.kernel.booting"
    KERNEL_STARTED = "system.kernel.started"
    KERNEL_STOPPING = "system.kernel.stopping"
    KERNEL_STOPPED = "system.kernel.stopped"
    CONFIG_LOADED = "system.config.loaded"
    MODULE_STARTED = "system.module.started"
    MODULE_STOPPED = "system.module.stopped"
    MODULE_FAILED = "system.module.failed"
    HEALTH_CHANGED = "health.state.changed"
    HANDLER_FAILED = "system.bus.handler_failed"


_CATEGORY: dict[SystemEvent, EventCategory] = {
    SystemEvent.KERNEL_BOOTING: EventCategory.SYSTEM,
    SystemEvent.KERNEL_STARTED: EventCategory.SYSTEM,
    SystemEvent.KERNEL_STOPPING: EventCategory.SYSTEM,
    SystemEvent.KERNEL_STOPPED: EventCategory.SYSTEM,
    SystemEvent.CONFIG_LOADED: EventCategory.SYSTEM,
    SystemEvent.MODULE_STARTED: EventCategory.SYSTEM,
    SystemEvent.MODULE_STOPPED: EventCategory.SYSTEM,
    SystemEvent.MODULE_FAILED: EventCategory.SYSTEM,
    SystemEvent.HEALTH_CHANGED: EventCategory.HEALTH,
    SystemEvent.HANDLER_FAILED: EventCategory.SYSTEM,
}

_PRIORITY: dict[SystemEvent, EventPriority] = {
    SystemEvent.KERNEL_BOOTING: EventPriority.HIGH,
    SystemEvent.KERNEL_STARTED: EventPriority.HIGH,
    SystemEvent.KERNEL_STOPPING: EventPriority.HIGH,
    SystemEvent.KERNEL_STOPPED: EventPriority.HIGH,
    SystemEvent.CONFIG_LOADED: EventPriority.MEDIUM,
    SystemEvent.MODULE_STARTED: EventPriority.MEDIUM,
    SystemEvent.MODULE_STOPPED: EventPriority.MEDIUM,
    SystemEvent.MODULE_FAILED: EventPriority.CRITICAL,
    SystemEvent.HEALTH_CHANGED: EventPriority.HIGH,
    SystemEvent.HANDLER_FAILED: EventPriority.CRITICAL,
}


def system_event(
    kind: SystemEvent,
    *,
    occurred_at: Timestamp,
    source: str,
    payload: EventPayload | None = None,
) -> Event:
    """Build a catalog event with its canonical category and priority."""
    return Event(
        event_type=kind.value,
        category=_CATEGORY[kind],
        priority=_PRIORITY[kind],
        occurred_at=occurred_at,
        source=source,
        payload=dict(payload or {}),
    )

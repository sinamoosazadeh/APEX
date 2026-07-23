"""Monitoring platform event catalog (Book II 29.7).

Alerts, incidents, kill-switch transitions, snapshots and the live
operational loop's lifecycle - defined here first, never inline at
call sites.
"""

import uuid
from enum import Enum, unique

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event, EventPayload
from apex.core.time.timestamp import Timestamp


@unique
class MonitoringEvent(Enum):
    """Canonical monitoring-platform event types."""

    ALERT_RAISED = "monitoring.alert.raised"
    INCIDENT_OPENED = "monitoring.incident.opened"
    KILL_SWITCH_CHANGED = "monitoring.killswitch.changed"
    SNAPSHOT_STORED = "monitoring.snapshot.stored"
    LOOP_STARTED = "operations.loop.started"
    LOOP_STOPPED = "operations.loop.stopped"
    BAR_PROCESSED = "operations.bar.processed"


_CATEGORY: dict[MonitoringEvent, EventCategory] = {
    MonitoringEvent.ALERT_RAISED: EventCategory.HEALTH,
    MonitoringEvent.INCIDENT_OPENED: EventCategory.HEALTH,
    MonitoringEvent.KILL_SWITCH_CHANGED: EventCategory.HEALTH,
    MonitoringEvent.SNAPSHOT_STORED: EventCategory.SYSTEM,
    MonitoringEvent.LOOP_STARTED: EventCategory.SYSTEM,
    MonitoringEvent.LOOP_STOPPED: EventCategory.SYSTEM,
    MonitoringEvent.BAR_PROCESSED: EventCategory.SYSTEM,
}

_PRIORITY: dict[MonitoringEvent, EventPriority] = {
    MonitoringEvent.ALERT_RAISED: EventPriority.HIGH,
    MonitoringEvent.INCIDENT_OPENED: EventPriority.CRITICAL,
    MonitoringEvent.KILL_SWITCH_CHANGED: EventPriority.CRITICAL,
    MonitoringEvent.SNAPSHOT_STORED: EventPriority.BACKGROUND,
    MonitoringEvent.LOOP_STARTED: EventPriority.MEDIUM,
    MonitoringEvent.LOOP_STOPPED: EventPriority.MEDIUM,
    MonitoringEvent.BAR_PROCESSED: EventPriority.BACKGROUND,
}


def monitoring_event(
    kind: MonitoringEvent,
    *,
    occurred_at: Timestamp,
    source: str,
    payload: EventPayload | None = None,
    trace_id: uuid.UUID | None = None,
) -> Event:
    """Build a catalog event with its canonical category and priority."""
    return Event(
        event_type=kind.value,
        category=_CATEGORY[kind],
        priority=_PRIORITY[kind],
        occurred_at=occurred_at,
        source=source,
        payload=dict(payload or {}),
        trace_id=trace_id,
    )

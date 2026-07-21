"""Event contract (Book II 5.12).

An event is an immutable record of a fact that happened. It carries
its id, type, category, priority, source, optional destination,
payload, trace/correlation identifiers and a schema version. The bus
assigns a monotonic ``sequence`` at journaling time, giving the whole
platform a deterministic total order of events (5.30).
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from apex.core.constants import CONTRACT_SCHEMA_VERSION, EVENT_TYPE_PATTERN
from apex.core.enums import EventCategory, EventPriority
from apex.core.exceptions import ValidationError
from apex.core.identity import new_entropy_id
from apex.core.serialization import JsonValue, content_hash, to_canonical
from apex.core.time.timestamp import Timestamp

type EventPayload = Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """Immutable event envelope.

    Attributes:
        event_id: unique identity of this event.
        event_type: dotted lowercase name, e.g. ``system.kernel.started``.
        category: taxonomy bucket (Book II 5.28).
        priority: dispatch priority class (Book II 5.29).
        occurred_at: instant the fact happened (from a Clock).
        source: dotted name of the producing component.
        destination: optional addressed consumer (broadcast when None).
        payload: canonical JSON-compatible fact data.
        trace_id: end-to-end trace identifier (5.14).
        correlation_id: causal chain identifier (5.13).
        causation_id: id of the event that directly caused this one.
        schema_version: event contract version (5.26).
        sequence: bus-assigned total order; None until journaled.
    """

    event_type: str
    category: EventCategory
    occurred_at: Timestamp
    source: str
    payload: EventPayload = field(default_factory=dict)
    priority: EventPriority = EventPriority.MEDIUM
    destination: str | None = None
    event_id: uuid.UUID = field(default_factory=new_entropy_id)
    trace_id: uuid.UUID | None = None
    correlation_id: uuid.UUID | None = None
    causation_id: uuid.UUID | None = None
    schema_version: int = CONTRACT_SCHEMA_VERSION
    sequence: int | None = None

    def __post_init__(self) -> None:
        if not EVENT_TYPE_PATTERN.match(self.event_type):
            raise ValidationError(
                "event_type must be dotted lowercase (e.g. 'system.kernel.started')",
                code="EVT-001",
                details={"event_type": self.event_type},
            )
        if not self.source:
            raise ValidationError("event source must not be empty", code="EVT-002")
        if self.schema_version < 1:
            raise ValidationError(
                "schema_version must be >= 1",
                code="EVT-003",
                details={"schema_version": self.schema_version},
            )
        if self.sequence is not None and self.sequence < 0:
            raise ValidationError(
                "sequence must be non-negative",
                code="EVT-004",
                details={"sequence": self.sequence},
            )
        # Force payload canonicalization early: an unserializable payload
        # must fail at construction, not at journaling time.
        to_canonical(dict(self.payload))

    def with_sequence(self, sequence: int) -> "Event":
        """Return a sequenced copy (assigned exactly once by the bus)."""
        if self.sequence is not None:
            raise ValidationError(
                "event is already sequenced",
                code="EVT-005",
                details={"event_id": str(self.event_id), "sequence": self.sequence},
            )
        return replace(self, sequence=sequence)

    def caused_event(
        self,
        *,
        event_type: str,
        category: EventCategory,
        occurred_at: Timestamp,
        source: str,
        payload: EventPayload | None = None,
        priority: EventPriority = EventPriority.MEDIUM,
    ) -> "Event":
        """Build a follow-up event inheriting trace and correlation."""
        return Event(
            event_type=event_type,
            category=category,
            occurred_at=occurred_at,
            source=source,
            payload=dict(payload or {}),
            priority=priority,
            trace_id=self.trace_id,
            correlation_id=self.correlation_id or self.event_id,
            causation_id=self.event_id,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        """Canonical serialized form (journal row)."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "category": self.category.value,
            "priority": int(self.priority),
            "occurred_at": self.occurred_at.epoch_ms,
            "source": self.source,
            "destination": self.destination,
            "payload": to_canonical(dict(self.payload)),
            "trace_id": str(self.trace_id) if self.trace_id else None,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "schema_version": self.schema_version,
            "sequence": self.sequence,
        }

    def content_hash(self) -> str:
        """Stable hash for audit and replay verification."""
        data = self.to_dict()
        data.pop("sequence")
        return content_hash(data)

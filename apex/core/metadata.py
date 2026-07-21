"""Object metadata.

Book II 4.9: every object carries metadata - origin module, trace and
correlation identifiers, session and execution context - so that any
signal, order or trade can be traced end-to-end across the platform
(Book II 5.13/5.14).
"""

import uuid
from dataclasses import dataclass, field, replace
from typing import Self


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    """Traceability and provenance attached to every domain object.

    Attributes:
        module: dotted name of the module that produced the object.
        trace_id: end-to-end trace across the whole system (5.14).
        correlation_id: shared by every object in one causal chain -
            signal -> risk -> order -> trade (5.13).
        causation_id: id of the object that directly caused this one.
        session_id: operating session the object belongs to.
        execution_id: execution run the object belongs to.
        tags: free-form classification labels (sorted, deduplicated).
    """

    module: str = "apex"
    trace_id: uuid.UUID | None = None
    correlation_id: uuid.UUID | None = None
    causation_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    execution_id: uuid.UUID | None = None
    tags: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        normalized = tuple(sorted(set(self.tags)))
        if normalized != self.tags:
            object.__setattr__(self, "tags", normalized)

    def with_correlation(self, correlation_id: uuid.UUID) -> Self:
        """Return a copy bound to a causal chain."""
        return replace(self, correlation_id=correlation_id)

    def with_causation(self, causation_id: uuid.UUID) -> Self:
        """Return a copy recording the direct cause."""
        return replace(self, causation_id=causation_id)

    def with_trace(self, trace_id: uuid.UUID) -> Self:
        """Return a copy bound to a trace."""
        return replace(self, trace_id=trace_id)

    def to_dict(self) -> dict[str, object]:
        """Serialize to plain data."""
        return {
            "module": self.module,
            "trace_id": str(self.trace_id) if self.trace_id else None,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "session_id": str(self.session_id) if self.session_id else None,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "tags": list(self.tags),
        }


EMPTY_METADATA = ObjectMetadata()

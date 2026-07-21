"""Core infrastructure interfaces.

All interaction between modules flows through versioned contracts and
official interfaces - no module may know another module's internals
(Book II 5.38). Interfaces are :class:`typing.Protocol` types so
implementations stay decoupled, and each declares a stability level
(Book II 5.36).
"""

import uuid
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol, runtime_checkable

from apex.core.enums import ClockSourceType, EventCategory, HealthState, StabilityLevel
from apex.core.events.event import Event
from apex.core.exceptions import ApexError
from apex.core.logging import LogFieldValue
from apex.core.time.timestamp import Timestamp
from apex.core.versioning import stability

type EventHandler = Callable[[Event], Awaitable[None]]


@runtime_checkable
@stability(StabilityLevel.STABLE)
class IClock(Protocol):
    """Time source (Book II 4.14). The only path to the current time."""

    @property
    def source(self) -> ClockSourceType:
        """Origin of this clock's readings."""
        ...

    def now(self) -> Timestamp:
        """Current instant, UTC."""
        ...


@runtime_checkable
@stability(StabilityLevel.STABLE)
class ILogger(Protocol):
    """Structured logger (Constitution 3.13, Book II 5.24)."""

    def debug(self, event: str, **fields: LogFieldValue) -> None:
        """Log a diagnostic event."""
        ...

    def info(self, event: str, **fields: LogFieldValue) -> None:
        """Log a routine operational event."""
        ...

    def warning(self, event: str, **fields: LogFieldValue) -> None:
        """Log a degraded-but-operational event."""
        ...

    def error(self, event: str, **fields: LogFieldValue) -> None:
        """Log a failure event."""
        ...

    def critical(self, event: str, **fields: LogFieldValue) -> None:
        """Log a platform-threatening event."""
        ...

    def failure(self, event: str, error: ApexError, **fields: LogFieldValue) -> None:
        """Log a structured platform error."""
        ...


@runtime_checkable
@stability(StabilityLevel.BETA)
class IEventBus(Protocol):
    """Deterministic event distribution (Book II 5.28-5.32)."""

    async def publish(self, event: Event) -> Event:
        """Journal then deliver an event; returns the sequenced event."""
        ...

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an exact event type."""
        ...

    def subscribe_category(self, category: EventCategory, handler: EventHandler) -> None:
        """Subscribe to every event of a category."""
        ...

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to every event on the bus."""
        ...


@runtime_checkable
@stability(StabilityLevel.EXPERIMENTAL)
class IStorage(Protocol):
    """Minimal persistence contract (Phase 3 provides implementations)."""

    async def write(self, namespace: str, key: str, payload: bytes) -> None:
        """Persist a payload under ``namespace/key``."""
        ...

    async def read(self, namespace: str, key: str) -> bytes | None:
        """Fetch a payload, or None when absent."""
        ...

    async def exists(self, namespace: str, key: str) -> bool:
        """Whether ``namespace/key`` holds a payload."""
        ...

    async def delete(self, namespace: str, key: str) -> bool:
        """Remove a payload; returns whether it existed."""
        ...


@runtime_checkable
@stability(StabilityLevel.EXPERIMENTAL)
class IRepository[T](Protocol):
    """Repository contract (Book II 5.17)."""

    async def save(self, item: T) -> None:
        """Persist a new object version."""
        ...

    async def get(self, object_id: uuid.UUID) -> T | None:
        """Fetch a specific object version by id."""
        ...

    async def exists(self, object_id: uuid.UUID) -> bool:
        """Whether an object version exists."""
        ...

    async def delete(self, object_id: uuid.UUID) -> bool:
        """Remove an object version; returns whether it existed."""
        ...

    async def search(self, lineage_id: uuid.UUID) -> Sequence[T]:
        """Return every version in a lineage, oldest first."""
        ...


@runtime_checkable
@stability(StabilityLevel.STABLE)
class IHealthCheck(Protocol):
    """Health reporting contract (Book II 5.22)."""

    def health(self) -> HealthState:
        """Current health of the component."""
        ...


@runtime_checkable
@stability(StabilityLevel.BETA)
class IModule(Protocol):
    """Kernel-managed module lifecycle contract (Book II 29.21/29.22)."""

    @property
    def name(self) -> str:
        """Unique module name."""
        ...

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Names of modules that must start before this one."""
        ...

    async def start(self) -> None:
        """Bring the module to its running state."""
        ...

    async def stop(self) -> None:
        """Release resources and stop cleanly."""
        ...

    def health(self) -> HealthState:
        """Current health of the module."""
        ...

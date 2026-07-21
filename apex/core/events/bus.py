"""In-process event bus.

Deterministic by construction (Book II 5.30): publishing journals the
event first (5.32), then delivers to subscribers strictly in
subscription order, awaiting each handler before the next. There is no
concurrent fan-out - determinism outranks throughput in the foundation;
a parallel dispatcher can be introduced later behind the same
:class:`~apex.core.contracts.interfaces.IEventBus` contract.

Handler failures are isolated: one failing subscriber never prevents
delivery to the rest. Failures are logged and surfaced as
``system.bus.handler_failed`` catalog events (never recursively).
"""

from collections.abc import Awaitable, Callable

from apex.core.enums import EventCategory
from apex.core.events.catalog import SystemEvent, system_event
from apex.core.events.event import Event
from apex.core.events.journal import EventJournal
from apex.core.exceptions import ApexError, EventError
from apex.core.logging import StructuredLogger
from apex.core.time.clock import Clock

type EventHandler = Callable[[Event], Awaitable[None]]

_SOURCE = "apex.core.events.bus"


class InProcessEventBus:
    """Single-process, deterministic, journaled event bus."""

    def __init__(
        self,
        *,
        journal: EventJournal,
        clock: Clock,
        logger: StructuredLogger,
        fail_fast: bool = False,
    ) -> None:
        self._journal = journal
        self._clock = clock
        self._logger = logger
        self._fail_fast = fail_fast
        self._by_type: dict[str, list[EventHandler]] = {}
        self._by_category: dict[EventCategory, list[EventHandler]] = {}
        self._global: list[EventHandler] = []
        self._closed = False

    @property
    def journal(self) -> EventJournal:
        """The journal backing this bus."""
        return self._journal

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an exact event type."""
        self._ensure_open()
        self._by_type.setdefault(event_type, []).append(handler)

    def subscribe_category(self, category: EventCategory, handler: EventHandler) -> None:
        """Subscribe to every event of one category."""
        self._ensure_open()
        self._by_category.setdefault(category, []).append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to every event on the bus."""
        self._ensure_open()
        self._global.append(handler)

    async def publish(self, event: Event) -> Event:
        """Journal, then deliver an event. Returns the sequenced event."""
        self._ensure_open()
        sequenced = self._journal.append(event)
        self._logger.debug(
            "event_published",
            event_type=sequenced.event_type,
            sequence=sequenced.sequence,
            category=sequenced.category.value,
        )
        for handler in self._handlers_for(sequenced):
            await self._deliver(handler, sequenced)
        return sequenced

    def close(self) -> None:
        """Refuse further publishes and subscriptions (shutdown)."""
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise EventError("event bus is closed", code="EVT-020")

    def _handlers_for(self, event: Event) -> list[EventHandler]:
        handlers: list[EventHandler] = []
        handlers.extend(self._by_type.get(event.event_type, ()))
        handlers.extend(self._by_category.get(event.category, ()))
        handlers.extend(self._global)
        return handlers

    async def _deliver(self, handler: EventHandler, event: Event) -> None:
        try:
            await handler(event)
        except ApexError as error:
            await self._on_handler_failure(handler, event, error)
        except Exception as error:
            wrapped = EventError(
                "unhandled exception in event handler",
                code="EVT-021",
                details={"reason": str(error), "exception": type(error).__name__},
            )
            await self._on_handler_failure(handler, event, wrapped)

    async def _on_handler_failure(
        self,
        handler: EventHandler,
        event: Event,
        error: ApexError,
    ) -> None:
        handler_name = getattr(handler, "__qualname__", repr(handler))
        self._logger.failure(
            "event_handler_failed",
            error,
            event_type=event.event_type,
            sequence=event.sequence,
            handler=handler_name,
        )
        if self._fail_fast:
            raise error
        if event.event_type == SystemEvent.HANDLER_FAILED.value:
            return  # never recurse on failure-of-failure
        failure_event = system_event(
            SystemEvent.HANDLER_FAILED,
            occurred_at=self._clock.now(),
            source=_SOURCE,
            payload={
                "failed_event_type": event.event_type,
                "failed_sequence": event.sequence,
                "handler": handler_name,
                "error_code": error.code,
                "error_message": error.message,
            },
        )
        sequenced = self._journal.append(failure_event)
        for observer in self._handlers_for(sequenced):
            try:
                await observer(sequenced)
            except Exception:
                self._logger.error(
                    "failure_observer_raised",
                    event_type=sequenced.event_type,
                    handler=getattr(observer, "__qualname__", repr(observer)),
                )

"""Telemetry collector (Book I 10.4: the universal telemetry bus).

The observability layer's sole ingestion path: engines never write to
the monitoring store directly. Two feeds converge here:

- **Event telemetry**: subscribed to the platform bus, every journaled
  event becomes counters (``events.total``, per-type counts) and error
  telemetry (``errors.total``) when it signals a failure - the bus is
  already the deterministic record of everything that happened.
- **Direct instrumentation**: the operational loop and services record
  stage latencies, operation counts and heartbeats through the
  collector's methods.

Samples buffer in memory and flush in batches; timestamps come from
event occurrence or the injected clock - never ambient time.
"""

from typing import Final

from apex.core.enums import EventPriority
from apex.core.events.event import Event
from apex.core.logging import StructuredLogger
from apex.core.time.clock import Clock
from apex.monitoring.records import MetricSample
from apex.monitoring.store import SqliteMonitoringRepository

METRIC_EVENTS_TOTAL: Final[str] = "events.total"
METRIC_ERRORS_TOTAL: Final[str] = "errors.total"
METRIC_OPERATIONS_TOTAL: Final[str] = "operations.total"
METRIC_STREAM_DISCONNECTS: Final[str] = "events.market.stream.disconnected"

# Event types that always count as errors regardless of priority.
_ERROR_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "market.ingestion.failed",
        "market.stream.disconnected",
        "decision.failed",
        "probability.failed",
        "portfolio.failed",
        "execution.failed",
        "research.failed",
        "system.bus.handler_failed",
        "system.module.failed",
    }
)


class TelemetryCollector:
    """Buffers telemetry and folds bus events into metrics."""

    def __init__(
        self,
        *,
        store: SqliteMonitoringRepository,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._store = store
        self._clock = clock
        self._logger = logger
        self._buffer: list[MetricSample] = []
        self._events_seen = 0
        self._errors_seen = 0

    @property
    def events_seen(self) -> int:
        """Bus events observed this session."""
        return self._events_seen

    @property
    def errors_seen(self) -> int:
        """Error events observed this session."""
        return self._errors_seen

    # --- Direct instrumentation -----------------------------------------------------

    def metric(
        self, name: str, value: float, *, tags: dict[str, str] | None = None
    ) -> None:
        """Buffer one metric sample at the current instant."""
        self._buffer.append(
            MetricSample(
                name=name,
                value=value,
                recorded_at=self._clock.now(),
                tags=dict(tags or {}),
            )
        )

    def operation(self, *, tags: dict[str, str] | None = None) -> None:
        """Count one completed operation (the SLO denominator)."""
        self.metric(METRIC_OPERATIONS_TOTAL, 1.0, tags=tags)

    def error(self, *, tags: dict[str, str] | None = None) -> None:
        """Count one failure (the SLO numerator)."""
        self._errors_seen += 1
        self.metric(METRIC_ERRORS_TOTAL, 1.0, tags=tags)

    async def beat(self, component: str) -> None:
        """Record one component heartbeat (Book I 10.8)."""
        await self._store.beat(component, self._clock.now())

    # --- Event telemetry ---------------------------------------------------------------

    async def observe_event(self, event: Event) -> None:
        """Bus subscriber: fold one journaled event into telemetry."""
        self._events_seen += 1
        occurred = event.occurred_at
        self._buffer.append(
            MetricSample(
                name=METRIC_EVENTS_TOTAL,
                value=1.0,
                recorded_at=occurred,
                tags={"type": event.event_type},
            )
        )
        self._buffer.append(
            MetricSample(
                name=f"events.{event.event_type}",
                value=1.0,
                recorded_at=occurred,
                tags={},
            )
        )
        if self._is_error(event):
            self._errors_seen += 1
            self._buffer.append(
                MetricSample(
                    name=METRIC_ERRORS_TOTAL,
                    value=1.0,
                    recorded_at=occurred,
                    tags={"type": event.event_type, "source": event.source},
                )
            )

    @staticmethod
    def _is_error(event: Event) -> bool:
        if event.event_type in _ERROR_EVENT_TYPES:
            return True
        return (
            event.priority is EventPriority.CRITICAL
            and event.event_type.endswith(".failed")
        )

    # --- Flush -----------------------------------------------------------------------

    async def flush(self) -> int:
        """Persist the buffered samples; returns the count written."""
        if not self._buffer:
            return 0
        batch = self._buffer
        self._buffer = []
        written = await self._store.insert_metrics(batch)
        self._logger.debug("telemetry_flushed", samples=written)
        return written

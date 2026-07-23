"""Telemetry collector: event folding, error classification, flush."""

import asyncio
from pathlib import Path

from apex.core.enums import EventCategory, EventPriority
from apex.core.events.event import Event
from apex.core.time.clock import ManualClock
from apex.monitoring.collector import (
    METRIC_ERRORS_TOTAL,
    METRIC_EVENTS_TOTAL,
    METRIC_OPERATIONS_TOTAL,
    TelemetryCollector,
)

from tests.conftest import T0
from tests.unit.monitoring.support import logger, store_at


def event(event_type: str, *, priority: EventPriority = EventPriority.MEDIUM) -> Event:
    return Event(
        event_type=event_type,
        category=EventCategory.SYSTEM,
        priority=priority,
        occurred_at=T0,
        source="tests",
    )


class TestCollector:
    def test_events_fold_into_metrics(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            collector = TelemetryCollector(
                store=store, clock=ManualClock(T0), logger=logger()
            )
            await collector.observe_event(event("market.bar.closed"))
            await collector.observe_event(event("execution.failed"))
            written = await collector.flush()
            assert written == 5  # 2x(total+per-type) + 1 error
            assert await store.count_metric(METRIC_EVENTS_TOTAL, since_ms=0) == 2
            assert await store.count_metric(METRIC_ERRORS_TOTAL, since_ms=0) == 1
            assert (
                await store.count_metric("events.market.bar.closed", since_ms=0) == 1
            )
            assert collector.events_seen == 2
            assert collector.errors_seen == 1
            await store.close()

        asyncio.run(scenario())

    def test_critical_failed_events_count_as_errors(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            collector = TelemetryCollector(
                store=store, clock=ManualClock(T0), logger=logger()
            )
            await collector.observe_event(
                event("probability.failed", priority=EventPriority.CRITICAL)
            )
            await collector.observe_event(
                event("research.study.completed", priority=EventPriority.CRITICAL)
            )
            await collector.flush()
            assert await store.count_metric(METRIC_ERRORS_TOTAL, since_ms=0) == 1
            await store.close()

        asyncio.run(scenario())

    def test_direct_instrumentation(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            collector = TelemetryCollector(
                store=store, clock=ManualClock(T0), logger=logger()
            )
            collector.metric("loop.bar.total_ms", 42.0, tags={"symbol": "BTCUSDT"})
            collector.operation()
            collector.error()
            await collector.flush()
            assert await store.count_metric("loop.bar.total_ms", since_ms=0) == 1
            assert await store.count_metric(METRIC_OPERATIONS_TOTAL, since_ms=0) == 1
            assert await store.count_metric(METRIC_ERRORS_TOTAL, since_ms=0) == 1
            await collector.beat("operations_loop")
            beats = await store.heartbeats()
            assert beats[0].component == "operations_loop"
            assert await collector.flush() == 0  # buffer drained
            await store.close()

        asyncio.run(scenario())

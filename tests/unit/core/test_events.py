"""Event platform: contract, journal, deterministic bus."""

import asyncio
import io

import pytest
from apex.core.enums import ClockSourceType, EventCategory, EventPriority
from apex.core.events.bus import InProcessEventBus
from apex.core.events.catalog import SystemEvent, system_event
from apex.core.events.event import Event
from apex.core.events.journal import EventJournal
from apex.core.exceptions import EventError, SerializationError, ValidationError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp

T0 = Timestamp(epoch_ms=1_750_000_000_000)


def make_event(event_type: str = "market.bar.closed", **payload: str | int) -> Event:
    return Event(
        event_type=event_type,
        category=EventCategory.MARKET,
        occurred_at=T0,
        source="tests",
        payload=dict(payload),
    )


def make_bus(*, fail_fast: bool = False, capacity: int = 100) -> InProcessEventBus:
    clock = ManualClock(T0, source=ClockSourceType.MANUAL)
    factory = LoggerFactory(
        clock=clock,
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return InProcessEventBus(
        journal=EventJournal(capacity=capacity),
        clock=clock,
        logger=factory.get("test.bus"),
        fail_fast=fail_fast,
    )


class TestEventContract:
    def test_type_format_enforced(self) -> None:
        with pytest.raises(ValidationError):
            make_event("BadType")
        with pytest.raises(ValidationError):
            make_event("single")

    def test_payload_must_be_serializable(self) -> None:
        with pytest.raises(SerializationError):
            Event(
                event_type="market.bar.closed",
                category=EventCategory.MARKET,
                occurred_at=T0,
                source="tests",
                payload={"bad": object()},  # type: ignore[dict-item]
            )

    def test_sequence_assigned_once(self) -> None:
        event = make_event().with_sequence(4)
        with pytest.raises(ValidationError):
            event.with_sequence(5)

    def test_caused_event_inherits_chain(self) -> None:
        cause = make_event()
        effect = cause.caused_event(
            event_type="signal.candidate.created",
            category=EventCategory.SIGNAL,
            occurred_at=T0.add_ms(1),
            source="tests",
        )
        assert effect.causation_id == cause.event_id
        assert effect.correlation_id == cause.event_id

    def test_content_hash_ignores_sequence(self) -> None:
        event = make_event(symbol="BTCUSDT")
        assert event.content_hash() == event.with_sequence(9).content_hash()

    def test_catalog_events_carry_canonical_priority(self) -> None:
        booting = system_event(SystemEvent.KERNEL_BOOTING, occurred_at=T0, source="tests")
        assert booting.priority is EventPriority.HIGH
        assert booting.category is EventCategory.SYSTEM


class TestJournal:
    def test_sequencing_is_monotonic(self) -> None:
        journal = EventJournal(capacity=10)
        first = journal.append(make_event())
        second = journal.append(make_event())
        assert (first.sequence, second.sequence) == (0, 1)

    def test_capacity_evicts_oldest_but_keeps_sequence(self) -> None:
        journal = EventJournal(capacity=2)
        for _ in range(5):
            journal.append(make_event())
        retained = list(journal.replay())
        assert [e.sequence for e in retained] == [3, 4]
        assert journal.total_appended == 5
        assert journal.next_sequence == 5

    def test_replay_from_sequence(self) -> None:
        journal = EventJournal(capacity=10)
        for _ in range(4):
            journal.append(make_event())
        assert [e.sequence for e in journal.replay(from_sequence=2)] == [2, 3]

    def test_invalid_capacity(self) -> None:
        with pytest.raises(EventError):
            EventJournal(capacity=0)


class TestBus:
    def test_delivery_order_is_deterministic(self) -> None:
        bus = make_bus()
        seen: list[str] = []

        async def scenario() -> None:
            async def type_handler(event: Event) -> None:
                seen.append("by_type")

            async def category_handler(event: Event) -> None:
                seen.append("by_category")

            async def global_handler(event: Event) -> None:
                seen.append("global")

            bus.subscribe("market.bar.closed", type_handler)
            bus.subscribe_category(EventCategory.MARKET, category_handler)
            bus.subscribe_all(global_handler)
            await bus.publish(make_event())

        asyncio.run(scenario())
        assert seen == ["by_type", "by_category", "global"]

    def test_journaled_before_delivery(self) -> None:
        bus = make_bus()
        observed_journal_size: list[int] = []

        async def scenario() -> None:
            async def handler(event: Event) -> None:
                observed_journal_size.append(len(bus.journal))

            bus.subscribe("market.bar.closed", handler)
            await bus.publish(make_event())

        asyncio.run(scenario())
        assert observed_journal_size == [1]

    def test_handler_failure_is_isolated(self) -> None:
        bus = make_bus()
        seen: list[str] = []

        async def scenario() -> None:
            async def failing(event: Event) -> None:
                raise RuntimeError("boom")

            async def surviving(event: Event) -> None:
                seen.append(event.event_type)

            bus.subscribe("market.bar.closed", failing)
            bus.subscribe("market.bar.closed", surviving)
            await bus.publish(make_event())

        asyncio.run(scenario())
        assert "market.bar.closed" in seen
        failure_types = [e.event_type for e in bus.journal.replay()]
        assert SystemEvent.HANDLER_FAILED.value in failure_types

    def test_fail_fast_propagates(self) -> None:
        bus = make_bus(fail_fast=True)

        async def scenario() -> None:
            async def failing(event: Event) -> None:
                raise RuntimeError("boom")

            bus.subscribe("market.bar.closed", failing)
            await bus.publish(make_event())

        with pytest.raises(EventError):
            asyncio.run(scenario())

    def test_closed_bus_refuses_publish(self) -> None:
        bus = make_bus()
        bus.close()
        with pytest.raises(EventError):
            asyncio.run(bus.publish(make_event()))

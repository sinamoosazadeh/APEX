"""Storage platform: key/value store, bar repository, event archive."""

import asyncio
import io
from pathlib import Path

import pytest
from apex.core.enums import EventCategory, HealthState, Timeframe
from apex.core.events.bus import InProcessEventBus
from apex.core.events.event import Event
from apex.core.events.journal import EventJournal
from apex.core.exceptions import StorageError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp
from apex.storage.archive import ARCHIVE_NAMESPACE, EventArchiveModule
from apex.storage.bars import SqliteBarRepository
from apex.storage.sqlite import SqliteKeyValueStorage

from tests.conftest import T0, make_bar


def make_logger(name: str = "test") -> object:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get(name)


class TestKeyValueStorage:
    def test_roundtrip_and_overwrite(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            storage = SqliteKeyValueStorage(database_path=tmp_path / "kv.sqlite")
            await storage.open()
            await storage.write("ns", "alpha", b"one")
            await storage.write("ns", "alpha", b"two")  # upsert
            assert await storage.read("ns", "alpha") == b"two"
            assert await storage.exists("ns", "alpha")
            assert await storage.read("other", "alpha") is None
            assert await storage.delete("ns", "alpha")
            assert not await storage.delete("ns", "alpha")
            await storage.close()

        asyncio.run(scenario())

    def test_survives_reopen(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            path = tmp_path / "kv.sqlite"
            first = SqliteKeyValueStorage(database_path=path)
            await first.open()
            await first.write("ns", "key", b"durable")
            await first.close()
            second = SqliteKeyValueStorage(database_path=path)
            await second.open()
            assert await second.read("ns", "key") == b"durable"
            await second.close()

        asyncio.run(scenario())

    def test_not_open_rejected(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            storage = SqliteKeyValueStorage(database_path=tmp_path / "kv.sqlite")
            with pytest.raises(StorageError) as excinfo:
                await storage.write("ns", "key", b"x")
            assert excinfo.value.code == "STO-002"

        asyncio.run(scenario())


class TestBarRepository:
    def test_upsert_is_idempotent(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            repo = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
            await repo.open()
            bars = [
                make_bar(open_time=T0),
                make_bar(open_time=T0.add_ms(Timeframe.H1.duration_ms)),
            ]
            assert await repo.upsert(bars) == 2
            assert await repo.upsert(bars) == 2  # overwrite, not duplicate
            assert await repo.count("toobit", "BTCUSDT", Timeframe.H1) == 2
            await repo.close()

        asyncio.run(scenario())

    def test_range_query_and_roundtrip(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            repo = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
            await repo.open()
            step = Timeframe.H1.duration_ms
            bars = [make_bar(open_time=T0.add_ms(i * step)) for i in range(5)]
            await repo.upsert(bars)
            window = await repo.get_range(
                "toobit",
                "BTCUSDT",
                Timeframe.H1,
                start=T0.add_ms(step),
                end=T0.add_ms(4 * step),
            )
            assert [b.open_time.epoch_ms for b in window] == [
                T0.add_ms(step).epoch_ms,
                T0.add_ms(2 * step).epoch_ms,
                T0.add_ms(3 * step).epoch_ms,
            ]
            # Full value-type round trip.
            assert window[0].open.value == bars[1].open.value
            assert window[0].quality.value == bars[1].quality.value
            assert window[0].content_hash() == bars[1].content_hash()
            await repo.close()

        asyncio.run(scenario())

    def test_closed_only_filter_and_latest(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            repo = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
            await repo.open()
            step = Timeframe.H1.duration_ms
            closed = make_bar(open_time=T0)
            forming = make_bar(open_time=T0.add_ms(step), is_closed=False)
            await repo.upsert([closed, forming])
            only_closed = await repo.get_range(
                "toobit",
                "BTCUSDT",
                Timeframe.H1,
                start=T0,
                end=T0.add_ms(10 * step),
                closed_only=True,
            )
            assert len(only_closed) == 1 and only_closed[0].is_closed
            latest = await repo.latest_open_time("toobit", "BTCUSDT", Timeframe.H1)
            assert latest == forming.open_time
            assert await repo.latest_open_time("toobit", "XRPUSDT", Timeframe.H1) is None
            await repo.close()

        asyncio.run(scenario())


class TestEventArchive:
    def make_stack(
        self, tmp_path: Path
    ) -> tuple[SqliteKeyValueStorage, InProcessEventBus, EventJournal, EventArchiveModule]:
        journal = EventJournal(capacity=100)
        clock = ManualClock(T0)
        bus = InProcessEventBus(
            journal=journal,
            clock=clock,
            logger=make_logger("bus"),  # type: ignore[arg-type]
            fail_fast=False,
        )
        storage = SqliteKeyValueStorage(database_path=tmp_path / "kv.sqlite")
        module = EventArchiveModule(
            storage=storage,
            bus=bus,
            journal=journal,
            logger=make_logger("archive"),  # type: ignore[arg-type]
        )
        return storage, bus, journal, module

    def make_event(self, event_type: str = "system.test.ping") -> Event:
        return Event(
            event_type=event_type,
            category=EventCategory.SYSTEM,
            occurred_at=T0,
            source="tests",
        )

    def test_catches_up_then_follows(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            storage, bus, _journal, module = self.make_stack(tmp_path)
            await storage.open()
            # Events published before the module started (boot events).
            await bus.publish(self.make_event())
            await bus.publish(self.make_event())
            await module.start()
            assert module.archived_count == 2  # caught up from journal
            await bus.publish(self.make_event())
            assert module.archived_count == 3
            assert await storage.exists(ARCHIVE_NAMESPACE, f"{0:020d}")
            assert await storage.exists(ARCHIVE_NAMESPACE, f"{2:020d}")
            assert module.health() is HealthState.HEALTHY
            await module.stop()
            assert module.health() is HealthState.OFFLINE
            await storage.close()

        asyncio.run(scenario())

    def test_archive_rows_are_canonical_json(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            storage, bus, _journal, module = self.make_stack(tmp_path)
            await storage.open()
            await module.start()
            published = await bus.publish(self.make_event("system.test.payload"))
            raw = await storage.read(ARCHIVE_NAMESPACE, f"{published.sequence:020d}")
            assert raw is not None
            assert b'"event_type":"system.test.payload"' in raw
            await storage.close()

        asyncio.run(scenario())


class TestTimestampGuard:
    def test_repo_paths_use_utc_timestamps(self) -> None:
        # Regression guard: natural keys are epoch-ms integers.
        bar = make_bar()
        assert isinstance(bar.open_time, Timestamp)
        assert bar.natural_key().endswith(str(bar.open_time.epoch_ms))

"""Quality inspection, ingestion pipeline, replay gateway."""

import asyncio
import io
from collections.abc import Sequence
from pathlib import Path

from apex.core.enums import ClockSourceType, EventCategory, Timeframe
from apex.core.events.bus import InProcessEventBus
from apex.core.events.event import Event
from apex.core.events.journal import EventJournal
from apex.core.exceptions import MarketError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp
from apex.data.events import MarketEvent
from apex.data.pipeline import BarIngestionPipeline
from apex.data.quality import BarQualityInspector
from apex.data.replay import ReplayMarketDataGateway
from apex.domain.market import Bar, Tick
from apex.storage.bars import SqliteBarRepository

from tests.conftest import T0, make_bar

H1_MS = Timeframe.H1.duration_ms


def make_logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.pipeline")


def make_bus() -> InProcessEventBus:
    return InProcessEventBus(
        journal=EventJournal(capacity=1000),
        clock=ManualClock(T0, source=ClockSourceType.SIMULATION),
        logger=make_logger(),
        fail_fast=True,
    )


class FakeGateway:
    """Deterministic in-memory market data gateway."""

    def __init__(self, bars: list[Bar] | None = None, *, error: MarketError | None = None):
        self._bars = bars or []
        self._error = error

    @property
    def exchange_id(self) -> str:
        return "toobit"

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> Result[Sequence[Bar]]:
        if self._error is not None:
            return Result.failure(self._error)
        window = [
            bar
            for bar in self._bars
            if start.epoch_ms <= bar.open_time.epoch_ms < end.epoch_ms
        ]
        return Result.success(tuple(window))

    async def fetch_ticks(
        self,
        symbol: str,
        *,
        start: Timestamp,
        limit: int,
    ) -> Result[Sequence[Tick]]:
        return Result.success(())


class TestQualityInspector:
    def test_gap_detection_and_penalty(self) -> None:
        inspector = BarQualityInspector(gap_penalty=0.25, forming_bar_quality=0.5)
        series = [
            make_bar(open_time=T0),
            make_bar(open_time=T0.add_ms(H1_MS)),
            make_bar(open_time=T0.add_ms(4 * H1_MS)),  # 2 bars missing
        ]
        scored, report = inspector.inspect(series)
        assert report is not None
        assert report.gap_count == 1
        assert report.missing_bars == 2
        assert scored[0].quality.value == 1.0
        assert scored[1].quality.value == 1.0
        assert scored[2].quality.value == 0.75  # penalized: follows the gap

    def test_forming_bar_scored_down(self) -> None:
        inspector = BarQualityInspector(gap_penalty=0.25, forming_bar_quality=0.5)
        series = [
            make_bar(open_time=T0),
            make_bar(open_time=T0.add_ms(H1_MS), is_closed=False),
        ]
        scored, report = inspector.inspect(series)
        assert report is not None and report.gap_count == 0
        assert scored[1].quality.value == 0.5

    def test_empty_series(self) -> None:
        inspector = BarQualityInspector(gap_penalty=0.25, forming_bar_quality=0.5)
        scored, report = inspector.inspect([])
        assert scored == [] and report is None


class TestIngestionPipeline:
    def make_pipeline(
        self, tmp_path: Path, gateway: FakeGateway
    ) -> tuple[BarIngestionPipeline, SqliteBarRepository, InProcessEventBus]:
        repository = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
        bus = make_bus()
        pipeline = BarIngestionPipeline(
            gateway=gateway,
            repository=repository,
            inspector=BarQualityInspector(gap_penalty=0.25, forming_bar_quality=0.5),
            bus=bus,
            clock=ManualClock(T0.add_ms(10 * H1_MS), source=ClockSourceType.SIMULATION),
            logger=make_logger(),
        )
        return pipeline, repository, bus

    def test_full_ingestion_run(self, tmp_path: Path) -> None:
        bars = [
            make_bar(open_time=T0),
            make_bar(open_time=T0.add_ms(H1_MS)),
            make_bar(open_time=T0.add_ms(3 * H1_MS)),  # gap before this one
        ]

        async def scenario() -> None:
            pipeline, repository, bus = self.make_pipeline(tmp_path, FakeGateway(bars))
            await repository.open()
            result = await pipeline.ingest(
                "BTCUSDT", Timeframe.H1, start=T0, end=T0.add_ms(5 * H1_MS)
            )
            summary = result.unwrap()
            assert summary.fetched == 3
            assert summary.stored == 3
            assert summary.closed_bars == 3
            assert summary.gap_count == 1
            assert summary.missing_bars == 1
            assert await repository.count("toobit", "BTCUSDT", Timeframe.H1) == 3
            event_types = [e.event_type for e in bus.journal.replay()]
            assert MarketEvent.BARS_INGESTED.value in event_types
            assert MarketEvent.GAP_DETECTED.value in event_types
            # Gap-adjacent bar persisted with its penalty applied.
            stored = await repository.get_range(
                "toobit",
                "BTCUSDT",
                Timeframe.H1,
                start=T0.add_ms(3 * H1_MS),
                end=T0.add_ms(4 * H1_MS),
            )
            assert stored[0].quality.value == 0.75
            await repository.close()

        asyncio.run(scenario())

    def test_failure_publishes_ingestion_failed(self, tmp_path: Path) -> None:
        error = MarketError("Toobit API error", code="MKT-008")

        async def scenario() -> None:
            pipeline, repository, bus = self.make_pipeline(tmp_path, FakeGateway(error=error))
            await repository.open()
            result = await pipeline.ingest(
                "BTCUSDT", Timeframe.H1, start=T0, end=T0.add_ms(H1_MS)
            )
            assert not result.ok
            event_types = [e.event_type for e in bus.journal.replay()]
            assert MarketEvent.INGESTION_FAILED.value in event_types
            assert await repository.count("toobit", "BTCUSDT", Timeframe.H1) == 0
            await repository.close()

        asyncio.run(scenario())

    def test_reingestion_is_idempotent(self, tmp_path: Path) -> None:
        bars = [make_bar(open_time=T0), make_bar(open_time=T0.add_ms(H1_MS))]

        async def scenario() -> None:
            pipeline, repository, _ = self.make_pipeline(tmp_path, FakeGateway(bars))
            await repository.open()
            first = await pipeline.ingest(
                "BTCUSDT", Timeframe.H1, start=T0, end=T0.add_ms(2 * H1_MS)
            )
            second = await pipeline.ingest(
                "BTCUSDT", Timeframe.H1, start=T0, end=T0.add_ms(2 * H1_MS)
            )
            assert first.unwrap().stored == 2
            assert second.unwrap().stored == 2
            assert await repository.count("toobit", "BTCUSDT", Timeframe.H1) == 2
            await repository.close()

        asyncio.run(scenario())


class TestReplayGateway:
    def test_serves_only_confirmed_stored_bars(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            repository = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
            await repository.open()
            await repository.upsert(
                [
                    make_bar(open_time=T0),
                    make_bar(open_time=T0.add_ms(H1_MS), is_closed=False),
                ]
            )
            replay = ReplayMarketDataGateway(
                source_exchange="toobit",
                repository=repository,
                logger=make_logger(),
            )
            result = await replay.fetch_bars(
                "BTCUSDT", Timeframe.H1, start=T0, end=T0.add_ms(10 * H1_MS)
            )
            bars = result.unwrap()
            assert len(bars) == 1 and bars[0].is_closed
            assert replay.exchange_id == "toobit"
            await repository.close()

        asyncio.run(scenario())

    def test_tick_replay_unavailable(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            repository = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
            await repository.open()
            replay = ReplayMarketDataGateway(
                source_exchange="toobit",
                repository=repository,
                logger=make_logger(),
            )
            result = await replay.fetch_ticks("BTCUSDT", start=T0, limit=10)
            assert not result.ok
            assert result.error is not None and result.error.code == "DAT-020"
            await repository.close()

        asyncio.run(scenario())


class TestEventContractCoverage:
    def test_market_events_are_market_category(self) -> None:
        from apex.data.events import market_event

        event: Event = market_event(
            MarketEvent.BARS_INGESTED, occurred_at=T0, source="tests"
        )
        assert event.category is EventCategory.MARKET

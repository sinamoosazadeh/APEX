"""Phase 3 completion: tick storage, catch-up, WS translation, streaming."""

import asyncio
import io
import json
from collections.abc import AsyncIterator, Sequence
from decimal import Decimal
from pathlib import Path

import pytest
from apex.core.config import MarketConfig
from apex.core.enums import ClockSourceType, EventCategory, OrderSide, Timeframe
from apex.core.events.bus import InProcessEventBus
from apex.core.events.journal import EventJournal
from apex.core.exceptions import DataError, MarketError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.result import Result
from apex.core.serialization import JsonValue
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp
from apex.core.types import Quantity
from apex.data.catchup import CatchUpService
from apex.data.events import MarketEvent
from apex.data.pipeline import BarIngestionPipeline
from apex.data.quality import BarQualityInspector
from apex.data.replay import ReplayMarketDataGateway
from apex.data.streaming import MarketStreamService
from apex.data.toobit.stream import StreamSubscription, ToobitStreamClient
from apex.data.toobit.translator import ToobitTranslator
from apex.domain.market import Bar, Tick
from apex.storage.bars import SqliteBarRepository
from apex.storage.ticks import SqliteTickRepository

from tests.conftest import T0, make_bar, price

H1_MS = Timeframe.H1.duration_ms


def make_logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.streaming")


def make_tick(ms_offset: int = 0, *, trade_id: str | None = "42") -> Tick:
    return Tick(
        exchange="toobit",
        symbol="BTCUSDT",
        occurred_at=T0.add_ms(ms_offset),
        price=price("100.5"),
        quantity=Quantity(Decimal("0.25")),
        aggressor=OrderSide.BUY,
        trade_id=trade_id,
    )


class TestTickRepository:
    def test_dedup_on_trade_id(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            repo = SqliteTickRepository(database_path=tmp_path / "ticks.sqlite")
            await repo.open()
            first = await repo.upsert([make_tick(0), make_tick(1000, trade_id="43")])
            duplicate = await repo.upsert([make_tick(0)])  # same trade id
            assert first == 2
            assert duplicate == 0
            assert await repo.count("toobit", "BTCUSDT") == 2
            await repo.close()

        asyncio.run(scenario())

    def test_synthesized_key_dedup(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            repo = SqliteTickRepository(database_path=tmp_path / "ticks.sqlite")
            await repo.open()
            anonymous = make_tick(0, trade_id=None)
            assert await repo.upsert([anonymous, anonymous]) == 1
            await repo.close()

        asyncio.run(scenario())

    def test_range_query_roundtrip(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            repo = SqliteTickRepository(database_path=tmp_path / "ticks.sqlite")
            await repo.open()
            await repo.upsert(
                [make_tick(i * 1000, trade_id=str(i)) for i in range(5)]
            )
            window = await repo.get_range(
                "toobit",
                "BTCUSDT",
                start=T0.add_ms(1000),
                end=T0.add_ms(4000),
                limit=10,
            )
            assert [t.occurred_at.epoch_ms for t in window] == [
                T0.add_ms(1000).epoch_ms,
                T0.add_ms(2000).epoch_ms,
                T0.add_ms(3000).epoch_ms,
            ]
            assert window[0].trade_id == "1"
            assert window[0].price.value == Decimal("100.5")
            await repo.close()

        asyncio.run(scenario())


def make_market_config(history_bars: int = 5) -> MarketConfig:
    return MarketConfig(
        symbols=("BTCUSDT",),
        timeframes=(Timeframe.H1,),
        history_bars=history_bars,
        gap_penalty=0.25,
        forming_bar_quality=0.5,
        stream_forming_flush_ms=1,
        stream_reconnect_backoff_ms=0,
        stream_max_reconnects=2,
    )


class WindowGateway:
    """Serves a fixed bar universe within any requested window."""

    def __init__(self, bars: list[Bar]) -> None:
        self._bars = bars
        self.requests: list[tuple[int, int]] = []

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
        self.requests.append((start.epoch_ms, end.epoch_ms))
        window = [
            b for b in self._bars if start.epoch_ms <= b.open_time.epoch_ms < end.epoch_ms
        ]
        return Result.success(tuple(window))

    async def fetch_ticks(
        self, symbol: str, *, start: Timestamp, limit: int
    ) -> Result[Sequence[Tick]]:
        return Result.success(())


class TestCatchUp:
    def make_service(
        self, tmp_path: Path, gateway: WindowGateway, *, now: Timestamp
    ) -> tuple[CatchUpService, SqliteBarRepository]:
        repository = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
        bus = InProcessEventBus(
            journal=EventJournal(capacity=1000),
            clock=ManualClock(now, source=ClockSourceType.SIMULATION),
            logger=make_logger(),
            fail_fast=True,
        )
        pipeline = BarIngestionPipeline(
            gateway=gateway,
            repository=repository,
            inspector=BarQualityInspector(gap_penalty=0.25, forming_bar_quality=0.5),
            bus=bus,
            clock=ManualClock(now, source=ClockSourceType.SIMULATION),
            logger=make_logger(),
        )
        service = CatchUpService(
            pipeline=pipeline,
            repository=repository,
            config=make_market_config(),
            exchange_id="toobit",
            clock=ManualClock(now, source=ClockSourceType.SIMULATION),
            logger=make_logger(),
        )
        return service, repository

    def test_empty_series_backfills_history(self, tmp_path: Path) -> None:
        now = T0.add_ms(10 * H1_MS)
        universe = [make_bar(open_time=T0.add_ms(i * H1_MS)) for i in range(11)]
        gateway = WindowGateway(universe)

        async def scenario() -> None:
            service, repository = self.make_service(tmp_path, gateway, now=now)
            await repository.open()
            report = await service.run_once()
            assert report.failed == 0
            # Window is [aligned_end - 5h, aligned_end); the universe bars
            # are offset from hour alignment, so exactly 5 of them fall in.
            assert report.bars_stored == 5
            await repository.close()

        asyncio.run(scenario())

    def test_existing_series_resumes_from_latest(self, tmp_path: Path) -> None:
        now = T0.add_ms(10 * H1_MS)
        universe = [make_bar(open_time=T0.add_ms(i * H1_MS)) for i in range(11)]
        gateway = WindowGateway(universe)

        async def scenario() -> None:
            service, repository = self.make_service(tmp_path, gateway, now=now)
            await repository.open()
            # Bars up to hour 7 already stored (hour 7 possibly forming then).
            await repository.upsert(universe[:8])
            report = await service.run_once()
            assert report.failed == 0
            start_ms, _ = gateway.requests[0]
            assert start_ms == T0.add_ms(7 * H1_MS).epoch_ms  # re-fetch latest
            assert await repository.count("toobit", "BTCUSDT", Timeframe.H1) == 11
            await repository.close()

        asyncio.run(scenario())


class TestStreamTranslator:
    def test_kline_stream_message(self) -> None:
        translator = ToobitTranslator()
        message: dict[str, JsonValue] = {
            "symbol": "BTCUSDT",
            "topic": "kline",
            "params": {"klineType": "1h", "binary": "false"},
            "data": [
                {"t": T0.epoch_ms, "o": "100", "h": "110", "l": "95", "c": "105", "v": "12.5"}
            ],
            "f": False,
        }
        bars = translator.stream_klines_to_bars(
            message, Timeframe.H1, now=T0.add_ms(H1_MS // 2)
        )
        assert len(bars) == 1
        assert bars[0].close.value == Decimal("105")
        assert not bars[0].is_closed  # still forming

    def test_trade_stream_message_semantics(self) -> None:
        translator = ToobitTranslator()
        message: dict[str, JsonValue] = {
            "symbol": "BTCUSDT",
            "topic": "trade",
            "data": [
                {"v": "112", "t": T0.epoch_ms, "p": "399", "q": "1", "m": False},
                {"v": "113", "t": T0.add_ms(10).epoch_ms, "p": "400", "q": "2", "m": True},
            ],
        }
        ticks = translator.stream_trades_to_ticks(message)
        assert ticks[0].trade_id == "112"
        assert ticks[0].aggressor is OrderSide.SELL  # m=false -> sell
        assert ticks[1].aggressor is OrderSide.BUY  # m=true -> buy

    def test_missing_data_rejected(self) -> None:
        with pytest.raises(DataError) as excinfo:
            ToobitTranslator().stream_trades_to_ticks({"symbol": "BTCUSDT"})
        assert excinfo.value.code == "DAT-022"


class ScriptedConnection:
    """Fake WebSocket connection driven by a message script."""

    def __init__(self, frames: list[str], *, fail_after: bool = False) -> None:
        self._frames = list(frames)
        self._fail_after = fail_after
        self.sent: list[str] = []
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str:
        if self._frames:
            return self._frames.pop(0)
        if self._fail_after:
            raise ConnectionError("scripted disconnect")
        raise TimeoutError  # nothing more to say

    async def close(self) -> None:
        self.closed = True


class TestStreamClient:
    def make_client(self, connection: ScriptedConnection) -> ToobitStreamClient:
        async def connect(url: str) -> ScriptedConnection:
            return connection

        return ToobitStreamClient(
            url="wss://stream.example/quote/ws/v1",
            clock=ManualClock(T0),
            logger=make_logger(),
            ping_interval_ms=60_000,
            recv_timeout_ms=10,
            connect=connect,
        )

    def test_subscribes_and_yields_data(self) -> None:
        data_frame = json.dumps(
            {"symbol": "BTCUSDT", "topic": "trade", "data": [], "f": True}
        )
        connection = ScriptedConnection(
            [json.dumps({"pong": 1}), data_frame], fail_after=True
        )
        client = self.make_client(connection)

        async def scenario() -> list[dict[str, JsonValue]]:
            received: list[dict[str, JsonValue]] = []
            with pytest.raises(MarketError) as excinfo:
                async for message in client.stream(
                    (StreamSubscription(symbols=("BTCUSDT",), topic="trade"),)
                ):
                    received.append(message)
            assert excinfo.value.code == "MKT-020"
            return received

        received = asyncio.run(scenario())
        assert len(received) == 1  # pong filtered, data yielded
        subscription_frame = json.loads(connection.sent[0])
        assert subscription_frame["topic"] == "trade"
        assert subscription_frame["event"] == "sub"
        assert connection.closed

    def test_requires_subscriptions(self) -> None:
        client = self.make_client(ScriptedConnection([]))

        async def scenario() -> None:
            with pytest.raises(MarketError) as excinfo:
                async for _ in client.stream(()):
                    pass
            assert excinfo.value.code == "MKT-021"

        asyncio.run(scenario())


class FakeStreamClient:
    """Scripted replacement for ToobitStreamClient in service tests."""

    def __init__(self, scripts: list[list[dict[str, JsonValue]] | MarketError]) -> None:
        self._scripts = list(scripts)
        self.subscription_sets: list[tuple[StreamSubscription, ...]] = []

    async def stream(
        self, subscriptions: tuple[StreamSubscription, ...]
    ) -> AsyncIterator[dict[str, JsonValue]]:
        self.subscription_sets.append(subscriptions)
        script = self._scripts.pop(0)
        if isinstance(script, MarketError):
            raise script
        for message in script:
            yield message


class TestMarketStreamService:
    def make_service(
        self,
        tmp_path: Path,
        client: FakeStreamClient,
        clock: ManualClock,
    ) -> tuple[MarketStreamService, SqliteBarRepository, SqliteTickRepository, InProcessEventBus]:
        bars = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
        ticks = SqliteTickRepository(database_path=tmp_path / "ticks.sqlite")
        bus = InProcessEventBus(
            journal=EventJournal(capacity=1000),
            clock=clock,
            logger=make_logger(),
            fail_fast=True,
        )
        service = MarketStreamService(
            client=client,  # type: ignore[arg-type]
            translator=ToobitTranslator(),
            bar_repository=bars,
            tick_repository=ticks,
            bus=bus,
            clock=clock,
            logger=make_logger(),
            symbols=("BTCUSDT",),
            timeframes=(Timeframe.H1, Timeframe.M3),  # M3 not streamable
            forming_flush_ms=1,
            reconnect_backoff_ms=0,
            max_reconnects=2,
        )
        return service, bars, ticks, bus

    @staticmethod
    def kline_message(open_ms: int, close: str) -> dict[str, JsonValue]:
        return {
            "symbol": "BTCUSDT",
            "topic": "kline",
            "params": {"klineType": "1h"},
            "data": [
                {"t": open_ms, "o": "100", "h": "110", "l": "95", "c": close, "v": "1"}
            ],
        }

    @staticmethod
    def trade_message(trade_id: int) -> dict[str, JsonValue]:
        return {
            "symbol": "BTCUSDT",
            "topic": "trade",
            "data": [
                {"v": str(trade_id), "t": T0.epoch_ms, "p": "100", "q": "1", "m": True}
            ],
        }

    def test_close_transition_and_ticks(self, tmp_path: Path) -> None:
        clock = ManualClock(T0.add_ms(H1_MS + 1000), source=ClockSourceType.SIMULATION)
        script: list[list[dict[str, JsonValue]] | MarketError] = [
            [
                self.kline_message(T0.epoch_ms, "105"),  # already-closed hour
                self.kline_message(T0.add_ms(H1_MS).epoch_ms, "106"),  # forming
                self.trade_message(1),
                self.trade_message(2),
                self.trade_message(2),  # duplicate trade id
            ]
        ]
        client = FakeStreamClient(script)

        async def scenario() -> None:
            service, bars, ticks, bus = self.make_service(tmp_path, client, clock)
            await bars.open()
            await ticks.open()
            stats = await service.run(duration_ms=60_000)
            assert stats.bars_closed == 1
            assert stats.ticks_stored == 2  # duplicate deduped
            stored = await bars.get_range(
                "toobit",
                "BTCUSDT",
                Timeframe.H1,
                start=T0,
                end=T0.add_ms(3 * H1_MS),
            )
            assert len(stored) == 2
            assert stored[0].is_closed and not stored[1].is_closed
            event_types = [e.event_type for e in bus.journal.replay()]
            assert MarketEvent.STREAM_CONNECTED.value in event_types
            assert MarketEvent.BAR_CLOSED.value in event_types
            assert MarketEvent.TICKS_INGESTED.value in event_types
            # Only the streamable timeframe is subscribed (plus trades).
            topics = [s.topic for s in client.subscription_sets[0]]
            assert topics == ["trade", "kline_1h"]
            await ticks.close()
            await bars.close()

        asyncio.run(scenario())

    def test_reconnects_after_drop(self, tmp_path: Path) -> None:
        clock = ManualClock(T0.add_ms(H1_MS), source=ClockSourceType.SIMULATION)
        script: list[list[dict[str, JsonValue]] | MarketError] = [
            MarketError("websocket connection lost", code="MKT-020"),
            [self.trade_message(7)],
        ]
        client = FakeStreamClient(script)

        async def scenario() -> None:
            service, bars, ticks, bus = self.make_service(tmp_path, client, clock)
            await bars.open()
            await ticks.open()
            stats = await service.run(duration_ms=60_000)
            assert stats.reconnects == 1
            assert stats.ticks_stored == 1
            event_types = [e.event_type for e in bus.journal.replay()]
            assert MarketEvent.STREAM_DISCONNECTED.value in event_types
            await ticks.close()
            await bars.close()

        asyncio.run(scenario())


class TestReplayTicks:
    def test_replay_serves_stored_ticks(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            bars = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
            ticks = SqliteTickRepository(database_path=tmp_path / "ticks.sqlite")
            await bars.open()
            await ticks.open()
            await ticks.upsert([make_tick(0), make_tick(5000, trade_id="43")])
            replay = ReplayMarketDataGateway(
                source_exchange="toobit",
                repository=bars,
                tick_repository=ticks,
                logger=make_logger(),
            )
            result = await replay.fetch_ticks("BTCUSDT", start=T0.add_ms(1), limit=10)
            served = result.unwrap()
            assert len(served) == 1 and served[0].trade_id == "43"
            await ticks.close()
            await bars.close()

        asyncio.run(scenario())

    def test_replay_without_tick_storage_fails_cleanly(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            bars = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
            await bars.open()
            replay = ReplayMarketDataGateway(
                source_exchange="toobit",
                repository=bars,
                logger=make_logger(),
            )
            result = await replay.fetch_ticks("BTCUSDT", start=T0, limit=10)
            assert not result.ok
            assert result.error is not None and result.error.code == "DAT-020"
            await bars.close()

        asyncio.run(scenario())


class TestEventCategories:
    def test_new_events_are_market_category(self) -> None:
        from apex.data.events import market_event

        for kind in (
            MarketEvent.BAR_CLOSED,
            MarketEvent.TICKS_INGESTED,
            MarketEvent.STREAM_CONNECTED,
            MarketEvent.STREAM_DISCONNECTED,
        ):
            event = market_event(kind, occurred_at=T0, source="tests")
            assert event.category is EventCategory.MARKET

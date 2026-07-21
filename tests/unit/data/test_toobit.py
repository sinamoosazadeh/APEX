"""Toobit connector: translator and REST client (no network)."""

import asyncio
import io
from decimal import Decimal

import httpx
import pytest
from apex.core.enums import ClockSourceType, OrderSide, Timeframe
from apex.core.exceptions import DataError, MarketError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.serialization import JsonValue
from apex.core.time.clock import ManualClock
from apex.data.toobit.client import ToobitRestClient
from apex.data.toobit.gateway import ToobitMarketDataGateway
from apex.data.toobit.translator import ToobitTranslator, interval_for

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms


def make_logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.toobit")


def kline(open_ms: int, *, close: str = "105", trades: int = 42) -> list[JsonValue]:
    return [
        open_ms,
        "100",
        "110",
        "95",
        close,
        "1234.5",
        open_ms + H1_MS - 1,
        "130000.0",
        trades,
        "600.0",
        "63000.0",
    ]


class TestTranslator:
    def test_kline_to_bar(self) -> None:
        translator = ToobitTranslator()
        now = T0.add_ms(2 * H1_MS)
        bar = translator.to_bar("BTCUSDT", Timeframe.H1, kline(T0.epoch_ms), now=now)
        assert bar.exchange == "toobit"
        assert bar.open.value == Decimal("100")
        assert bar.close.value == Decimal("105")
        assert bar.volume.value == Decimal("1234.5")
        assert bar.trade_count == 42
        assert bar.is_closed  # close time is in the past

    def test_forming_bar_detection(self) -> None:
        translator = ToobitTranslator()
        now = T0.add_ms(H1_MS // 2)  # halfway through the bar
        bar = translator.to_bar("BTCUSDT", Timeframe.H1, kline(T0.epoch_ms), now=now)
        assert not bar.is_closed

    def test_batch_is_sorted(self) -> None:
        translator = ToobitTranslator()
        now = T0.add_ms(10 * H1_MS)
        klines = [kline(T0.add_ms(H1_MS).epoch_ms), kline(T0.epoch_ms)]
        bars = translator.to_bars("BTCUSDT", Timeframe.H1, klines, now=now)
        assert [b.open_time.epoch_ms for b in bars] == [
            T0.epoch_ms,
            T0.add_ms(H1_MS).epoch_ms,
        ]

    def test_short_kline_rejected(self) -> None:
        with pytest.raises(DataError) as excinfo:
            ToobitTranslator().to_bar("BTCUSDT", Timeframe.H1, [T0.epoch_ms, "1"], now=T0)
        assert excinfo.value.code == "DAT-013"

    def test_bad_number_rejected(self) -> None:
        bad = kline(T0.epoch_ms)
        bad[1] = "not-a-price"
        with pytest.raises(DataError) as excinfo:
            ToobitTranslator().to_bar("BTCUSDT", Timeframe.H1, bad, now=T0)
        assert excinfo.value.code == "DAT-016"

    def test_tick_aggressor_semantics(self) -> None:
        translator = ToobitTranslator()
        seller_aggresses = translator.to_tick(
            "BTCUSDT", {"p": "100.5", "q": "0.25", "t": T0.epoch_ms, "ibm": True}
        )
        buyer_aggresses = translator.to_tick(
            "BTCUSDT", {"p": "100.5", "q": "0.25", "t": T0.epoch_ms, "ibm": False}
        )
        assert seller_aggresses.aggressor is OrderSide.SELL
        assert buyer_aggresses.aggressor is OrderSide.BUY

    def test_tick_missing_field_rejected(self) -> None:
        with pytest.raises(DataError) as excinfo:
            ToobitTranslator().to_tick("BTCUSDT", {"p": "1", "q": "1"})
        assert excinfo.value.code == "DAT-014"

    def test_interval_notation_matches_enum(self) -> None:
        assert interval_for(Timeframe.H1) == "1h"
        assert interval_for(Timeframe.M15) == "15m"


def make_client(
    handler: httpx.MockTransport,
    *,
    max_retries: int = 2,
) -> ToobitRestClient:
    return ToobitRestClient(
        base_url="https://api.toobit.example",
        request_timeout_ms=1000,
        max_retries=max_retries,
        retry_backoff_ms=0,
        logger=make_logger(),
        transport=handler,
    )


class TestRestClient:
    def test_get_klines_success(self) -> None:
        seen: list[httpx.URL] = []

        def handle(request: httpx.Request) -> httpx.Response:
            seen.append(request.url)
            return httpx.Response(200, json=[kline(T0.epoch_ms)])

        async def scenario() -> None:
            client = make_client(httpx.MockTransport(handle))
            await client.open()
            rows = await client.get_klines(
                "BTCUSDT", "1h", start_ms=T0.epoch_ms, end_ms=T0.epoch_ms + H1_MS, limit=100
            )
            assert len(rows) == 1
            await client.close()

        asyncio.run(scenario())
        assert seen[0].path == "/quote/v1/klines"
        assert seen[0].params["symbol"] == "BTCUSDT"
        assert seen[0].params["interval"] == "1h"
        assert seen[0].params["limit"] == "100"

    def test_retries_on_rate_limit_then_succeeds(self) -> None:
        attempts: list[int] = []

        def handle(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            if len(attempts) < 3:
                return httpx.Response(429, json={"msg": "slow down"})
            return httpx.Response(200, json=[])

        async def scenario() -> None:
            client = make_client(httpx.MockTransport(handle), max_retries=3)
            await client.open()
            rows = await client.get_klines(
                "BTCUSDT", "1h", start_ms=0, end_ms=H1_MS, limit=10
            )
            assert rows == []
            await client.close()

        asyncio.run(scenario())
        assert len(attempts) == 3

    def test_exhausted_retries_raise(self) -> None:
        def handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        async def scenario() -> None:
            client = make_client(httpx.MockTransport(handle), max_retries=1)
            await client.open()
            try:
                with pytest.raises(MarketError) as excinfo:
                    await client.get_klines("BTCUSDT", "1h", start_ms=0, end_ms=1, limit=10)
                assert excinfo.value.code == "MKT-006"
            finally:
                await client.close()

        asyncio.run(scenario())

    def test_api_error_envelope_raises(self) -> None:
        def handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"code": -1121, "msg": "Invalid symbol."})

        async def scenario() -> None:
            client = make_client(httpx.MockTransport(handle))
            await client.open()
            try:
                with pytest.raises(MarketError) as excinfo:
                    await client.get_klines("NOPEUSDT", "1h", start_ms=0, end_ms=1, limit=10)
                assert excinfo.value.code == "MKT-008"
                assert excinfo.value.details["api_code"] == "-1121"
            finally:
                await client.close()

        asyncio.run(scenario())

    def test_limit_bounds_enforced(self) -> None:
        async def scenario() -> None:
            client = make_client(httpx.MockTransport(lambda r: httpx.Response(200, json=[])))
            await client.open()
            try:
                with pytest.raises(MarketError) as excinfo:
                    await client.get_klines("BTCUSDT", "1h", start_ms=0, end_ms=1, limit=1001)
                assert excinfo.value.code == "MKT-002"
            finally:
                await client.close()

        asyncio.run(scenario())

    def test_unopened_client_rejected(self) -> None:
        async def scenario() -> None:
            client = make_client(httpx.MockTransport(lambda r: httpx.Response(200, json=[])))
            with pytest.raises(MarketError) as excinfo:
                await client.get_trades("BTCUSDT", limit=10)
            assert excinfo.value.code == "MKT-009"

        asyncio.run(scenario())


class TestGateway:
    def test_paginates_and_filters_window(self) -> None:
        pages: list[tuple[str, str]] = []

        def handle(request: httpx.Request) -> httpx.Response:
            start = int(request.url.params["startTime"])
            end = int(request.url.params["endTime"])
            limit = int(request.url.params["limit"])
            pages.append((request.url.params["startTime"], request.url.params["endTime"]))
            rows: list[list[JsonValue]] = []
            cursor = start
            while cursor < end and len(rows) < limit:
                rows.append(kline(cursor))
                cursor += H1_MS
            return httpx.Response(200, json=rows)

        async def scenario() -> None:
            clock = ManualClock(
                T0.add_ms(100 * H1_MS), source=ClockSourceType.SIMULATION
            )
            client = ToobitRestClient(
                base_url="https://api.toobit.example",
                request_timeout_ms=1000,
                max_retries=0,
                retry_backoff_ms=0,
                logger=make_logger(),
                transport=httpx.MockTransport(handle),
            )
            gateway = ToobitMarketDataGateway(
                client=client,
                translator=ToobitTranslator(),
                clock=clock,
                logger=make_logger(),
                kline_page_limit=3,  # force pagination
            )
            await gateway.open()
            result = await gateway.fetch_bars(
                "BTCUSDT",
                Timeframe.H1,
                start=T0,
                end=T0.add_ms(7 * H1_MS),
            )
            bars = result.unwrap()
            assert len(bars) == 7
            assert all(bar.is_closed for bar in bars)
            assert [b.open_time.epoch_ms for b in bars] == [
                T0.add_ms(i * H1_MS).epoch_ms for i in range(7)
            ]
            await gateway.close()

        asyncio.run(scenario())
        assert len(pages) >= 3  # 7 bars at page size 3

    def test_fetch_failure_becomes_result(self) -> None:
        def handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"code": -1121, "msg": "Invalid symbol."})

        async def scenario() -> None:
            client = make_client(httpx.MockTransport(handle))
            gateway = ToobitMarketDataGateway(
                client=client,
                translator=ToobitTranslator(),
                clock=ManualClock(T0),
                logger=make_logger(),
                kline_page_limit=100,
            )
            await gateway.open()
            result = await gateway.fetch_bars(
                "NOPEUSDT", Timeframe.H1, start=T0, end=T0.add_ms(H1_MS)
            )
            assert not result.ok
            assert result.error is not None and result.error.code == "MKT-008"
            await gateway.close()

        asyncio.run(scenario())

    def test_fetch_ticks_filters_and_warns(self) -> None:
        trades = [
            {"p": "100", "q": "1", "t": T0.epoch_ms - 1000, "ibm": False},
            {"p": "101", "q": "1", "t": T0.epoch_ms + 1000, "ibm": True},
        ]

        def handle(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/quote/v1/trades"
            return httpx.Response(200, json=trades)

        async def scenario() -> None:
            client = make_client(httpx.MockTransport(handle))
            gateway = ToobitMarketDataGateway(
                client=client,
                translator=ToobitTranslator(),
                clock=ManualClock(T0),
                logger=make_logger(),
                kline_page_limit=100,
            )
            await gateway.open()
            result = await gateway.fetch_ticks("BTCUSDT", start=T0, limit=500)
            ticks = result.unwrap()
            assert len(ticks) == 1  # older trade filtered out
            assert ticks[0].aggressor is OrderSide.SELL
            assert result.warnings  # capped at Toobit's 60-trade window
            await gateway.close()

        asyncio.run(scenario())

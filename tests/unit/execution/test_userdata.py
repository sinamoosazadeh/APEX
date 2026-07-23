"""User-data stream: parsing, listenKey lifecycle, engine consultation."""

import asyncio
import io
import json
from typing import Final

import httpx
from apex.core.enums import OrderStatus
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.serialization import JsonValue
from apex.core.time.clock import ManualClock
from apex.execution.trading.client import ToobitTradingClient, TradingCredentials
from apex.execution.trading.userdata import (
    EVENT_KEY_EXPIRING,
    EVENT_ORDER,
    UserDataFeed,
    parse_user_data,
)

from tests.conftest import T0

_KEY: Final[str] = "test-listen-key"


def logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.userdata")


class TestParsing:
    def test_order_report_array_parses_status_and_ids(self) -> None:
        frame: JsonValue = [
            {
                "e": "contractExecutionReport",
                "E": 1499405658658,
                "s": "BTC-SWAP-USDT",
                "c": 1000087761,
                "S": "BUY",
                "X": "FILLED",
                "i": 4293153,
            }
        ]
        events = parse_user_data(frame)
        assert len(events) == 1
        event = events[0]
        assert event.event_type == EVENT_ORDER
        assert event.status is OrderStatus.FILLED
        assert event.order_id == "4293153"
        assert event.client_order_id == "1000087761"

    def test_ticket_info_carries_order_ids_without_status(self) -> None:
        frame: JsonValue = [
            {
                "e": "ticketInfo",
                "E": "1668693440976",
                "s": "BTC-SWAP-USDT",
                "o": "1291488620167835136",
                "c": "1668693440093",
            }
        ]
        events = parse_user_data(frame)
        assert events[0].order_id == "1291488620167835136"
        assert events[0].status is None

    def test_balance_event_letters_do_not_leak(self) -> None:
        # ``f``/``a`` mean different things per event type (Book VII);
        # a balance frame must never produce order ids or statuses.
        frame: JsonValue = [
            {
                "e": "outboundContractAccountInfo",
                "E": 1564745798939,
                "T": True,
                "B": [{"a": "LTC", "f": "17366.18538083", "l": "0.0"}],
            }
        ]
        events = parse_user_data(frame)
        assert events[0].order_id is None
        assert events[0].status is None

    def test_events_order_by_event_time(self) -> None:
        frame: JsonValue = [
            {"e": "ticketInfo", "E": "200", "o": "2"},
            {"e": "ticketInfo", "E": "100", "o": "1"},
        ]
        events = parse_user_data(frame)
        assert [event.order_id for event in events] == ["1", "2"]

    def test_expiry_event_parses(self) -> None:
        frame: JsonValue = {
            "eventTime": 1767536100360,
            "eventType": "listenKeyWillExpire",
            "listenKey": "zUe",
        }
        events = parse_user_data(frame)
        assert events[0].event_type == EVENT_KEY_EXPIRING


class _ScriptedConnection:
    """A WsConnection yielding scripted frames, then pending forever."""

    def __init__(self, frames: list[object]) -> None:
        self._frames = list(frames)
        self.closed = False

    async def send(self, message: str) -> None:
        return

    async def recv(self) -> str:
        if self._frames:
            return json.dumps(self._frames.pop(0))
        await asyncio.sleep(3600)
        raise AssertionError("unreachable")

    async def close(self) -> None:
        self.closed = True


class _Recorder:
    """Records listenKey REST calls made through the trading client."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        return httpx.Response(200, json={"listenKey": _KEY})


def trading_client(recorder: _Recorder, clock: ManualClock) -> ToobitTradingClient:
    return ToobitTradingClient(
        base_url="https://api.toobit.test",
        request_timeout_ms=2_000,
        recv_window_ms=5_000,
        max_retries=0,
        retry_backoff_ms=1,
        clock=clock,
        logger=logger(),
        credentials=TradingCredentials(api_key="k", api_secret="s"),
        transport=httpx.MockTransport(recorder.handler),
    )


def feed_with(
    recorder: _Recorder,
    clock: ManualClock,
    connection: _ScriptedConnection,
    *,
    keepalive_ms: int = 60_000,
) -> tuple[UserDataFeed, ToobitTradingClient]:
    client = trading_client(recorder, clock)

    async def connect(url: str) -> _ScriptedConnection:
        assert url.endswith(f"/api/v1/ws/{_KEY}")
        return connection

    feed = UserDataFeed(
        client=client,
        ws_base_url="wss://stream.toobit.test",
        keepalive_interval_ms=keepalive_ms,
        recv_timeout_ms=50,
        clock=clock,
        logger=logger(),
        connect=connect,
    )
    return feed, client


class TestFeedLifecycle:
    def test_start_folds_pushed_status_and_stop_closes_key(self) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            recorder = _Recorder()
            connection = _ScriptedConnection(
                [
                    [
                        {
                            "e": "contractExecutionReport",
                            "E": 1,
                            "i": 42,
                            "c": "cid-1",
                            "X": "FILLED",
                        }
                    ]
                ]
            )
            feed, client = feed_with(recorder, clock, connection)
            await client.open()
            await feed.start()
            for _ in range(50):
                if feed.status_for(order_id="42") is not None:
                    break
                await asyncio.sleep(0.01)
            assert feed.status_for(order_id="42") is OrderStatus.FILLED
            assert feed.status_for(client_order_id="cid-1") is OrderStatus.FILLED
            assert feed.status_for(order_id="404") is None
            await feed.stop()
            assert feed.running is False
            assert connection.closed
            methods = [method for method, path in recorder.calls]
            assert methods[0] == "POST"  # create listenKey
            assert methods[-1] == "DELETE"  # close listenKey
            await client.close()

        asyncio.run(scenario())

    def test_expiry_push_triggers_immediate_keepalive(self) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            recorder = _Recorder()
            connection = _ScriptedConnection(
                [{"eventType": "listenKeyWillExpire", "listenKey": _KEY}]
            )
            feed, client = feed_with(recorder, clock, connection, keepalive_ms=3_600_000)
            await client.open()
            await feed.start()
            for _ in range(50):
                if any(method == "PUT" for method, _ in recorder.calls):
                    break
                await asyncio.sleep(0.01)
            assert any(
                method == "PUT" and path == "/api/v1/listenKey"
                for method, path in recorder.calls
            )
            await feed.stop()
            await client.close()

        asyncio.run(scenario())

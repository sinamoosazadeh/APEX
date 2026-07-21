"""Toobit WebSocket stream client (Book VII, /quote/ws/v1).

Owns the wire protocol only: connect, subscribe, keepalive ping/pong,
yield parsed messages. Reconnection policy belongs to the streaming
service; domain translation belongs to the translator.

The connection factory is injectable so tests drive the client with
scripted fake connections and zero network access.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import websockets

from apex.core.contracts.interfaces import IClock
from apex.core.exceptions import DataError, MarketError
from apex.core.logging import StructuredLogger
from apex.core.serialization import JsonValue


@runtime_checkable
class WsConnection(Protocol):
    """Minimal duplex text connection contract."""

    async def send(self, message: str) -> None:
        """Send one text frame."""
        ...

    async def recv(self) -> str | bytes:
        """Receive one frame (may raise on disconnect)."""
        ...

    async def close(self) -> None:
        """Close the connection."""
        ...


type WsConnectFactory = Callable[[str], Awaitable[WsConnection]]


async def _default_connect(url: str) -> WsConnection:
    """Production connector backed by the websockets library."""
    return await websockets.connect(url, ping_interval=None, max_queue=1024)


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamSubscription:
    """One topic subscription (Book VII subscription frame)."""

    symbols: tuple[str, ...]
    topic: str  # e.g. "kline_1h" or "trade"

    def to_frame(self) -> str:
        """Render the subscription request frame."""
        return json.dumps(
            {
                "symbol": ",".join(self.symbols),
                "topic": self.topic,
                "event": "sub",
                "params": {"binary": False},
            }
        )


class ToobitStreamClient:
    """Connects, subscribes and yields parsed stream messages."""

    def __init__(
        self,
        *,
        url: str,
        clock: IClock,
        logger: StructuredLogger,
        ping_interval_ms: int,
        recv_timeout_ms: int,
        connect: WsConnectFactory | None = None,
    ) -> None:
        self._url = url
        self._clock = clock
        self._logger = logger
        self._ping_interval_ms = ping_interval_ms
        self._recv_timeout_ms = recv_timeout_ms
        self._connect: WsConnectFactory = connect if connect is not None else _default_connect

    async def stream(
        self,
        subscriptions: tuple[StreamSubscription, ...],
    ) -> AsyncIterator[dict[str, JsonValue]]:
        """Yield data messages for one connection's lifetime.

        Sends keepalive pings on the configured interval, filters
        pong/ack frames, and raises :class:`MarketError` (MKT-020)
        when the connection drops - callers own reconnection.
        """
        if not subscriptions:
            raise MarketError("at least one subscription is required", code="MKT-021")
        try:
            connection = await self._connect(self._url)
        except Exception as error:
            raise MarketError(
                "websocket connect failed",
                code="MKT-020",
                details={"url": self._url, "reason": str(error)},
            ) from error
        try:
            for subscription in subscriptions:
                await connection.send(subscription.to_frame())
                self._logger.info(
                    "stream_subscribed",
                    topic=subscription.topic,
                    symbols=",".join(subscription.symbols),
                )
            last_ping_ms = self._clock.now().epoch_ms
            while True:
                message = await self._receive(connection)
                if message is None:
                    last_ping_ms = await self._maybe_ping(connection, last_ping_ms)
                    continue
                if self._is_control_frame(message):
                    continue
                last_ping_ms = await self._maybe_ping(connection, last_ping_ms)
                yield message
        finally:
            await connection.close()

    async def _receive(self, connection: WsConnection) -> dict[str, JsonValue] | None:
        """One frame, or None on receive timeout (keepalive tick)."""
        try:
            raw = await asyncio.wait_for(
                connection.recv(), timeout=self._recv_timeout_ms / 1000
            )
        except TimeoutError:
            return None
        except Exception as error:
            raise MarketError(
                "websocket connection lost",
                code="MKT-020",
                details={"url": self._url, "reason": str(error)},
            ) from error
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        try:
            parsed: JsonValue = json.loads(text)
        except json.JSONDecodeError as error:
            raise DataError(
                "stream frame is not valid JSON",
                code="DAT-024",
                details={"reason": str(error)},
            ) from error
        if not isinstance(parsed, dict):
            raise DataError("stream frame is not an object", code="DAT-025")
        return parsed

    async def _maybe_ping(self, connection: WsConnection, last_ping_ms: int) -> int:
        now_ms = self._clock.now().epoch_ms
        if now_ms - last_ping_ms >= self._ping_interval_ms:
            await connection.send(json.dumps({"ping": now_ms}))
            return now_ms
        return last_ping_ms

    @staticmethod
    def _is_control_frame(message: dict[str, JsonValue]) -> bool:
        """Pong replies and subscription acks carry no market data."""
        return "pong" in message or ("data" not in message)

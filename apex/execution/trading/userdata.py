"""Toobit user-data stream (Book VII listenKey; the Phase 10 deferral).

Order and fill events pushed by the venue over
``wss://.../api/v1/ws/<listenKey>`` replace REST fill polling as the
primary signal that an order reached a terminal state. The listenKey
lifecycle is exact Book VII: created via POST, kept alive with a PUT
"every 60 minutes or less" (the platform defaults to 30 minutes -
half the hard TTL), closed with DELETE; the venue also pushes
``listenKeyWillExpire`` five minutes ahead, which triggers an
immediate keepalive.

Payload parsing keys off the event type before touching any
single-letter field - Book VII reuses letters across event types
(``f`` is free balance in one, liquidation price in another). Events
are ordered by their ``E`` event time, per the venue's own guidance.
The REST poll stays as the fallback: a quiet stream never blocks an
execution (the engine re-checks the venue at its poll cadence).
"""

import asyncio
import contextlib
import json
from dataclasses import dataclass
from typing import Final

from apex.core.enums import OrderStatus
from apex.core.exceptions import ApexError, ExecutionError
from apex.core.logging import StructuredLogger
from apex.core.serialization import JsonValue
from apex.core.time.clock import Clock
from apex.data.toobit.stream import WsConnectFactory, WsConnection
from apex.execution.trading.client import ToobitTradingClient

EVENT_ORDER: Final[str] = "contractExecutionReport"
EVENT_TICKET: Final[str] = "ticketInfo"
EVENT_KEY_EXPIRING: Final[str] = "listenKeyWillExpire"

_STATUS_BY_VENUE: Final[dict[str, OrderStatus]] = {
    "NEW": OrderStatus.NEW,
    "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
    "FILLED": OrderStatus.FILLED,
    "CANCELED": OrderStatus.CANCELED,
    "PENDING_CANCEL": OrderStatus.NEW,
    "REJECTED": OrderStatus.REJECTED,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDataEvent:
    """One parsed user-data push."""

    event_type: str
    event_time_ms: int
    order_id: str | None
    client_order_id: str | None
    status: OrderStatus | None
    raw: dict[str, JsonValue]


def parse_user_data(message: JsonValue) -> list[UserDataEvent]:
    """Parse one WebSocket frame into user-data events.

    Frames arrive as either a single object or an array of event
    objects (Book VII shows both shapes). Unknown event types pass
    through with type-only parsing - never dropped silently, never
    misread through another type's field letters.
    """
    items: list[JsonValue] = message if isinstance(message, list) else [message]
    events: list[UserDataEvent] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("e") or item.get("eventType") or "")
        if not event_type:
            continue
        events.append(_parse_one(event_type, item))
    events.sort(key=lambda event: event.event_time_ms)
    return events


def _parse_one(event_type: str, item: dict[str, JsonValue]) -> UserDataEvent:
    event_time = item.get("E") or item.get("eventTime") or item.get("time") or 0
    order_id: str | None = None
    client_order_id: str | None = None
    status: OrderStatus | None = None
    if event_type == EVENT_ORDER:
        order_id = _text(item.get("i"))
        client_order_id = _text(item.get("c"))
        raw_status = str(item.get("X", ""))
        status = _STATUS_BY_VENUE.get(raw_status)
    elif event_type == EVENT_TICKET:
        order_id = _text(item.get("o"))
        client_order_id = _text(item.get("c"))
    return UserDataEvent(
        event_type=event_type,
        event_time_ms=int(str(event_time)) if str(event_time).isdigit() else 0,
        order_id=order_id,
        client_order_id=client_order_id,
        status=status,
        raw=item,
    )


def _text(value: JsonValue | None) -> str | None:
    return str(value) if value is not None else None


def _extract_listen_key(payload: JsonValue) -> str | None:
    """The listenKey from Book VII's bare response (no v2 envelope).

    The doc shows ``{"listenKey": "..."}`` verbatim; a ``data``-wrapped
    variant is tolerated defensively without ever inventing a key.
    """
    if not isinstance(payload, dict):
        return None
    key = payload.get("listenKey")
    if isinstance(key, str) and key:
        return key
    data = payload.get("data")
    if isinstance(data, dict):
        nested = data.get("listenKey")
        if isinstance(nested, str) and nested:
            return nested
    return None


class UserDataFeed:
    """Owns the listenKey lifecycle and the latest per-order state.

    Started lazily by the live engine on first use (boot stays
    network-free), it maintains one WebSocket connection, keeps the
    listenKey alive on the configured cadence, and folds order events
    into a per-venue-order-id status map the engine consults between
    REST polls.
    """

    def __init__(
        self,
        *,
        client: ToobitTradingClient,
        ws_base_url: str,
        keepalive_interval_ms: int,
        recv_timeout_ms: int,
        clock: Clock,
        logger: StructuredLogger,
        connect: WsConnectFactory,
    ) -> None:
        self._client = client
        self._ws_base_url = ws_base_url.rstrip("/")
        self._keepalive_interval_ms = keepalive_interval_ms
        self._recv_timeout_ms = recv_timeout_ms
        self._clock = clock
        self._logger = logger
        self._connect = connect
        self._listen_key: str | None = None
        self._connection: WsConnection | None = None
        self._reader: asyncio.Task[None] | None = None
        self._last_keepalive_ms = 0
        self._statuses: dict[str, OrderStatus] = {}
        self._statuses_by_client: dict[str, OrderStatus] = {}
        self._events_seen = 0

    @property
    def running(self) -> bool:
        """Whether the feed holds a live connection."""
        return self._reader is not None and not self._reader.done()

    @property
    def events_seen(self) -> int:
        """User-data events folded this session."""
        return self._events_seen

    def status_for(
        self, *, order_id: str | None = None, client_order_id: str | None = None
    ) -> OrderStatus | None:
        """The latest pushed status for one order, if any arrived."""
        if order_id is not None and order_id in self._statuses:
            return self._statuses[order_id]
        if client_order_id is not None:
            return self._statuses_by_client.get(client_order_id)
        return None

    # --- Lifecycle -----------------------------------------------------------------

    async def start(self) -> None:
        """Create the listenKey and begin consuming pushes."""
        if self.running:
            return
        payload = await self._client.create_listen_key()
        key = _extract_listen_key(payload)
        if key is None:
            raise ExecutionError(
                "venue returned no listenKey",
                code="EXE-033",
                details={"payload_type": type(payload).__name__},
            )
        self._listen_key = key
        self._last_keepalive_ms = self._clock.now().epoch_ms
        url = f"{self._ws_base_url}/api/v1/ws/{key}"
        try:
            self._connection = await self._connect(url)
        except Exception as error:
            raise ExecutionError(
                "user-data stream connection failed",
                code="EXE-034",
                details={"reason": str(error)},
            ) from error
        self._reader = asyncio.create_task(self._consume())
        self._logger.info("user_data_stream_started")

    async def stop(self) -> None:
        """Close the stream and invalidate the listenKey."""
        if self._reader is not None:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError, ApexError):
                await self._reader
            self._reader = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
        if self._listen_key is not None:
            try:
                await self._client.close_listen_key(self._listen_key)
            except ApexError as error:
                self._logger.failure("listen_key_close_failed", error)
            self._listen_key = None
        self._logger.info("user_data_stream_stopped")

    # --- Consumption ---------------------------------------------------------------

    async def _consume(self) -> None:
        connection = self._connection
        if connection is None:
            return
        while True:
            message = await self._receive(connection)
            await self._maybe_keepalive()
            if message is None:
                continue
            for event in parse_user_data(message):
                await self._fold(event)

    async def _receive(self, connection: WsConnection) -> JsonValue | None:
        try:
            raw = await asyncio.wait_for(
                connection.recv(), timeout=self._recv_timeout_ms / 1000
            )
        except TimeoutError:
            return None
        except Exception as error:
            raise ExecutionError(
                "user-data stream receive failed",
                code="EXE-035",
                details={"reason": str(error)},
            ) from error
        text = raw.decode() if isinstance(raw, bytes) else raw
        try:
            payload: JsonValue = json.loads(text)
        except ValueError:
            self._logger.warning("user_data_invalid_json")
            return None
        return payload

    async def _fold(self, event: UserDataEvent) -> None:
        self._events_seen += 1
        if event.event_type == EVENT_KEY_EXPIRING:
            await self._keepalive_now()
            return
        if event.status is not None:
            if event.order_id is not None:
                self._statuses[event.order_id] = event.status
            if event.client_order_id is not None:
                self._statuses_by_client[event.client_order_id] = event.status
            self._logger.debug(
                "user_data_order_update",
                order_id=event.order_id or "-",
                status=event.status.value,
            )

    async def _maybe_keepalive(self) -> None:
        now_ms = self._clock.now().epoch_ms
        if now_ms - self._last_keepalive_ms < self._keepalive_interval_ms:
            return
        await self._keepalive_now()

    async def _keepalive_now(self) -> None:
        if self._listen_key is None:
            return
        try:
            await self._client.keepalive_listen_key(self._listen_key)
        except ApexError as error:
            self._logger.failure("listen_key_keepalive_failed", error)
            return
        self._last_keepalive_ms = self._clock.now().epoch_ms
        self._logger.debug("listen_key_keepalive_sent")

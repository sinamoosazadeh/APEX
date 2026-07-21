"""Market streaming service (Book II ch. 6: real-time path).

Consumes the Toobit WebSocket stream and keeps the platform current:

- kline updates upsert the forming bar (throttled) and, when the open
  time advances, finalize the previous bar and publish
  ``market.bar.closed`` - the heartbeat every decision engine will
  eventually run on.
- trades are stored idempotently (unique trade ids) and announced in
  batches as ``market.ticks.ingested``.

Reconnects with linear backoff up to a configured attempt budget.
Deterministic-friendly: all timing flows through the injected clock,
and the stream client is injectable for scripted tests.
"""

import asyncio
from dataclasses import dataclass, field, replace

from apex.core.contracts.interfaces import IClock, IEventBus
from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.core.serialization import JsonValue
from apex.data.events import MarketEvent, market_event
from apex.data.toobit.stream import StreamSubscription, ToobitStreamClient
from apex.data.toobit.translator import ToobitTranslator
from apex.domain.market import Bar
from apex.storage.bars import SqliteBarRepository
from apex.storage.ticks import SqliteTickRepository

_SOURCE = "apex.data.streaming"

# Book VII kline stream intervals (3m is REST-only).
WS_SUPPORTED_TIMEFRAMES: frozenset[Timeframe] = frozenset(
    {
        Timeframe.M1,
        Timeframe.M5,
        Timeframe.M15,
        Timeframe.M30,
        Timeframe.H1,
        Timeframe.H2,
        Timeframe.H4,
        Timeframe.H6,
        Timeframe.H12,
        Timeframe.D1,
        Timeframe.W1,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamStats:
    """Outcome of one streaming session."""

    messages: int
    bars_updated: int
    bars_closed: int
    ticks_stored: int
    reconnects: int


@dataclass(slots=True)
class _SessionState:
    """Mutable counters and caches for one streaming session."""

    messages: int = 0
    bars_updated: int = 0
    bars_closed: int = 0
    ticks_stored: int = 0
    reconnects: int = 0
    ticks_unannounced: int = 0
    last_flush_ms: int = 0
    forming: dict[tuple[str, str], Bar] = field(default_factory=dict)
    dirty: set[tuple[str, str]] = field(default_factory=set)


class MarketStreamService:
    """Drives the live WebSocket feed into storage and the event bus."""

    def __init__(
        self,
        *,
        client: ToobitStreamClient,
        translator: ToobitTranslator,
        bar_repository: SqliteBarRepository,
        tick_repository: SqliteTickRepository,
        bus: IEventBus,
        clock: IClock,
        logger: StructuredLogger,
        symbols: tuple[str, ...],
        timeframes: tuple[Timeframe, ...],
        forming_flush_ms: int,
        reconnect_backoff_ms: int,
        max_reconnects: int,
    ) -> None:
        self._client = client
        self._translator = translator
        self._bars = bar_repository
        self._ticks = tick_repository
        self._bus = bus
        self._clock = clock
        self._logger = logger
        self._symbols = symbols
        self._timeframes = tuple(
            tf for tf in timeframes if tf in WS_SUPPORTED_TIMEFRAMES
        )
        self._skipped = tuple(tf for tf in timeframes if tf not in WS_SUPPORTED_TIMEFRAMES)
        self._forming_flush_ms = forming_flush_ms
        self._reconnect_backoff_ms = reconnect_backoff_ms
        self._max_reconnects = max_reconnects

    def subscriptions(self) -> tuple[StreamSubscription, ...]:
        """Subscription set derived from configuration."""
        subs = [StreamSubscription(symbols=self._symbols, topic="trade")]
        subs.extend(
            StreamSubscription(symbols=self._symbols, topic=f"kline_{tf.value}")
            for tf in self._timeframes
        )
        return tuple(subs)

    async def run(self, *, duration_ms: int) -> StreamStats:
        """Stream until the duration elapses; reconnect on drops."""
        for timeframe in self._skipped:
            self._logger.warning(
                "timeframe_not_streamable", timeframe=timeframe.value
            )
        state = _SessionState(last_flush_ms=self._clock.now().epoch_ms)
        deadline_ms = self._clock.now().epoch_ms + duration_ms
        while self._clock.now().epoch_ms < deadline_ms:
            try:
                await self._consume_connection(state, deadline_ms)
                break  # deadline reached inside the consume loop
            except ApexError as error:
                await self._publish_disconnect(error)
                if state.reconnects >= self._max_reconnects:
                    self._logger.failure("stream_reconnects_exhausted", error)
                    break
                state.reconnects += 1
                await asyncio.sleep(
                    self._reconnect_backoff_ms * state.reconnects / 1000
                )
        await self._flush_forming(state)
        await self._announce_ticks(state)
        return StreamStats(
            messages=state.messages,
            bars_updated=state.bars_updated,
            bars_closed=state.bars_closed,
            ticks_stored=state.ticks_stored,
            reconnects=state.reconnects,
        )

    async def _consume_connection(self, state: _SessionState, deadline_ms: int) -> None:
        await self._bus.publish(
            market_event(
                MarketEvent.STREAM_CONNECTED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "symbols": ",".join(self._symbols),
                    "topics": ",".join(s.topic for s in self.subscriptions()),
                },
            )
        )
        async for message in self._client.stream(self.subscriptions()):
            state.messages += 1
            await self._handle(message, state)
            if self._clock.now().epoch_ms >= deadline_ms:
                return

    async def _handle(self, message: dict[str, JsonValue], state: _SessionState) -> None:
        topic = message.get("topic")
        if topic == "trade":
            ticks = self._translator.stream_trades_to_ticks(message)
            inserted = await self._ticks.upsert(ticks)
            state.ticks_stored += inserted
            state.ticks_unannounced += inserted
        elif topic == "kline":
            timeframe = self._kline_timeframe(message)
            if timeframe is None:
                return
            bars = self._translator.stream_klines_to_bars(
                message, timeframe, now=self._clock.now()
            )
            for bar in bars:
                await self._track_bar(bar, state)
        await self._maybe_flush(state)

    @staticmethod
    def _kline_timeframe(message: dict[str, JsonValue]) -> Timeframe | None:
        params = message.get("params")
        if not isinstance(params, dict):
            return None
        kline_type = params.get("klineType")
        by_value = {tf.value: tf for tf in Timeframe}
        return by_value.get(str(kline_type)) if isinstance(kline_type, str) else None

    async def _track_bar(self, bar: Bar, state: _SessionState) -> None:
        key = (bar.symbol, bar.timeframe.value)
        cached = state.forming.get(key)
        if cached is not None and bar.open_time.epoch_ms > cached.open_time.epoch_ms:
            await self._finalize(cached, state)
        if bar.is_closed:
            await self._finalize(bar, state)
            state.forming.pop(key, None)
            state.dirty.discard(key)
        else:
            state.forming[key] = bar
            state.dirty.add(key)

    async def _finalize(self, bar: Bar, state: _SessionState) -> None:
        """Persist a bar as final and announce the close."""
        final = bar if bar.is_closed else replace(bar, is_closed=True)
        await self._bars.upsert([final])
        state.bars_closed += 1
        await self._bus.publish(
            market_event(
                MarketEvent.BAR_CLOSED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "exchange": final.exchange,
                    "symbol": final.symbol,
                    "timeframe": final.timeframe.value,
                    "open_time": final.open_time.epoch_ms,
                    "close": str(final.close.value),
                    "volume": str(final.volume.value),
                },
            )
        )

    async def _maybe_flush(self, state: _SessionState) -> None:
        """Throttled persistence of forming bars + tick announcements."""
        now_ms = self._clock.now().epoch_ms
        if now_ms - state.last_flush_ms < self._forming_flush_ms:
            return
        state.last_flush_ms = now_ms
        await self._flush_forming(state)
        await self._announce_ticks(state)

    async def _announce_ticks(self, state: _SessionState) -> None:
        if state.ticks_unannounced == 0:
            return
        await self._bus.publish(
            market_event(
                MarketEvent.TICKS_INGESTED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "exchange": "toobit",
                    "count": state.ticks_unannounced,
                    "total": state.ticks_stored,
                },
            )
        )
        state.ticks_unannounced = 0

    async def _flush_forming(self, state: _SessionState) -> None:
        """Persist every forming bar that changed since the last flush."""
        for key in sorted(state.dirty):
            bar = state.forming.get(key)
            if bar is None:
                continue
            await self._bars.upsert([bar])
            state.bars_updated += 1
        state.dirty.clear()

    async def _publish_disconnect(self, error: ApexError) -> None:
        self._logger.failure("stream_disconnected", error)
        await self._bus.publish(
            market_event(
                MarketEvent.STREAM_DISCONNECTED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={"error_code": error.code, "error_message": error.message},
            )
        )

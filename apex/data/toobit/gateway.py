"""Toobit market data gateway.

Implements :class:`~apex.contracts.engines.IMarketDataGateway` by
composing the REST client (transport) with the translator
(anti-corruption). Paginates kline history transparently and returns
domain contracts inside Result envelopes - callers never see HTTP.
"""

from collections.abc import Sequence

from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.data.toobit.client import MAX_TRADES_LIMIT, ToobitRestClient
from apex.data.toobit.translator import EXCHANGE_ID, ToobitTranslator, interval_for
from apex.domain.market import Bar, Tick


class ToobitMarketDataGateway:
    """Toobit-backed implementation of the market data contract."""

    def __init__(
        self,
        *,
        client: ToobitRestClient,
        translator: ToobitTranslator,
        clock: Clock,
        logger: StructuredLogger,
        kline_page_limit: int,
    ) -> None:
        self._client = client
        self._translator = translator
        self._clock = clock
        self._logger = logger
        self._page_limit = kline_page_limit

    @property
    def exchange_id(self) -> str:
        """Lowercase exchange identifier."""
        return EXCHANGE_ID

    async def open(self) -> None:
        """Open the underlying HTTP session."""
        await self._client.open()

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        await self._client.close()

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> Result[Sequence[Bar]]:
        """Fetch bars with open time in [start, end), paginating as needed."""
        try:
            bars = await self._fetch_bars_paginated(symbol, timeframe, start, end)
        except ApexError as error:
            self._logger.failure(
                "toobit_fetch_bars_failed", error, symbol=symbol, timeframe=timeframe.value
            )
            return Result.failure(error)
        self._logger.info(
            "toobit_bars_fetched",
            symbol=symbol,
            timeframe=timeframe.value,
            count=len(bars),
        )
        return Result.success(tuple(bars))

    async def _fetch_bars_paginated(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: Timestamp,
        end: Timestamp,
    ) -> list[Bar]:
        """Backward pagination on ``endTime`` (the venue's real dialect).

        Production validation (Phase 15) established that Toobit
        returns the newest ``limit`` klines at or before ``endTime``
        and IGNORES ``startTime``, so deep windows page BACKWARD from
        ``end`` until ``start`` is covered, history is exhausted (a
        short page) or a page makes no older progress. Overlapping
        boundary bars deduplicate through the keyed collection.
        """
        collected: dict[int, Bar] = {}
        cursor_end = end
        while cursor_end.epoch_ms > start.epoch_ms:
            klines = await self._client.get_klines(
                symbol,
                interval_for(timeframe),
                start_ms=start.epoch_ms,
                end_ms=cursor_end.epoch_ms,
                limit=self._page_limit,
            )
            if not klines:
                break
            page = self._translator.to_bars(
                symbol, timeframe, klines, now=self._clock.now()
            )
            for bar in page:
                if start.epoch_ms <= bar.open_time.epoch_ms < end.epoch_ms:
                    collected[bar.open_time.epoch_ms] = bar
            oldest_open = page[0].open_time
            if oldest_open.epoch_ms >= cursor_end.epoch_ms:
                break  # defensive: exchange made no backward progress
            cursor_end = oldest_open
            if len(page) < self._page_limit:
                break  # history exhausted (partial page)
        return [collected[key] for key in sorted(collected)]

    async def fetch_ticks(
        self,
        symbol: str,
        *,
        start: Timestamp,
        limit: int,
    ) -> Result[Sequence[Tick]]:
        """Fetch recent trades at or after ``start`` (Toobit window: 60)."""
        try:
            capped = min(limit, MAX_TRADES_LIMIT)
            trades = await self._client.get_trades(symbol, limit=capped)
            ticks = [self._translator.to_tick(symbol, trade) for trade in trades]
        except ApexError as error:
            self._logger.failure("toobit_fetch_ticks_failed", error, symbol=symbol)
            return Result.failure(error)
        filtered = tuple(
            sorted(
                (tick for tick in ticks if tick.occurred_at.epoch_ms >= start.epoch_ms),
                key=lambda tick: tick.occurred_at.epoch_ms,
            )
        )
        warnings: tuple[str, ...] = ()
        if limit > MAX_TRADES_LIMIT:
            warnings = (f"Toobit caps recent trades at {MAX_TRADES_LIMIT} per request",)
        return Result.success(filtered, warnings=warnings)

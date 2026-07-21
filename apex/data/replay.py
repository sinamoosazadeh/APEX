"""Replay market data gateway (Book II ch. 6: Replay).

Serves stored, confirmed bars through the same IMarketDataGateway
contract the live gateway implements - backtests and research consume
history exactly the way live engines consume the market. Deterministic
by construction: same repository, same query, same bars.
"""

from collections.abc import Sequence

from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError, DataError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.timestamp import MAX_EPOCH_MS, Timestamp
from apex.domain.market import Bar, Tick
from apex.storage.bars import SqliteBarRepository
from apex.storage.ticks import SqliteTickRepository


class ReplayMarketDataGateway:
    """Repository-backed implementation of the market data contract."""

    def __init__(
        self,
        *,
        source_exchange: str,
        repository: SqliteBarRepository,
        logger: StructuredLogger,
        tick_repository: SqliteTickRepository | None = None,
    ) -> None:
        self._source_exchange = source_exchange
        self._repository = repository
        self._ticks = tick_repository
        self._logger = logger

    @property
    def exchange_id(self) -> str:
        """Identifier of the exchange whose history is replayed."""
        return self._source_exchange

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> Result[Sequence[Bar]]:
        """Serve stored confirmed bars with open time in [start, end)."""
        try:
            bars = await self._repository.get_range(
                self._source_exchange,
                symbol,
                timeframe,
                start=start,
                end=end,
                closed_only=True,
            )
        except ApexError as error:
            self._logger.failure("replay_fetch_failed", error, symbol=symbol)
            return Result.failure(error)
        return Result.success(tuple(bars))

    async def fetch_ticks(
        self,
        symbol: str,
        *,
        start: Timestamp,
        limit: int,
    ) -> Result[Sequence[Tick]]:
        """Serve stored ticks at or after ``start``, oldest first."""
        if self._ticks is None:
            return Result.failure(
                DataError(
                    "this replay gateway was built without tick storage",
                    code="DAT-020",
                    details={"symbol": symbol, "requested_limit": limit},
                )
            )
        try:
            ticks = await self._ticks.get_range(
                self._source_exchange,
                symbol,
                start=start,
                end=Timestamp(epoch_ms=MAX_EPOCH_MS),
                limit=limit,
            )
        except ApexError as error:
            self._logger.failure("replay_tick_fetch_failed", error, symbol=symbol)
            return Result.failure(error)
        return Result.success(tuple(ticks))

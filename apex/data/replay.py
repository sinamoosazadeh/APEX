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
from apex.core.time.timestamp import Timestamp
from apex.domain.market import Bar, Tick
from apex.storage.bars import SqliteBarRepository


class ReplayMarketDataGateway:
    """Repository-backed implementation of the market data contract."""

    def __init__(
        self,
        *,
        source_exchange: str,
        repository: SqliteBarRepository,
        logger: StructuredLogger,
    ) -> None:
        self._source_exchange = source_exchange
        self._repository = repository
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
        """Tick replay requires tick storage, which lands later in Phase 3."""
        return Result.failure(
            DataError(
                "tick replay is unavailable: tick storage is a later Phase 3 slice",
                code="DAT-020",
                details={"symbol": symbol, "requested_limit": limit},
            )
        )

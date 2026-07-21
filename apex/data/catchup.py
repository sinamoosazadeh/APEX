"""Ingestion catch-up service (Book II ch. 6: synchronization).

Brings every configured (symbol, timeframe) series up to date through
the ingestion pipeline:

- empty series backfill ``history_bars`` bars;
- existing series resume from the latest stored bar (re-fetching it,
  since it may have been forming when last stored).

One series failing never blocks the others; every outcome is returned.
"""

from dataclasses import dataclass

from apex.core.config import MarketConfig
from apex.core.contracts.interfaces import IClock
from apex.core.enums import Timeframe
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.timestamp import Timestamp
from apex.data.pipeline import BarIngestionPipeline, IngestionSummary
from apex.storage.bars import SqliteBarRepository


@dataclass(frozen=True, slots=True, kw_only=True)
class CatchUpReport:
    """Outcome of one catch-up pass across all configured series."""

    results: tuple[tuple[str, Timeframe, Result[IngestionSummary]], ...]

    @property
    def succeeded(self) -> int:
        """Number of series brought up to date."""
        return sum(1 for _, _, result in self.results if result.ok)

    @property
    def failed(self) -> int:
        """Number of series that failed."""
        return len(self.results) - self.succeeded

    @property
    def bars_stored(self) -> int:
        """Total bars written across successful series."""
        total = 0
        for _, _, result in self.results:
            if result.ok:
                total += result.unwrap().stored
        return total


class CatchUpService:
    """Synchronizes all configured series via the ingestion pipeline."""

    def __init__(
        self,
        *,
        pipeline: BarIngestionPipeline,
        repository: SqliteBarRepository,
        config: MarketConfig,
        exchange_id: str,
        clock: IClock,
        logger: StructuredLogger,
    ) -> None:
        self._pipeline = pipeline
        self._repository = repository
        self._config = config
        self._exchange_id = exchange_id
        self._clock = clock
        self._logger = logger

    async def run_once(self) -> CatchUpReport:
        """One catch-up pass over every configured (symbol, timeframe)."""
        results: list[tuple[str, Timeframe, Result[IngestionSummary]]] = []
        for symbol in self._config.symbols:
            for timeframe in self._config.timeframes:
                result = await self._sync_series(symbol, timeframe)
                results.append((symbol, timeframe, result))
        report = CatchUpReport(results=tuple(results))
        self._logger.info(
            "catchup_complete",
            series=len(report.results),
            succeeded=report.succeeded,
            failed=report.failed,
            bars_stored=report.bars_stored,
        )
        return report

    async def _sync_series(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Result[IngestionSummary]:
        start = await self._resume_point(symbol, timeframe)
        end = self._aligned_end(timeframe)
        if start.epoch_ms >= end.epoch_ms:
            start = end.add_ms(-timeframe.duration_ms)
        self._logger.info(
            "catchup_series",
            symbol=symbol,
            timeframe=timeframe.value,
            start=str(start),
            end=str(end),
        )
        return await self._pipeline.ingest(symbol, timeframe, start=start, end=end)

    async def _resume_point(self, symbol: str, timeframe: Timeframe) -> Timestamp:
        """Latest stored bar's open time, or the backfill horizon."""
        latest = await self._repository.latest_open_time(
            self._exchange_id, symbol, timeframe
        )
        if latest is not None:
            return latest  # re-fetch: it may have been forming when stored
        return self._aligned_end(timeframe).add_ms(
            -self._config.history_bars * timeframe.duration_ms
        )

    def _aligned_end(self, timeframe: Timeframe) -> Timestamp:
        """Exclusive end covering the currently forming bar."""
        step = timeframe.duration_ms
        return self._clock.now().floor(step).add_ms(step)

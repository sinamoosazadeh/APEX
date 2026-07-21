"""Bar ingestion pipeline (Book II ch. 6/16).

The one sanctioned path market data takes into the platform:

    gateway fetch -> translate (already domain) -> quality inspection
    -> persist (idempotent) -> publish catalog events

Every run returns a full :class:`IngestionSummary` inside a Result -
observable, explainable, replayable.
"""

from dataclasses import dataclass

from apex.contracts.engines import IMarketDataGateway
from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import Timeframe
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.data.events import MarketEvent, market_event
from apex.data.quality import BarQualityInspector
from apex.storage.bars import SqliteBarRepository

_SOURCE = "apex.data.pipeline"


@dataclass(frozen=True, slots=True, kw_only=True)
class IngestionSummary:
    """Outcome of one ingestion run."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    fetched: int
    stored: int
    closed_bars: int
    forming_bars: int
    gap_count: int
    missing_bars: int
    first_open: Timestamp | None
    last_open: Timestamp | None


class BarIngestionPipeline:
    """Fetches, scores, persists and announces market bars."""

    def __init__(
        self,
        *,
        gateway: IMarketDataGateway,
        repository: SqliteBarRepository,
        inspector: BarQualityInspector,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._gateway = gateway
        self._repository = repository
        self._inspector = inspector
        self._bus = bus
        self._clock = clock
        self._logger = logger

    async def ingest(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> Result[IngestionSummary]:
        """Run one ingestion pass for a series over [start, end)."""
        fetch = await self._gateway.fetch_bars(symbol, timeframe, start=start, end=end)
        if not fetch.ok:
            assert fetch.error is not None
            await self._bus.publish(
                market_event(
                    MarketEvent.INGESTION_FAILED,
                    occurred_at=self._clock.now(),
                    source=_SOURCE,
                    payload={
                        "exchange": self._gateway.exchange_id,
                        "symbol": symbol,
                        "timeframe": timeframe.value,
                        "error_code": fetch.error.code,
                        "error_message": fetch.error.message,
                    },
                )
            )
            return Result.failure(fetch.error, warnings=fetch.warnings)

        bars = list(fetch.unwrap())
        scored, gap_report = self._inspector.inspect(bars)
        stored = await self._repository.upsert(scored)
        closed = sum(1 for bar in scored if bar.is_closed)
        summary = IngestionSummary(
            exchange=self._gateway.exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            fetched=len(bars),
            stored=stored,
            closed_bars=closed,
            forming_bars=len(scored) - closed,
            gap_count=gap_report.gap_count if gap_report else 0,
            missing_bars=gap_report.missing_bars if gap_report else 0,
            first_open=scored[0].open_time if scored else None,
            last_open=scored[-1].open_time if scored else None,
        )
        await self._announce(summary, gap_report)
        return Result.success(summary, warnings=fetch.warnings)

    async def _announce(
        self,
        summary: IngestionSummary,
        gap_report: object | None,
    ) -> None:
        self._logger.info(
            "bars_ingested",
            symbol=summary.symbol,
            timeframe=summary.timeframe.value,
            fetched=summary.fetched,
            stored=summary.stored,
            gaps=summary.gap_count,
        )
        await self._bus.publish(
            market_event(
                MarketEvent.BARS_INGESTED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "exchange": summary.exchange,
                    "symbol": summary.symbol,
                    "timeframe": summary.timeframe.value,
                    "fetched": summary.fetched,
                    "stored": summary.stored,
                    "closed_bars": summary.closed_bars,
                    "forming_bars": summary.forming_bars,
                    "gap_count": summary.gap_count,
                },
            )
        )
        if summary.gap_count > 0:
            await self._bus.publish(
                market_event(
                    MarketEvent.GAP_DETECTED,
                    occurred_at=self._clock.now(),
                    source=_SOURCE,
                    payload={
                        "exchange": summary.exchange,
                        "symbol": summary.symbol,
                        "timeframe": summary.timeframe.value,
                        "gap_count": summary.gap_count,
                        "missing_bars": summary.missing_bars,
                    },
                )
            )

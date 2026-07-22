"""Portfolio rebuild service (Book II 21.5).

Reconstructs the governed portfolio from the persisted decision
streams: loads each series' confirmed bars and stored decisions, runs
the pure engine fold, replaces the portfolio's durable memory
(positions, snapshots, rejections) and announces every state change
on the event bus. No consumer ever reads positions from anywhere but
this store (Book II 21.5).
"""

from dataclasses import dataclass
from typing import Final

from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import PositionStatus, Timeframe
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.decision.store import SqliteDecisionRepository
from apex.portfolio.account import TradeStatistics
from apex.portfolio.engine import PortfolioEngine, PortfolioFold, SeriesStream
from apex.portfolio.events import PortfolioEvent, portfolio_event
from apex.portfolio.ledger import ClosedTrade, OpenLot
from apex.portfolio.store import (
    PositionRecord,
    RejectionRecord,
    SnapshotRecord,
    SqlitePortfolioRepository,
)
from apex.storage.bars import SqliteBarRepository

_SOURCE: Final[str] = "apex.portfolio.service"


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSummary:
    """Outcome of one portfolio rebuild."""

    portfolio_id: str
    exchange: str
    timeframe: Timeframe
    symbols: tuple[str, ...]
    bars_loaded: int
    signals_seen: int
    positions_opened: int
    positions_closed: int
    signals_rejected: int
    snapshots_stored: int
    final_equity: str
    final_drawdown: float
    open_positions: int


class PortfolioService:
    """Rebuilds and persists the governed portfolio state."""

    def __init__(
        self,
        *,
        exchange_id: str,
        portfolio_id: str,
        engine: PortfolioEngine,
        bar_repository: SqliteBarRepository,
        decision_repository: SqliteDecisionRepository,
        portfolio_repository: SqlitePortfolioRepository,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._exchange_id = exchange_id
        self._portfolio_id = portfolio_id
        self._engine = engine
        self._bars = bar_repository
        self._decisions = decision_repository
        self._store = portfolio_repository
        self._bus = bus
        self._clock = clock
        self._logger = logger

    async def rebuild(
        self,
        symbols: tuple[str, ...],
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> Result[PortfolioSummary]:
        """Fold every series' stored decisions in [start, end)."""
        streams: list[SeriesStream] = []
        bars_loaded = 0
        signals_seen = 0
        for symbol in symbols:
            bars = await self._bars.get_range(
                self._exchange_id, symbol, timeframe,
                start=start, end=end, closed_only=True,
            )
            decisions = await self._decisions.get_range(
                self._exchange_id, symbol, timeframe, start=start, end=end
            )
            bars_loaded += len(bars)
            signals_seen += sum(1 for record in decisions if record.action == "signal")
            streams.append(
                SeriesStream(
                    symbol=symbol,
                    timeframe=timeframe,
                    bars=tuple(bars),
                    decisions=tuple(decisions),
                )
            )
        result = self._engine.fold_streams(streams)
        if not result.ok:
            assert result.error is not None
            await self._announce_failure(symbols, timeframe, result.error)
            return Result.failure(result.error)
        fold = result.unwrap()
        stored_snapshots = await self._persist(fold)
        summary = PortfolioSummary(
            portfolio_id=self._portfolio_id,
            exchange=self._exchange_id,
            timeframe=timeframe,
            symbols=symbols,
            bars_loaded=bars_loaded,
            signals_seen=signals_seen,
            positions_opened=len(fold.closed_trades) + len(fold.open_positions),
            positions_closed=len(fold.closed_trades),
            signals_rejected=len(fold.rejections),
            snapshots_stored=stored_snapshots,
            final_equity=str(fold.final.equity.amount),
            final_drawdown=fold.final.current_drawdown.value,
            open_positions=len(fold.open_positions),
        )
        await self._announce(summary, fold)
        return Result.success(summary)

    async def statistics(self) -> Result[TradeStatistics]:
        """The stored closed-trade statistics (sizing inputs)."""
        try:
            stats = await self._store.statistics(self._portfolio_id)
        except ApexError as error:
            return Result.failure(error)
        return Result.success(stats)

    # --- Persistence -----------------------------------------------------------

    async def _persist(self, fold: PortfolioFold) -> int:
        await self._store.clear(self._portfolio_id)
        positions = [
            self._open_record(lot) for lot in fold.open_positions
        ] + [
            self._closed_record(trade) for trade in fold.closed_trades
        ]
        await self._store.upsert_positions(positions)
        await self._store.upsert_rejections(
            [
                RejectionRecord(
                    portfolio_id=self._portfolio_id,
                    exchange=rejection.exchange,
                    symbol=rejection.symbol,
                    timeframe=rejection.timeframe,
                    bar_open_time=rejection.bar_open_time,
                    reasons=rejection.reasons,
                )
                for rejection in fold.rejections
            ]
        )
        snapshots = [
            SnapshotRecord(
                portfolio_id=self._portfolio_id,
                as_of=snapshot.as_of,
                equity=snapshot.equity.amount,
                cash=snapshot.cash.amount,
                gross_exposure=snapshot.total_exposure.amount,
                unrealized_pnl=snapshot.unrealized_pnl.amount,
                realized_pnl=snapshot.realized_pnl.amount,
                drawdown=snapshot.current_drawdown.value,
                open_positions=snapshot.position_count,
            )
            for snapshot in (*fold.snapshots, fold.final)
        ]
        return await self._store.upsert_snapshots(snapshots)

    def _open_record(self, lot: OpenLot) -> PositionRecord:
        position = lot.position
        return PositionRecord(
            portfolio_id=self._portfolio_id,
            exchange=position.exchange,
            symbol=position.symbol,
            timeframe=lot.timeframe,
            entry_bar_time=Timestamp(epoch_ms=lot.entry_bar_ms),
            position_id=str(position.object_id),
            lineage_id=str(position.lineage_id or position.object_id),
            direction=position.direction.value,
            quantity=position.quantity.value,
            entry=lot.entry,
            stop=lot.stop,
            target=lot.target,
            risk_amount=lot.risk_amount.amount,
            opened_at=position.opened_at,
            status=PositionStatus.OPEN.value,
            closed_at=None,
            exit_price=None,
            realized_pnl=None,
            realized_r=None,
            close_reason=None,
        )

    def _closed_record(self, trade: ClosedTrade) -> PositionRecord:
        return PositionRecord(
            portfolio_id=self._portfolio_id,
            exchange=trade.exchange,
            symbol=trade.symbol,
            timeframe=trade.timeframe,
            entry_bar_time=Timestamp(epoch_ms=trade.entry_bar_ms),
            position_id=str(trade.position_id),
            lineage_id=str(trade.lineage_id),
            direction=trade.direction.value,
            quantity=trade.quantity,
            entry=trade.entry,
            stop=trade.stop,
            target=trade.target,
            risk_amount=trade.risk_amount.amount,
            opened_at=trade.opened_at,
            status=PositionStatus.CLOSED.value,
            closed_at=trade.closed_at,
            exit_price=trade.exit_price,
            realized_pnl=trade.realized_pnl.amount,
            realized_r=trade.realized_r,
            close_reason=trade.reason,
        )

    # --- Announcements ----------------------------------------------------------

    async def _announce(self, summary: PortfolioSummary, fold: PortfolioFold) -> None:
        for trade in fold.closed_trades:
            await self._bus.publish(
                portfolio_event(
                    PortfolioEvent.POSITION_CLOSED,
                    occurred_at=self._clock.now(),
                    source=_SOURCE,
                    payload={
                        "portfolio_id": summary.portfolio_id,
                        "symbol": trade.symbol,
                        "timeframe": trade.timeframe.value,
                        "direction": trade.direction.value,
                        "realized_r": trade.realized_r,
                        "reason": trade.reason,
                    },
                )
            )
        for rejection in fold.rejections:
            await self._bus.publish(
                portfolio_event(
                    PortfolioEvent.SIGNAL_REJECTED,
                    occurred_at=self._clock.now(),
                    source=_SOURCE,
                    payload={
                        "portfolio_id": summary.portfolio_id,
                        "symbol": rejection.symbol,
                        "timeframe": rejection.timeframe.value,
                        "bar_open_ms": rejection.bar_open_time.epoch_ms,
                        "reasons": list(rejection.reasons),
                    },
                )
            )
        for lot in fold.open_positions:
            await self._bus.publish(
                portfolio_event(
                    PortfolioEvent.POSITION_OPENED,
                    occurred_at=self._clock.now(),
                    source=_SOURCE,
                    payload={
                        "portfolio_id": summary.portfolio_id,
                        "symbol": lot.position.symbol,
                        "timeframe": lot.timeframe.value,
                        "direction": lot.position.direction.value,
                        "entry": str(lot.entry),
                        "stop": str(lot.stop),
                    },
                )
            )
        await self._bus.publish(
            portfolio_event(
                PortfolioEvent.REBUILT,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "portfolio_id": summary.portfolio_id,
                    "symbols": list(summary.symbols),
                    "timeframe": summary.timeframe.value,
                    "positions_opened": summary.positions_opened,
                    "positions_closed": summary.positions_closed,
                    "signals_rejected": summary.signals_rejected,
                    "final_equity": summary.final_equity,
                },
            )
        )
        self._logger.info(
            "portfolio_rebuilt",
            portfolio_id=summary.portfolio_id,
            symbols=",".join(summary.symbols),
            timeframe=summary.timeframe.value,
            positions_opened=summary.positions_opened,
            positions_closed=summary.positions_closed,
            signals_rejected=summary.signals_rejected,
            final_equity=summary.final_equity,
        )

    async def _announce_failure(
        self, symbols: tuple[str, ...], timeframe: Timeframe, error: ApexError
    ) -> None:
        await self._bus.publish(
            portfolio_event(
                PortfolioEvent.FAILED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "portfolio_id": self._portfolio_id,
                    "symbols": list(symbols),
                    "timeframe": timeframe.value,
                    "error_code": error.code,
                    "error_message": str(error),
                },
            )
        )
        self._logger.error(
            "portfolio_rebuild_failed",
            portfolio_id=self._portfolio_id,
            timeframe=timeframe.value,
            error_code=error.code,
        )

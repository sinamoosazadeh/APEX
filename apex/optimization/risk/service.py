"""Risk optimization service (Book V part 6).

Produces the fixed decision stream once (the base kernel over the
stored snapshots - never re-optimized here), then runs the ten-stage
risk search over it, records the run and publishes the accepted
winner's ``{SYMBOL}_{TF}_risk.json`` artifact.
"""

from dataclasses import dataclass
from typing import Final

from apex import __version__
from apex.core.context import MarketContext
from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import EventCategory, EventPriority, Timeframe
from apex.core.events.event import Event
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.decision.kernel import CentralDecisionKernel, DecisionParams
from apex.decision.service import DecisionService
from apex.optimization.objective import ObjectiveWeights
from apex.optimization.risk.engine import RiskOptimizer
from apex.optimization.risk.simulator import StopLevels
from apex.optimization.signal.service import OptimizationSummary
from apex.optimization.signal.store import SignalOptimizationStore
from apex.optimization.staged import StageSettings
from apex.storage.bars import SqliteBarRepository

_SOURCE: Final[str] = "apex.optimization.risk.service"
EVENT_COMPLETED: Final[str] = "optimizer.risk.completed"
EVENT_FAILED: Final[str] = "optimizer.risk.failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskOptimizationSummary(OptimizationSummary):
    """Outcome of one risk optimization run."""


class RiskOptimizationService:
    """Runs the risk optimizer over the fixed decision stream."""

    def __init__(
        self,
        *,
        exchange_id: str,
        base_params: DecisionParams,
        settings: StageSettings,
        weights: ObjectiveWeights,
        decision_service: DecisionService,
        bar_repository: SqliteBarRepository,
        store: SignalOptimizationStore,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
        slippage_r: float = 0.01,
    ) -> None:
        self._slippage_r = slippage_r
        self._exchange_id = exchange_id
        self._base_params = base_params
        self._settings = settings
        self._weights = weights
        self._decisions = decision_service
        self._bars = bar_repository
        self._store = store
        self._bus = bus
        self._clock = clock
        self._logger = logger

    async def optimize(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
        seed: int,
    ) -> Result[OptimizationSummary]:
        """Optimize the risk plan for one series with one seed."""
        bars = await self._bars.get_range(
            self._exchange_id, symbol, timeframe, start=start, end=end, closed_only=True
        )
        snapshots = await self._decisions.build_snapshots(bars, symbol, timeframe, end)
        context = MarketContext(symbol=symbol, timeframe=timeframe, as_of=self._clock.now())
        kernel = CentralDecisionKernel(params=self._base_params, clock=self._clock)
        decided = kernel.decide_series(snapshots, context)
        if not decided.ok:
            assert decided.error is not None
            await self._announce_failure(symbol, timeframe, decided.error)
            return Result.failure(decided.error)
        levels = {
            snapshot.bar.open_time.epoch_ms: StopLevels(
                ob_long_bottom=snapshot.ob_long_bottom,
                ob_short_top=snapshot.ob_short_top,
                macro_high=snapshot.macro_high,
                macro_low=snapshot.macro_low,
            )
            for snapshot in snapshots
        }
        optimizer = RiskOptimizer(
            outcomes=decided.unwrap(),
            bars=[snapshot.bar for snapshot in snapshots],
            symbol=symbol,
            timeframe=timeframe.value,
            fee_r=self._base_params.fee_slippage_r,
            settings=self._settings,
            weights=self._weights,
            levels=levels,
            slippage_r=self._slippage_r,
        )
        result = optimizer.optimize_detailed(seed=seed)
        if not result.ok:
            assert result.error is not None
            await self._announce_failure(symbol, timeframe, result.error)
            return Result.failure(result.error)
        report = result.unwrap()
        created_at = self._clock.now()
        await self._store.record_run(report, created_at=created_at)
        artifact_path: str | None = None
        if report.accepted:
            path = await self._store.publish_artifact(
                report, created_at=created_at, apex_version=__version__
            )
            artifact_path = str(path)
        summary = RiskOptimizationSummary(
            symbol=symbol,
            timeframe=timeframe,
            trials=report.trials,
            best_score=report.best_score,
            confidence=report.confidence,
            accepted=report.accepted,
            artifact_path=artifact_path,
        )
        await self._announce_success(summary)
        return Result.success(summary)

    async def _announce_success(self, summary: OptimizationSummary) -> None:
        await self._bus.publish(
            Event(
                event_type=EVENT_COMPLETED,
                category=EventCategory.SYSTEM,
                priority=EventPriority.MEDIUM,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "symbol": summary.symbol,
                    "timeframe": summary.timeframe.value,
                    "trials": summary.trials,
                    "best_score": summary.best_score,
                    "confidence": summary.confidence,
                    "accepted": summary.accepted,
                },
            )
        )
        self._logger.info(
            "risk_optimization_completed",
            symbol=summary.symbol,
            timeframe=summary.timeframe.value,
            trials=summary.trials,
            accepted=summary.accepted,
        )

    async def _announce_failure(
        self, symbol: str, timeframe: Timeframe, error: ApexError
    ) -> None:
        await self._bus.publish(
            Event(
                event_type=EVENT_FAILED,
                category=EventCategory.SYSTEM,
                priority=EventPriority.CRITICAL,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "symbol": symbol,
                    "timeframe": timeframe.value,
                    "error_code": error.code,
                    "error_message": str(error),
                },
            )
        )
        self._logger.error(
            "risk_optimization_failed",
            symbol=symbol,
            timeframe=timeframe.value,
            error_code=error.code,
        )

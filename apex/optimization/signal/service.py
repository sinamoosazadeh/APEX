"""Signal optimization service (Book V part 5).

Assembles the decision snapshots for one series, runs the ten-stage
optimizer, records the run, publishes the artifact for accepted
winners and announces the outcome on the event bus.
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
from apex.decision.kernel import DecisionParams
from apex.decision.service import DecisionService
from apex.optimization.objective import ObjectiveWeights
from apex.optimization.signal.engine import (
    OptimizerSettings,
    SignalOptimizationReport,
    SignalOptimizer,
)
from apex.optimization.signal.store import SignalOptimizationStore
from apex.storage.bars import SqliteBarRepository

_SOURCE: Final[str] = "apex.optimization.signal.service"
EVENT_COMPLETED: Final[str] = "optimizer.signal.completed"
EVENT_FAILED: Final[str] = "optimizer.signal.failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class OptimizationSummary:
    """Outcome of one optimization run."""

    symbol: str
    timeframe: Timeframe
    trials: int
    best_score: float
    confidence: float
    accepted: bool
    artifact_path: str | None


class SignalOptimizationService:
    """Runs the signal optimizer over stored decision inputs."""

    def __init__(
        self,
        *,
        exchange_id: str,
        base_params: DecisionParams,
        settings: OptimizerSettings,
        weights: ObjectiveWeights,
        decision_service: DecisionService,
        bar_repository: SqliteBarRepository,
        store: SignalOptimizationStore,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
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
        """Optimize one series over [start, end) with one seed."""
        bars = await self._bars.get_range(
            self._exchange_id, symbol, timeframe, start=start, end=end, closed_only=True
        )
        snapshots = await self._decisions.build_snapshots(bars, symbol, timeframe, end)
        context = MarketContext(symbol=symbol, timeframe=timeframe, as_of=self._clock.now())
        optimizer = SignalOptimizer(
            snapshots=snapshots,
            base_params=self._base_params,
            context=context,
            settings=self._settings,
            weights=self._weights,
            clock=self._clock,
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
        summary = OptimizationSummary(
            symbol=symbol,
            timeframe=timeframe,
            trials=report.trials,
            best_score=report.best_score,
            confidence=report.confidence,
            accepted=report.accepted,
            artifact_path=artifact_path,
        )
        await self._announce_success(summary, report)
        return Result.success(summary)

    async def _announce_success(
        self, summary: OptimizationSummary, report: SignalOptimizationReport
    ) -> None:
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
                    "monte_carlo_share": report.monte_carlo_share,
                    "stability_score": report.stability_score,
                },
            )
        )
        self._logger.info(
            "signal_optimization_completed",
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
            "signal_optimization_failed",
            symbol=symbol,
            timeframe=timeframe.value,
            error_code=error.code,
        )

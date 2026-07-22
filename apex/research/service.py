"""Research service (Book II ch. 14/23; Book V part 7).

Two responsibilities behind one service:

- **Study**: the scientific pass over one or more series - attribution
  join, the AICE learning fold into a versioned artifact, calibration
  measurement, drift detection and execution-quality aggregation. A
  study only produces knowledge (14.3): nothing it writes is consumed
  without the injection path below.
- **Orchestrate**: the Book V part 7 lifecycle - drain queued
  optimization jobs sequentially (priority policy, bounded retries),
  activate accepted artifacts as the series' active version, roll
  back on demand, and answer the runtime injector: active kernel
  overrides and the latest learning state per series.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from apex import __version__
from apex.core.context import MarketContext
from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError, ResearchError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.decision.kernel import DecisionParams
from apex.decision.service import DecisionService
from apex.decision.store import SqliteDecisionRepository
from apex.domain.learning import LearningParams, LearningState
from apex.execution.store import SqliteExecutionRepository
from apex.optimization.objective import ObjectiveWeights
from apex.optimization.risk.service import RiskOptimizationService
from apex.optimization.signal.service import SignalOptimizationService
from apex.optimization.staged import StageSettings
from apex.portfolio.store import SqlitePortfolioRepository
from apex.probability.store import SqliteProbabilityRepository
from apex.research.analysis import (
    CalibrationReport,
    DriftReport,
    ExecutionQualityReport,
    detect_drift,
    measure_calibration,
    measure_execution_quality,
)
from apex.research.attribution import AttributionResult, join_outcomes
from apex.research.events import ResearchEvent, research_event
from apex.research.experiments import walk_forward_reoptimize
from apex.research.store import (
    JOB_COMPLETED,
    JOB_FAILED,
    JOB_RUNNING,
    ResearchJob,
    SqliteResearchRepository,
)
from apex.storage.bars import SqliteBarRepository

_SOURCE: Final[str] = "apex.research.service"

KIND_SIGNAL: Final[str] = "signal"
KIND_RISK: Final[str] = "risk"
KIND_WALK_FORWARD: Final[str] = "walk_forward"
# Per-fold re-optimization budget (kept intentionally small: every
# fold runs the full staged pipeline).
_FOLD_SETTINGS: Final[StageSettings] = StageSettings(
    random_trials=6, latin_trials=4, bayesian_trials=6, refinement_rounds=1,
    validation_folds=2, monte_carlo_resamples=50,
)
_WALK_FORWARD_FOLDS: Final[int] = 3

_PRIORITY: Final[dict[str, int]] = {"BTCUSDT": 0, "ETHUSDT": 1}
_DEFAULT_PRIORITY: Final[int] = 2


@dataclass(frozen=True, slots=True, kw_only=True)
class SeriesStudy:
    """One series' study output."""

    symbol: str
    timeframe: Timeframe
    attribution: AttributionResult
    learning_version: int
    calibration: CalibrationReport
    drifts: tuple[DriftReport, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ResearchSummary:
    """Outcome of one research study run."""

    timeframe: Timeframe
    studies: tuple[SeriesStudy, ...]
    execution_quality: ExecutionQualityReport


@dataclass(frozen=True, slots=True, kw_only=True)
class OrchestrationSummary:
    """Outcome of one queue drain."""

    drained: int
    completed: int
    failed: int
    activated: tuple[str, ...]


class ResearchService:
    """Produces knowledge and orchestrates the optimization lifecycle."""

    def __init__(
        self,
        *,
        exchange_id: str,
        portfolio_id: str,
        learning_params: LearningParams,
        store: SqliteResearchRepository,
        portfolio_repository: SqlitePortfolioRepository,
        decision_repository: SqliteDecisionRepository,
        probability_repository: SqliteProbabilityRepository,
        execution_repository: SqliteExecutionRepository,
        signal_service: SignalOptimizationService,
        risk_service: RiskOptimizationService,
        decision_service: DecisionService,
        bar_repository: SqliteBarRepository,
        base_params: DecisionParams,
        weights: ObjectiveWeights,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._decision_service = decision_service
        self._bars = bar_repository
        self._base_params = base_params
        self._weights = weights
        self._exchange_id = exchange_id
        self._portfolio_id = portfolio_id
        self._learning_params = learning_params
        self._store = store
        self._portfolio = portfolio_repository
        self._decisions = decision_repository
        self._assessments = probability_repository
        self._executions = execution_repository
        self._signal_service = signal_service
        self._risk_service = risk_service
        self._bus = bus
        self._clock = clock
        self._logger = logger

    # --- Study -----------------------------------------------------------------

    async def study(
        self,
        symbols: tuple[str, ...],
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> Result[ResearchSummary]:
        """Attribution, learning fold, calibration and drift per series."""
        try:
            summary = await self._study(symbols, timeframe, start, end)
        except ApexError as error:
            await self._announce_failure(symbols, timeframe, error)
            return Result.failure(error)
        return Result.success(summary)

    async def _study(
        self,
        symbols: tuple[str, ...],
        timeframe: Timeframe,
        start: Timestamp,
        end: Timestamp,
    ) -> ResearchSummary:
        studies: list[SeriesStudy] = []
        for symbol in symbols:
            studies.append(await self._study_series(symbol, timeframe, start, end))
        execution_quality = measure_execution_quality(
            await self._executions.get_executions(self._portfolio_id)
        )
        summary = ResearchSummary(
            timeframe=timeframe,
            studies=tuple(studies),
            execution_quality=execution_quality,
        )
        await self._announce(summary)
        return summary

    async def _study_series(
        self, symbol: str, timeframe: Timeframe, start: Timestamp, end: Timestamp
    ) -> SeriesStudy:
        positions = [
            record
            for record in await self._portfolio.get_positions(self._portfolio_id)
            if record.symbol == symbol and record.timeframe is timeframe
        ]
        decisions = await self._decisions.get_range(
            self._exchange_id, symbol, timeframe, start=start, end=end
        )
        assessment_rows = await self._assessments.get_range(
            self._exchange_id, symbol, timeframe, start=start, end=end
        )
        channels_by_bar = {
            record.bar_open_time.epoch_ms: record.channels
            for record in assessment_rows
            if record.side == "long"
        }
        attribution = join_outcomes(positions, decisions, channels_by_bar)
        state = LearningState.fresh(self._learning_params)
        for outcome in attribution.outcomes:
            state = state.fold_outcome(
                setup=outcome.setup,
                win=outcome.win,
                realized_r=outcome.realized_r,
                probability=outcome.probability,
                channel_scores=outcome.channel_scores,
            )
        version = await self._store.save_learning_artifact(
            symbol=symbol,
            timeframe=timeframe,
            payload=state.to_json(),
            outcomes=state.outcomes_folded,
            created_at=self._clock.now(),
        )
        calibration = measure_calibration(attribution.outcomes)
        drifts = self._drifts(
            [record.probability for record in assessment_rows if record.side == "long"],
            [1.0 if outcome.win else 0.0 for outcome in attribution.outcomes],
        )
        return SeriesStudy(
            symbol=symbol,
            timeframe=timeframe,
            attribution=attribution,
            learning_version=version,
            calibration=calibration,
            drifts=drifts,
        )

    def _drifts(
        self, probabilities: list[float], wins: list[float]
    ) -> tuple[DriftReport, ...]:
        reports = [detect_drift("assessment_probability_long", probabilities)]
        if len(wins) >= 20:
            reports.append(detect_drift("trade_win_rate", wins))
        return tuple(reports)

    # --- Orchestration (Book V part 7) ---------------------------------------------

    async def enqueue_cycle(
        self,
        symbols: tuple[str, ...],
        timeframes: tuple[Timeframe, ...],
        *,
        kinds: tuple[str, ...] = (KIND_SIGNAL, KIND_RISK),
        seed: int = 7,
        window_bars: int = 0,
    ) -> int:
        """Queue one optimization cycle; returns the number queued."""
        queued = 0
        for symbol in symbols:
            for timeframe in timeframes:
                for kind in kinds:
                    await self._store.enqueue_job(
                        symbol=symbol,
                        timeframe=timeframe,
                        kind=kind,
                        priority=_PRIORITY.get(symbol, _DEFAULT_PRIORITY),
                        seed=seed,
                        window_bars=window_bars,
                        created_at=self._clock.now(),
                    )
                    queued += 1
        return queued

    async def orchestrate(
        self, *, limit: int, default_window_bars: int
    ) -> Result[OrchestrationSummary]:
        """Drain up to ``limit`` jobs sequentially (max concurrency 1)."""
        try:
            summary = await self._orchestrate(limit, default_window_bars)
        except ApexError as error:
            await self._announce_failure((), Timeframe.H1, error)
            return Result.failure(error)
        return Result.success(summary)

    async def _orchestrate(
        self, limit: int, default_window_bars: int
    ) -> OrchestrationSummary:
        drained = completed = failed = 0
        activated: list[str] = []
        while drained < limit:
            job = await self._store.next_pending_job()
            if job is None:
                break
            drained += 1
            await self._store.mark_job(
                job.job_id, status=JOB_RUNNING, bump_attempts=True
            )
            try:
                artifact = await self._run_job(job, default_window_bars)
            except ApexError as error:
                failed += 1
                await self._store.mark_job(
                    job.job_id,
                    status=JOB_FAILED,
                    completed_at=self._clock.now(),
                    result=f"{error.code}: {error}",
                )
                self._logger.failure("research_job_failed", error)
                continue
            completed += 1
            await self._store.mark_job(
                job.job_id,
                status=JOB_COMPLETED,
                completed_at=self._clock.now(),
                result=artifact or "rejected",
            )
            if artifact:
                activated.append(artifact)
        return OrchestrationSummary(
            drained=drained,
            completed=completed,
            failed=failed,
            activated=tuple(activated),
        )

    async def _run_job(self, job: ResearchJob, default_window_bars: int) -> str | None:
        """Run one optimizer job; returns the activated artifact path."""
        bars = job.window_bars if job.window_bars > 0 else default_window_bars
        now = self._clock.now()
        end = now.floor(job.timeframe.duration_ms).add_ms(job.timeframe.duration_ms)
        start = end.add_ms(-bars * job.timeframe.duration_ms)
        if job.kind == KIND_SIGNAL:
            outcome = await self._signal_service.optimize(
                job.symbol, job.timeframe, start=start, end=end, seed=job.seed
            )
        elif job.kind == KIND_RISK:
            outcome = await self._risk_service.optimize(
                job.symbol, job.timeframe, start=start, end=end, seed=job.seed
            )
        elif job.kind == KIND_WALK_FORWARD:
            return await self._run_walk_forward(job, start, end)
        else:
            raise ResearchError(
                "unknown research job kind",
                code="RES-001",
                details={"kind": job.kind},
            )
        summary = outcome.unwrap()
        if not summary.accepted or not summary.artifact_path:
            return None
        await self._store.activate_version(
            symbol=job.symbol,
            timeframe=job.timeframe,
            kind=job.kind,
            artifact_path=summary.artifact_path,
            activated_at=self._clock.now(),
        )
        return summary.artifact_path

    async def _run_walk_forward(
        self, job: ResearchJob, start: Timestamp, end: Timestamp
    ) -> str | None:
        """Per-fold re-optimization (the Phase 7 deferral) as a job.

        Registers the outcome in the experiment registry with full
        reproducibility stamps; walk-forward runs never activate
        artifacts - they judge robustness (Book V validation).
        """
        chart_bars = await self._bars.get_range(
            self._exchange_id, job.symbol, job.timeframe,
            start=start, end=end, closed_only=True,
        )
        bars = await self._decision_service.build_snapshots(
            chart_bars, job.symbol, job.timeframe, end
        )
        context = MarketContext(
            symbol=job.symbol, timeframe=job.timeframe, as_of=self._clock.now()
        )
        report = walk_forward_reoptimize(
            bars,
            base_params=self._base_params,
            context=context,
            clock=self._clock,
            settings=_FOLD_SETTINGS,
            weights=self._weights,
            folds=_WALK_FORWARD_FOLDS,
            seed=job.seed,
        )
        status = (
            "validated"
            if report.accepted_folds > 0 and report.total_r > 0
            else "rejected"
        )
        await self._store.register_experiment(
            hypothesis="per-fold walk-forward re-optimization sustains an edge",
            symbol=job.symbol,
            timeframe=job.timeframe,
            window_start=start,
            window_end=end,
            seed=job.seed,
            project_version=__version__,
            baseline="base decision parameters",
            candidate=f"re-optimized per fold ({report.accepted_folds} accepted)",
            p_value=None,
            effect_size=None,
            status=status,
            created_at=self._clock.now(),
        )
        self._logger.info(
            "walk_forward_reoptimized",
            symbol=job.symbol,
            timeframe=job.timeframe.value,
            folds=len(report.folds),
            accepted=report.accepted_folds,
            total_r=f"{report.total_r:.2f}",
        )
        return None


    # --- Runtime injection (Book V part 7) --------------------------------------------

    async def active_overrides(
        self, symbol: str, timeframe: Timeframe, *, kind: str = KIND_SIGNAL
    ) -> dict[str, float] | None:
        """The active accepted artifact's optimized parameters."""
        path = await self._store.active_artifact(symbol, timeframe, kind)
        if path is None:
            return None
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ResearchError(
                "active artifact is unreadable",
                code="RES-002",
                details={"path": path, "reason": str(error)},
            ) from error
        parameters = payload.get("optimized_parameters", {})
        if not isinstance(parameters, dict):
            raise ResearchError(
                "active artifact carries no parameter mapping",
                code="RES-003",
                details={"path": path},
            )
        return {str(name): float(value) for name, value in parameters.items()}

    async def learning_state(
        self, symbol: str, timeframe: Timeframe
    ) -> LearningState | None:
        """The latest learning artifact for one series, if any."""
        payload = await self._store.latest_learning_artifact(symbol, timeframe)
        if payload is None:
            return None
        return LearningState.from_json(payload)

    async def rollback(
        self, symbol: str, timeframe: Timeframe, kind: str
    ) -> str | None:
        """Repoint the series to its previous accepted artifact."""
        return await self._store.rollback_version(symbol, timeframe, kind)

    # --- Announcements ------------------------------------------------------------------

    async def _announce(self, summary: ResearchSummary) -> None:
        for study in summary.studies:
            await self._bus.publish(
                research_event(
                    ResearchEvent.STUDIED,
                    occurred_at=self._clock.now(),
                    source=_SOURCE,
                    payload={
                        "symbol": study.symbol,
                        "timeframe": study.timeframe.value,
                        "outcomes": study.attribution.closed_trades,
                        "learning_version": study.learning_version,
                        "brier": study.calibration.brier_score,
                        "drifting": [
                            report.name for report in study.drifts if report.drifting
                        ],
                    },
                )
            )
        self._logger.info(
            "research_study_completed",
            series=len(summary.studies),
            executions=summary.execution_quality.executions,
        )

    async def _announce_failure(
        self, symbols: tuple[str, ...], timeframe: Timeframe, error: ApexError
    ) -> None:
        await self._bus.publish(
            research_event(
                ResearchEvent.FAILED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "symbols": list(symbols),
                    "timeframe": timeframe.value,
                    "error_code": error.code,
                    "error_message": str(error),
                },
            )
        )
        self._logger.error(
            "research_failed",
            timeframe=timeframe.value,
            error_code=error.code,
        )

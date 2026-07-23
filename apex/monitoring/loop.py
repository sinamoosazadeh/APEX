"""Live operational loop (Book I 10.12 end-to-end path; Book II ch. 26).

The realtime spine: streamed bars close -> features -> assessment ->
decision (research-injected) -> kill-switch gate -> execution ->
portfolio fold -> research upkeep - every stage timed, heartbeaten,
traced and alert-checked. The loop consumes ``market.bar.closed``
events inline (the bus is deterministic and sequential by design:
one bar is fully processed before the next message), so the whole
pipeline stays strictly causal on confirmed bars only.

Research upkeep per bar: shadow promotions are evaluated once enough
forward bars accumulated, the post-promotion guard rolls a degrading
artifact back automatically (Book V continuous monitoring), and -
when enabled - one queued optimization job drains between bars.

Runs bounded (``--seconds``) for validation or indefinitely with
OS-signal-driven graceful shutdown - the first indefinite runtime
surface in the platform.
"""

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Final

from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import Timeframe
from apex.core.events.event import Event
from apex.core.exceptions import ApexError
from apex.core.identity import IdProvider
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.data.catchup import CatchUpService
from apex.data.events import MarketEvent
from apex.data.streaming import MarketStreamService
from apex.decision.kernel import CentralDecisionKernel
from apex.decision.plugin import decision_params_from_config
from apex.decision.service import DecisionService
from apex.decision.store import SqliteDecisionRepository
from apex.execution.service import ExecutionService
from apex.execution.store import SqliteExecutionRepository
from apex.features.pipeline import FeatureComputationPipeline
from apex.monitoring.events import MonitoringEvent, monitoring_event
from apex.monitoring.records import AlertSeverity
from apex.monitoring.service import MonitoringService
from apex.probability.engine import ConfluenceProbabilityEngine
from apex.probability.plugin import probability_params_from_config
from apex.probability.service import ProbabilityService
from apex.research.service import ResearchService

_SOURCE: Final[str] = "apex.monitoring.loop"
_STREAM_CHUNK_MS: Final[int] = 60_000
_COMPONENT: Final[str] = "operations_loop"


@dataclass(frozen=True, slots=True, kw_only=True)
class LoopStats:
    """Outcome of one operational-loop session."""

    bars_processed: int
    signals_fired: int
    executions_attempted: int
    executions_filled: int
    alerts_raised: int
    jobs_drained: int
    promotions_evaluated: int
    rollbacks: int
    snapshots_taken: int
    stream_reconnects: int


@dataclass(slots=True)
class _LoopState:
    """Mutable counters for one loop session."""

    bars_processed: int = 0
    signals_fired: int = 0
    executions_attempted: int = 0
    executions_filled: int = 0
    alerts_raised: int = 0
    jobs_drained: int = 0
    promotions_evaluated: int = 0
    rollbacks: int = 0
    snapshots_taken: int = 0
    stream_reconnects: int = 0
    last_snapshot_ms: int = 0


class OperationsLoopService:
    """Drives the live pipeline off closed-bar events."""

    def __init__(
        self,
        *,
        config: AppConfig,
        catchup: CatchUpService,
        stream: MarketStreamService,
        features: FeatureComputationPipeline,
        probability: ProbabilityService,
        decision: DecisionService,
        decision_repository: SqliteDecisionRepository,
        execution: ExecutionService,
        execution_repository: SqliteExecutionRepository,
        research: ResearchService,
        monitoring: MonitoringService,
        portfolio_id: str,
        bus: IEventBus,
        clock: Clock,
        id_provider: IdProvider,
        logger: StructuredLogger,
    ) -> None:
        self._config = config
        self._catchup = catchup
        self._stream = stream
        self._features = features
        self._probability = probability
        self._decision = decision
        self._decisions = decision_repository
        self._execution = execution
        self._executions = execution_repository
        self._research = research
        self._monitoring = monitoring
        self._portfolio_id = portfolio_id
        self._bus = bus
        self._clock = clock
        self._ids = id_provider
        self._logger = logger
        self._subscribed = False
        self._stop = asyncio.Event()
        self._state = _LoopState()
        self._live = False
        self._orchestrate = False
        self._tracked: frozenset[tuple[str, str]] = frozenset()

    # --- Session -----------------------------------------------------------------

    async def run(
        self,
        *,
        seconds: int,
        live: bool = False,
        orchestrate: bool = False,
        symbols: tuple[str, ...] = (),
        timeframes: tuple[Timeframe, ...] = (),
    ) -> LoopStats:
        """Catch up, then stream and process until stop or deadline.

        ``seconds == 0`` runs indefinitely until SIGINT/SIGTERM.
        """
        self._live = live
        self._orchestrate = orchestrate
        self._tracked = self._resolve_tracked(symbols, timeframes)
        self._state = _LoopState(last_snapshot_ms=self._clock.now().epoch_ms)
        self._stop.clear()
        self._subscribe_once()
        await self._announce(MonitoringEvent.LOOP_STARTED)
        await self._catchup.run_once()
        try:
            await self._stream_until_done(seconds)
        finally:
            await self._monitoring.collector.flush()
            await self._announce(MonitoringEvent.LOOP_STOPPED)
        return self._stats()

    def request_stop(self) -> None:
        """Ask the loop to finish after the current stream chunk."""
        self._stop.set()

    def _resolve_tracked(
        self, symbols: tuple[str, ...], timeframes: tuple[Timeframe, ...]
    ) -> frozenset[tuple[str, str]]:
        chosen_symbols = symbols or self._config.market.symbols
        chosen_timeframes = timeframes or self._config.market.timeframes
        return frozenset(
            (symbol, timeframe.value)
            for symbol in chosen_symbols
            for timeframe in chosen_timeframes
        )

    def _subscribe_once(self) -> None:
        if self._subscribed:
            return
        self._bus.subscribe(MarketEvent.BAR_CLOSED.value, self._on_bar_closed)
        self._subscribed = True

    async def _stream_until_done(self, seconds: int) -> None:
        deadline_ms = (
            self._clock.now().epoch_ms + seconds * 1_000 if seconds > 0 else None
        )
        while not self._stop.is_set():
            remaining = (
                deadline_ms - self._clock.now().epoch_ms
                if deadline_ms is not None
                else _STREAM_CHUNK_MS
            )
            if remaining <= 0:
                break
            stats = await self._stream.run(
                duration_ms=min(remaining, _STREAM_CHUNK_MS)
            )
            self._state.stream_reconnects += stats.reconnects

    # --- Bar processing ------------------------------------------------------------

    async def _on_bar_closed(self, event: Event) -> None:
        """Bus handler: run the pipeline for one tracked closed bar."""
        payload = event.payload
        symbol = str(payload.get("symbol", ""))
        timeframe_raw = str(payload.get("timeframe", ""))
        open_time = payload.get("open_time")
        if (symbol, timeframe_raw) not in self._tracked:
            return
        if not isinstance(open_time, int):
            return
        timeframe = Timeframe(timeframe_raw)
        try:
            await self._process_bar(symbol, timeframe, open_time)
        except ApexError as error:
            await self._on_stage_failure(symbol, timeframe, error)

    async def _process_bar(
        self, symbol: str, timeframe: Timeframe, open_ms: int
    ) -> None:
        started_ms = self._clock.now().epoch_ms
        end = Timestamp(epoch_ms=open_ms + timeframe.duration_ms)
        start = end.add_ms(-self._config.market.history_bars * timeframe.duration_ms)
        tags = {"symbol": symbol, "timeframe": timeframe.value}
        collector = self._monitoring.collector
        await self._staged(
            "features", tags,
            self._features.compute(symbol, timeframe, start=start, end=end),
        )
        if await self._monitoring.kill_switch.allows_processing():
            await self._assess_and_decide(symbol, timeframe, start, end, tags)
        else:
            collector.metric("loop.skipped_paused", 1.0, tags=tags)
        await self._research_upkeep(symbol, timeframe)
        collector.operation(tags=tags)
        await collector.beat(_COMPONENT)
        total_ms = self._clock.now().epoch_ms - started_ms
        collector.metric("loop.bar.total_ms", float(total_ms), tags=tags)
        self._state.bars_processed += 1
        await self._finish_bar(symbol, timeframe, open_ms, total_ms)

    async def _assess_and_decide(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: Timestamp,
        end: Timestamp,
        tags: dict[str, str],
    ) -> None:
        learning = await self._research.learning_state(symbol, timeframe)
        engine_override = None
        if learning is not None:
            engine_override = ConfluenceProbabilityEngine(
                params=probability_params_from_config(self._config.market.probability),
                clock=self._clock,
                learning=learning,
            )
        await self._staged(
            "probability", tags,
            self._probability.compute(
                symbol, timeframe, start=start, end=end,
                engine_override=engine_override,
            ),
        )
        overrides = await self._research.active_overrides(symbol, timeframe)
        kernel_override = None
        if overrides or learning is not None:
            base = decision_params_from_config(self._config.market.decision)
            params = base.with_overrides(overrides) if overrides else base
            kernel_override = CentralDecisionKernel(
                params=params, clock=self._clock, learning=learning
            )
        await self._staged(
            "decision", tags,
            self._decision.compute(
                symbol, timeframe, start=start, end=end,
                kernel_override=kernel_override,
            ),
        )
        await self._maybe_execute(symbol, timeframe, start, end, tags)

    async def _maybe_execute(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: Timestamp,
        end: Timestamp,
        tags: dict[str, str],
    ) -> None:
        """Execute the newest unexecuted fired signal, if entries allowed."""
        signal_bar = await self._latest_unexecuted_signal(
            symbol, timeframe, start, end
        )
        if signal_bar is None:
            return
        self._state.signals_fired += 1
        if not await self._monitoring.kill_switch.allows_new_entries():
            self._monitoring.collector.metric("loop.entries_blocked", 1.0, tags=tags)
            return
        self._state.executions_attempted += 1
        stage_start = self._clock.now().epoch_ms
        outcome = await self._execution.execute_latest_signal(
            symbol, timeframe, start=start, end=end, live=self._live
        )
        elapsed = self._clock.now().epoch_ms - stage_start
        self._monitoring.collector.metric(
            "loop.stage.execution.ms", float(elapsed), tags=tags
        )
        if outcome.ok and outcome.unwrap().position_opened:
            self._state.executions_filled += 1

    async def _latest_unexecuted_signal(
        self, symbol: str, timeframe: Timeframe, start: Timestamp, end: Timestamp
    ) -> int | None:
        """The newest fired signal bar without an execution record."""
        decisions = await self._decisions.get_range(
            "toobit", symbol, timeframe, start=start, end=end
        )
        fired = [record for record in decisions if record.action == "signal"]
        if not fired:
            return None
        latest = fired[-1]
        executions = await self._executions.get_executions(self._portfolio_id)
        for record in executions:
            if (
                record.symbol == symbol
                and record.timeframe is timeframe
                and record.signal_bar_time.epoch_ms == latest.bar_open_time.epoch_ms
            ):
                return None
        return latest.bar_open_time.epoch_ms

    async def _research_upkeep(self, symbol: str, timeframe: Timeframe) -> None:
        """Shadow evaluation, the promotion guard and queue draining."""
        evaluated = await self._research.evaluate_promotions(symbol, timeframe)
        self._state.promotions_evaluated += evaluated
        settings = self._monitoring.settings
        rolled_back = await self._research.apply_promotion_guard(
            symbol,
            timeframe,
            min_trades=settings.promotion_guard_trades,
            floor_r=settings.promotion_guard_floor_r,
        )
        if rolled_back is not None:
            self._state.rollbacks += 1
            await self._alert_rollback(symbol, timeframe, rolled_back)
        if self._orchestrate and await self._monitoring.kill_switch.allows_processing():
            summary = await self._research.orchestrate(
                limit=1, default_window_bars=self._config.market.history_bars
            )
            if summary.ok:
                self._state.jobs_drained += summary.unwrap().drained

    async def _alert_rollback(
        self, symbol: str, timeframe: Timeframe, artifact: str
    ) -> None:
        await self._monitoring.collector.flush()
        raised = await self._monitoring_alert(
            severity=AlertSeverity.EMERGENCY,
            category="research",
            message=(
                f"promotion guard rolled back {symbol} {timeframe.value} "
                f"to {artifact}"
            ),
            dedup_key=f"research.promotion_guard.{symbol}.{timeframe.value}",
        )
        self._state.alerts_raised += int(raised)

    async def _monitoring_alert(
        self,
        *,
        severity: AlertSeverity,
        category: str,
        message: str,
        dedup_key: str,
    ) -> bool:
        return await self._monitoring.raise_alert(
            severity=severity, category=category, message=message, dedup_key=dedup_key
        )

    async def _finish_bar(
        self, symbol: str, timeframe: Timeframe, open_ms: int, total_ms: int
    ) -> None:
        """Alert tick, snapshot cadence, retention and the bar event."""
        self._state.alerts_raised += await self._monitoring.alert_tick()
        now_ms = self._clock.now().epoch_ms
        if now_ms - self._state.last_snapshot_ms >= (
            self._monitoring.settings.snapshot_interval_ms
        ):
            await self._monitoring.capture_snapshot()
            await self._monitoring.prune()
            self._state.last_snapshot_ms = now_ms
            self._state.snapshots_taken += 1
        trace = self._ids.derive_id(f"loop.{symbol}.{timeframe.value}.{open_ms}")
        await self._bus.publish(
            monitoring_event(
                MonitoringEvent.BAR_PROCESSED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                trace_id=trace,
                payload={
                    "symbol": symbol,
                    "timeframe": timeframe.value,
                    "open_time": open_ms,
                    "total_ms": total_ms,
                },
            )
        )

    # --- Failures and reporting -------------------------------------------------------

    async def _staged[T](
        self, stage: str, tags: dict[str, str], awaitable: Awaitable[Result[T]]
    ) -> Result[T]:
        """Await one pipeline stage, timing it and surfacing failures."""
        stage_start = self._clock.now().epoch_ms
        result = await awaitable
        elapsed = self._clock.now().epoch_ms - stage_start
        self._monitoring.collector.metric(
            f"loop.stage.{stage}.ms", float(elapsed), tags=tags
        )
        if not result.ok:
            assert result.error is not None  # Result contract: error set on failure
            raise result.error
        return result

    async def _on_stage_failure(
        self, symbol: str, timeframe: Timeframe, error: ApexError
    ) -> None:
        """Record, alert and continue - the loop never dies on one bar."""
        self._monitoring.collector.error(
            tags={"symbol": symbol, "timeframe": timeframe.value}
        )
        await self._monitoring.collector.flush()
        raised = await self._monitoring_alert(
            severity=AlertSeverity.HIGH,
            category="system",
            message=f"loop stage failed for {symbol} {timeframe.value}: {error.code}",
            dedup_key=f"loop.stage_failure.{symbol}.{timeframe.value}",
        )
        self._state.alerts_raised += int(raised)
        self._logger.failure(
            "loop_bar_failed", error, symbol=symbol, timeframe=timeframe.value
        )

    async def _announce(self, kind: MonitoringEvent) -> None:
        await self._bus.publish(
            monitoring_event(
                kind,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "tracked": len(self._tracked),
                    "live": self._live,
                    "orchestrate": self._orchestrate,
                },
            )
        )

    def _stats(self) -> LoopStats:
        return LoopStats(
            bars_processed=self._state.bars_processed,
            signals_fired=self._state.signals_fired,
            executions_attempted=self._state.executions_attempted,
            executions_filled=self._state.executions_filled,
            alerts_raised=self._state.alerts_raised,
            jobs_drained=self._state.jobs_drained,
            promotions_evaluated=self._state.promotions_evaluated,
            rollbacks=self._state.rollbacks,
            snapshots_taken=self._state.snapshots_taken,
            stream_reconnects=self._state.stream_reconnects,
        )

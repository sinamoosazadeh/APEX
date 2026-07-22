"""Decision computation service (Book II ch. 11/19).

Assembles per-bar decision snapshots (bar + stored feature vector +
persisted assessment + macro liquidity extremes), runs the Central
Decision Kernel over the window and persists the outcomes,
announcing fired signals and run completion on the event bus.
"""

from dataclasses import dataclass
from typing import Final

from apex.contracts.engines import DecisionSnapshot
from apex.core.context import MarketContext
from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.decision.events import DecisionEvent, decision_event
from apex.decision.kernel import CentralDecisionKernel, DecisionOutcome
from apex.decision.store import DecisionRecord, SqliteDecisionRepository
from apex.domain.market import Bar
from apex.features.calculations import last_closed_indices, rolling_extremes
from apex.probability.service import REQUIRED_FEATURES
from apex.probability.store import SqliteProbabilityRepository
from apex.storage.bars import SqliteBarRepository
from apex.storage.features import SqliteFeatureRepository

_SOURCE: Final[str] = "apex.decision.service"
# f_struct_pack extreme window: lookback x 8 (AICE line 322).
_EXTREME_WINDOW_MULTIPLE: Final[int] = 8


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionSummary:
    """Outcome of one decision computation run."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    bars_loaded: int
    bars_decided: int
    signals_fired: int
    pendings: int
    vetoes: int
    records_stored: int


class DecisionService:
    """Turns stored assessments into persisted, audited decisions."""

    def __init__(
        self,
        *,
        exchange_id: str,
        kernel: CentralDecisionKernel,
        macro_timeframe: Timeframe,
        macro_pivot_lookback: int,
        bar_repository: SqliteBarRepository,
        feature_repository: SqliteFeatureRepository,
        probability_repository: SqliteProbabilityRepository,
        decision_repository: SqliteDecisionRepository,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._exchange_id = exchange_id
        self._kernel = kernel
        self._macro_timeframe = macro_timeframe
        self._macro_window = macro_pivot_lookback * _EXTREME_WINDOW_MULTIPLE
        self._bars = bar_repository
        self._features = feature_repository
        self._assessments = probability_repository
        self._decisions = decision_repository
        self._bus = bus
        self._clock = clock
        self._logger = logger

    async def compute(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
        kernel_override: CentralDecisionKernel | None = None,
    ) -> Result[DecisionSummary]:
        """Decide every assessed confirmed bar in [start, end).

        ``kernel_override`` is the runtime injector's hook (Book V
        part 7): a kernel carrying the series' active optimized
        parameters and learning state replaces the config-built one
        for this run only.
        """
        bars = await self._bars.get_range(
            self._exchange_id, symbol, timeframe, start=start, end=end, closed_only=True
        )
        snapshots = await self.build_snapshots(bars, symbol, timeframe, end)
        context = MarketContext(symbol=symbol, timeframe=timeframe, as_of=self._clock.now())
        kernel = kernel_override if kernel_override is not None else self._kernel
        result = kernel.decide_series(snapshots, context)
        if not result.ok:
            assert result.error is not None
            await self._announce_failure(symbol, timeframe, result.error)
            return Result.failure(result.error)
        outcomes = result.unwrap()
        records = [
            self._record(outcome, symbol, timeframe) for outcome in outcomes
        ]
        stored = await self._decisions.upsert(records)
        summary = DecisionSummary(
            exchange=self._exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            bars_loaded=len(bars),
            bars_decided=len(outcomes),
            signals_fired=sum(1 for outcome in outcomes if outcome.action == "signal"),
            pendings=sum(1 for outcome in outcomes if outcome.action == "pending"),
            vetoes=sum(1 for outcome in outcomes if outcome.action == "veto"),
            records_stored=stored,
        )
        await self._announce(summary, outcomes)
        return Result.success(summary)

    async def build_snapshots(
        self,
        bars: list[Bar],
        symbol: str,
        timeframe: Timeframe,
        end: Timestamp,
    ) -> list[DecisionSnapshot]:
        """Assemble decision snapshots (public: the optimizer replays them)."""
        macro_bars = await self._bars.get_range(
            self._exchange_id,
            symbol,
            self._macro_timeframe,
            start=Timestamp(epoch_ms=0),
            end=end,
            closed_only=True,
        )
        assessments = {
            (record.bar_open_time.epoch_ms, record.side): record
            for record in await self._assessments.get_range(
                self._exchange_id, symbol, timeframe,
                start=Timestamp(epoch_ms=0), end=end,
            )
        }
        macro_close = [
            bar.open_time.epoch_ms + bar.timeframe.duration_ms for bar in macro_bars
        ]
        chart_close = [
            bar.open_time.epoch_ms + bar.timeframe.duration_ms for bar in bars
        ]
        mapping = last_closed_indices(chart_close, macro_close)
        snapshots: list[DecisionSnapshot] = []
        for index, bar in enumerate(bars):
            key_long = (bar.open_time.epoch_ms, "long")
            key_short = (bar.open_time.epoch_ms, "short")
            if key_long not in assessments or key_short not in assessments:
                continue
            features = await self._features.get_vector(
                self._exchange_id, symbol, timeframe, bar.open_time
            )
            vector = {feature.name: feature.value for feature in features}
            if not all(name in vector for name in REQUIRED_FEATURES):
                continue
            macro_high, macro_low = self._macro_extremes(macro_bars, mapping[index])
            long_record = assessments[key_long]
            snapshots.append(
                DecisionSnapshot(
                    bar=bar,
                    vector=vector,
                    probability_long=long_record.probability,
                    probability_short=assessments[key_short].probability,
                    channels=long_record.channels,
                    macro_high=macro_high,
                    macro_low=macro_low,
                    ob_long_bottom=vector.get("orderblocks.bull_ob_bottom"),
                    ob_short_top=vector.get("orderblocks.bear_ob_top"),
                )
            )
        return snapshots

    def _macro_extremes(
        self, macro_bars: list[Bar], macro_index: int | None
    ) -> tuple[float | None, float | None]:
        """AICE htf1_hi/lo: shifted rolling extremes on the macro series."""
        if macro_index is None:
            return None, None
        return rolling_extremes(macro_bars, macro_index, self._macro_window)

    def _record(
        self, outcome: DecisionOutcome, symbol: str, timeframe: Timeframe
    ) -> DecisionRecord:
        signal = outcome.signal
        entry = stop = None
        targets: tuple[float, ...] = ()
        if signal is not None:
            entry = float(signal.entry_zone.lower.value)
            stop = float(signal.stop_zone.lower.value)
            targets = tuple(
                float(zone.lower.value) for zone in signal.target_zones
            )
        return DecisionRecord(
            exchange=self._exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            bar_open_time=Timestamp(epoch_ms=outcome.bar_open_ms),
            action=outcome.action,
            direction=outcome.direction.value,
            setup=outcome.setup,
            probability=outcome.probability,
            uncertainty=outcome.uncertainty,
            expected_r=outcome.expected_r,
            contributors=outcome.contributors,
            failed_gates=outcome.failed_gates,
            entry=entry,
            stop=stop,
            targets=targets,
            computed_at=self._clock.now(),
        )

    async def _announce(
        self, summary: DecisionSummary, outcomes: tuple[DecisionOutcome, ...]
    ) -> None:
        for outcome in outcomes:
            if outcome.action != "signal" or outcome.signal is None:
                continue
            await self._bus.publish(
                decision_event(
                    DecisionEvent.SIGNAL_FIRED,
                    occurred_at=self._clock.now(),
                    source=_SOURCE,
                    payload={
                        "symbol": summary.symbol,
                        "timeframe": summary.timeframe.value,
                        "bar_open_ms": outcome.bar_open_ms,
                        "direction": outcome.direction.value,
                        "setup": outcome.setup,
                        "probability": outcome.probability,
                        "expected_r": outcome.expected_r,
                    },
                )
            )
        await self._bus.publish(
            decision_event(
                DecisionEvent.DECIDED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "exchange": summary.exchange,
                    "symbol": summary.symbol,
                    "timeframe": summary.timeframe.value,
                    "bars_decided": summary.bars_decided,
                    "signals_fired": summary.signals_fired,
                    "vetoes": summary.vetoes,
                },
            )
        )
        self._logger.info(
            "decision_completed",
            symbol=summary.symbol,
            timeframe=summary.timeframe.value,
            bars_decided=summary.bars_decided,
            signals_fired=summary.signals_fired,
            vetoes=summary.vetoes,
        )

    async def _announce_failure(
        self, symbol: str, timeframe: Timeframe, error: ApexError
    ) -> None:
        await self._bus.publish(
            decision_event(
                DecisionEvent.FAILED,
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
            "decision_failed",
            symbol=symbol,
            timeframe=timeframe.value,
            error_code=error.code,
        )

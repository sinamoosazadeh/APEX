"""Probability computation service (Book II ch. 8/18).

Reads confirmed bars, assembles each bar's stored feature vector,
runs the confluence engine over the window and persists per-side
assessment records, announcing the outcome on the event bus.

A bar is assessable only when its vector carries every family the
confluence consumes (one sentinel feature per family); bars inside a
family's warmup are skipped, so assessments never run on partial
evidence.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from apex.contracts.engines import FeatureVectorSnapshot
from apex.core.context import MarketContext
from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.domain.market import Bar
from apex.probability.engine import BarProbabilities, ConfluenceProbabilityEngine
from apex.probability.events import ProbabilityEvent, probability_event
from apex.probability.store import AssessmentRecord, SqliteProbabilityRepository
from apex.storage.bars import SqliteBarRepository
from apex.storage.features import SqliteFeatureRepository

_SOURCE: Final[str] = "apex.probability.service"

# One sentinel feature per family: present only after that family's
# warmup, so requiring all of them gates assessment on full evidence.
REQUIRED_FEATURES: Final[tuple[str, ...]] = (
    "structure.trend_direction",
    "liquidity.resting_low",
    "orderblocks.ob_long_confidence",
    "volume.rvol",
    "htf.alignment",
    "smt.correlation_quality",
    "statistical.trend_confidence",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProbabilitySummary:
    """Outcome of one probability computation run."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    bars_loaded: int
    bars_assessed: int
    records_stored: int


class ProbabilityService:
    """Turns stored feature vectors into persisted assessments."""

    def __init__(
        self,
        *,
        exchange_id: str,
        engine: ConfluenceProbabilityEngine,
        bar_repository: SqliteBarRepository,
        feature_repository: SqliteFeatureRepository,
        probability_repository: SqliteProbabilityRepository,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._exchange_id = exchange_id
        self._engine = engine
        self._bars = bar_repository
        self._features = feature_repository
        self._assessments = probability_repository
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
        engine_override: ConfluenceProbabilityEngine | None = None,
    ) -> Result[ProbabilitySummary]:
        """Assess every fully-featured confirmed bar in [start, end).

        ``engine_override`` is the runtime injector's hook (Book V
        part 7): an engine carrying researched learning state replaces
        the config-built one for this run only.
        """
        bars = await self._bars.get_range(
            self._exchange_id, symbol, timeframe, start=start, end=end, closed_only=True
        )
        snapshots = await self._snapshots(bars, symbol, timeframe)
        context = MarketContext(symbol=symbol, timeframe=timeframe, as_of=self._clock.now())
        engine = engine_override if engine_override is not None else self._engine
        result = engine.assess_series_detailed(snapshots, context)
        if not result.ok:
            assert result.error is not None
            await self._announce_failure(symbol, timeframe, result.error)
            return Result.failure(result.error)
        assessed = result.unwrap()
        stored = await self._assessments.upsert(
            [record for bar in assessed for record in self._records(bar, symbol, timeframe)]
        )
        summary = ProbabilitySummary(
            exchange=self._exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            bars_loaded=len(bars),
            bars_assessed=len(assessed),
            records_stored=stored,
        )
        await self._announce_success(summary)
        return Result.success(summary)

    async def _snapshots(
        self,
        bars: Sequence[Bar],
        symbol: str,
        timeframe: Timeframe,
    ) -> list[FeatureVectorSnapshot]:
        snapshots: list[FeatureVectorSnapshot] = []
        for bar in bars:
            features = await self._features.get_vector(
                self._exchange_id, symbol, timeframe, bar.open_time
            )
            vector = {feature.name: feature.value for feature in features}
            if all(name in vector for name in REQUIRED_FEATURES):
                snapshots.append(
                    FeatureVectorSnapshot(
                        bar_open_time=bar.open_time,
                        values=vector,
                        close=float(bar.close.value),
                    )
                )
        return snapshots

    def _records(
        self,
        bar: BarProbabilities,
        symbol: str,
        timeframe: Timeframe,
    ) -> list[AssessmentRecord]:
        channels = {
            name: value
            for pair, name in zip(
                bar.channels.pairs(),
                (
                    "structure", "liquidity", "orderblock", "fvg", "zone", "dna",
                    "kinetic", "delta", "sequence", "trend", "mtf", "smt", "profile",
                ),
                strict=True,
            )
            for name, value in ((f"{name}_long", pair[0]), (f"{name}_short", pair[1]))
        }
        common = {
            "exchange": self._exchange_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "bar_open_time": bar.snapshot.bar_open_time,
            "channels": channels,
            "computed_at": self._clock.now(),
        }
        return [
            AssessmentRecord(
                side="long",
                probability=bar.long.probability.value,
                lower_bound=bar.long.confidence_interval.lower.value,
                upper_bound=bar.long.confidence_interval.upper.value,
                entropy=bar.long.entropy.value,
                raw_score=bar.raw_long,
                sample_size=bar.long.sample_size,
                **common,  # type: ignore[arg-type]
            ),
            AssessmentRecord(
                side="short",
                probability=bar.short.probability.value,
                lower_bound=bar.short.confidence_interval.lower.value,
                upper_bound=bar.short.confidence_interval.upper.value,
                entropy=bar.short.entropy.value,
                raw_score=bar.raw_short,
                sample_size=bar.short.sample_size,
                **common,  # type: ignore[arg-type]
            ),
        ]

    async def _announce_success(self, summary: ProbabilitySummary) -> None:
        await self._bus.publish(
            probability_event(
                ProbabilityEvent.ASSESSED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "exchange": summary.exchange,
                    "symbol": summary.symbol,
                    "timeframe": summary.timeframe.value,
                    "bars_loaded": summary.bars_loaded,
                    "bars_assessed": summary.bars_assessed,
                    "records_stored": summary.records_stored,
                },
            )
        )
        self._logger.info(
            "probability_assessed",
            symbol=summary.symbol,
            timeframe=summary.timeframe.value,
            bars_assessed=summary.bars_assessed,
            records_stored=summary.records_stored,
        )

    async def _announce_failure(
        self, symbol: str, timeframe: Timeframe, error: ApexError
    ) -> None:
        await self._bus.publish(
            probability_event(
                ProbabilityEvent.FAILED,
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
            "probability_failed",
            symbol=symbol,
            timeframe=timeframe.value,
            error_code=error.code,
        )

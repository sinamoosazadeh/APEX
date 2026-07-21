"""Feature computation pipeline (Book II 29.10).

The one sanctioned path features take into the store:

    load confirmed bars -> run registered engines -> validate every
    emitted feature against the registry -> persist idempotently ->
    publish catalog events

Engines are pure; the pipeline owns I/O, validation and announcement.
"""

from dataclasses import dataclass

from apex.contracts.engines import IFeatureEngine
from apex.core.context import MarketContext
from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError, FeatureError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.domain.feature import Feature
from apex.features.events import FeatureEvent, feature_event
from apex.features.registry import FeatureRegistry
from apex.storage.bars import SqliteBarRepository
from apex.storage.features import SqliteFeatureRepository

_SOURCE = "apex.features.pipeline"


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureComputationSummary:
    """Outcome of one feature computation run."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    bars_loaded: int
    engines_run: int
    features_computed: int
    features_stored: int
    families: tuple[str, ...]


class FeatureComputationPipeline:
    """Runs feature engines over stored confirmed bars."""

    def __init__(
        self,
        *,
        exchange_id: str,
        engines: tuple[IFeatureEngine, ...],
        registry: FeatureRegistry,
        bar_repository: SqliteBarRepository,
        feature_repository: SqliteFeatureRepository,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._exchange_id = exchange_id
        self._engines = engines
        self._registry = registry
        self._bars = bar_repository
        self._features = feature_repository
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
    ) -> Result[FeatureComputationSummary]:
        """Compute every registered family over [start, end)."""
        bars = await self._bars.get_range(
            self._exchange_id, symbol, timeframe, start=start, end=end, closed_only=True
        )
        context = MarketContext(
            symbol=symbol, timeframe=timeframe, as_of=self._clock.now()
        )
        computed: list[Feature] = []
        families: set[str] = set()
        for engine in self._engines:
            result = engine.compute(bars, context)
            if not result.ok:
                assert result.error is not None
                await self._announce_failure(symbol, timeframe, engine, result.error)
                return Result.failure(result.error)
            emitted = result.unwrap()
            self._validate(engine, emitted)
            computed.extend(emitted)
            families.add(engine.family)
        stored = await self._features.upsert(computed)
        summary = FeatureComputationSummary(
            exchange=self._exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            bars_loaded=len(bars),
            engines_run=len(self._engines),
            features_computed=len(computed),
            features_stored=stored,
            families=tuple(sorted(families)),
        )
        await self._announce_success(summary)
        return Result.success(summary)

    def _validate(self, engine: IFeatureEngine, features: tuple[Feature, ...]) -> None:
        """Every emitted feature must be declared and family-consistent."""
        for feature in features:
            if not self._registry.is_registered(feature.name):
                raise FeatureError(
                    "engine emitted an unregistered feature",
                    code="FEA-004",
                    details={"name": feature.name, "family": engine.family},
                )
            if feature.family != engine.family:
                raise FeatureError(
                    "engine emitted a feature outside its family",
                    code="FEA-005",
                    details={"name": feature.name, "engine_family": engine.family},
                )

    async def _announce_success(self, summary: FeatureComputationSummary) -> None:
        self._logger.info(
            "features_computed",
            symbol=summary.symbol,
            timeframe=summary.timeframe.value,
            bars=summary.bars_loaded,
            features=summary.features_stored,
            families=",".join(summary.families),
        )
        await self._bus.publish(
            feature_event(
                FeatureEvent.FEATURES_COMPUTED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "exchange": summary.exchange,
                    "symbol": summary.symbol,
                    "timeframe": summary.timeframe.value,
                    "bars_loaded": summary.bars_loaded,
                    "features_stored": summary.features_stored,
                    "families": ",".join(summary.families),
                },
            )
        )

    async def _announce_failure(
        self,
        symbol: str,
        timeframe: Timeframe,
        engine: IFeatureEngine,
        error: ApexError,
    ) -> None:
        self._logger.failure(
            "feature_computation_failed", error, symbol=symbol, family=engine.family
        )
        await self._bus.publish(
            feature_event(
                FeatureEvent.FEATURES_FAILED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "symbol": symbol,
                    "timeframe": timeframe.value,
                    "family": engine.family,
                    "error_code": error.code,
                    "error_message": error.message,
                },
            )
        )

"""Feature platform plugin (Book II 3.23: features are plugins).

Wires the Phase 4 slice: registry -> store -> engines -> pipeline ->
kernel module. Engine parameters come from the ``features`` section of
market.yaml, falling back to the AICE input defaults (Constitution 3.7:
tunables are data).
"""

from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig, ConfigSection
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel, Timeframe
from apex.core.exceptions import ConfigurationError
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.features.htf.definitions import htf_definitions
from apex.features.htf.engine import HtfContextEngine, HtfParams
from apex.features.liquidity.definitions import liquidity_definitions
from apex.features.liquidity.engine import LiquidityEngine, LiquidityParams
from apex.features.orderblocks.definitions import orderblock_definitions
from apex.features.orderblocks.engine import OrderBlockEngine, OrderBlockParams
from apex.features.pipeline import FeatureComputationPipeline
from apex.features.registry import FeatureRegistry
from apex.features.smt.definitions import smt_definitions
from apex.features.smt.engine import SmtEngine, SmtParams
from apex.features.statistical.definitions import statistical_definitions
from apex.features.statistical.engine import StatisticalEngine, StatisticalParams
from apex.features.structure.definitions import structure_definitions
from apex.features.structure.engine import MarketStructureEngine, StructureParams
from apex.features.volume.definitions import volume_definitions
from apex.features.volume.engine import VolumeEngine, VolumeParams
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest
from apex.storage.bars import SqliteBarRepository
from apex.storage.features import SqliteFeatureRepository

FEATURES_DATABASE_FILENAME = "features.sqlite"


class FeaturePlatformModule:
    """Kernel module owning the feature store lifecycle."""

    MODULE_NAME = "feature_platform"

    def __init__(
        self,
        *,
        repository: SqliteFeatureRepository,
        logger: StructuredLogger,
    ) -> None:
        self._repository = repository
        self._logger = logger
        self._running = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Consumes stored bars; starts after the data platform."""
        return ("market_data",)

    async def start(self) -> None:
        """Open the feature store."""
        await self._repository.open()
        self._running = True
        self._logger.info("feature_platform_started")

    async def stop(self) -> None:
        """Close the feature store."""
        self._running = False
        await self._repository.close()
        self._logger.info("feature_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the store is open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


def _family_numbers(features_config: ConfigSection, family: str) -> dict[str, float]:
    """Read a family's numeric overrides from market.features config."""
    raw = features_config.get(family, {})
    if not isinstance(raw, dict):
        raise ConfigurationError(
            f"market.features.{family} must be a mapping",
            code="CFG-024",
            details={"family": family},
        )
    numbers: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(
                f"market.features.{family} values must be numbers",
                code="CFG-025",
                details={"family": family, "key": key},
            )
        numbers[key] = float(value)
    return numbers


def _structure_params(features_config: ConfigSection) -> StructureParams:
    """Structure params: config overrides on AICE defaults."""
    numbers = _family_numbers(features_config, "structure")
    defaults = StructureParams()
    return StructureParams(
        pivot_lookback=int(numbers.get("pivot_lookback", defaults.pivot_lookback)),
        atr_length=int(numbers.get("atr_length", defaults.atr_length)),
        displacement_body_atr=numbers.get(
            "displacement_body_atr", defaults.displacement_body_atr
        ),
        equal_tolerance_atr=numbers.get(
            "equal_tolerance_atr", defaults.equal_tolerance_atr
        ),
        break_decay=numbers.get("break_decay", defaults.break_decay),
    )


def _liquidity_params(features_config: ConfigSection) -> LiquidityParams:
    """Liquidity params: config overrides on AICE defaults."""
    numbers = _family_numbers(features_config, "liquidity")
    defaults = LiquidityParams()
    return LiquidityParams(
        chart_lookback=int(numbers.get("chart_lookback", defaults.chart_lookback)),
        internal_lookback=int(
            numbers.get("internal_lookback", defaults.internal_lookback)
        ),
        external_lookback=int(
            numbers.get("external_lookback", defaults.external_lookback)
        ),
        atr_length=int(numbers.get("atr_length", defaults.atr_length)),
        equal_tolerance_atr=numbers.get(
            "equal_tolerance_atr", defaults.equal_tolerance_atr
        ),
        liquidity_decay=numbers.get("liquidity_decay", defaults.liquidity_decay),
        ema_length=int(numbers.get("ema_length", defaults.ema_length)),
    )


def _orderblock_params(features_config: ConfigSection) -> OrderBlockParams:
    """OB/FVG params: config overrides on AICE defaults."""
    numbers = _family_numbers(features_config, "orderblocks")
    defaults = OrderBlockParams()
    return OrderBlockParams(
        pivot_lookback=int(numbers.get("pivot_lookback", defaults.pivot_lookback)),
        atr_length=int(numbers.get("atr_length", defaults.atr_length)),
        displacement_body_atr=numbers.get(
            "displacement_body_atr", defaults.displacement_body_atr
        ),
        break_decay=numbers.get("break_decay", defaults.break_decay),
        scan_lookback=int(numbers.get("scan_lookback", defaults.scan_lookback)),
        scan_cap=int(numbers.get("scan_cap", defaults.scan_cap)),
        ob_decay=numbers.get("ob_decay", defaults.ob_decay),
        fvg_decay=numbers.get("fvg_decay", defaults.fvg_decay),
        max_live_objects=int(numbers.get("max_live_objects", defaults.max_live_objects)),
        max_object_age=int(numbers.get("max_object_age", defaults.max_object_age)),
        min_fvg_size_atr=numbers.get("min_fvg_size_atr", defaults.min_fvg_size_atr),
        volume_sma_length=int(numbers.get("volume_sma_length", defaults.volume_sma_length)),
        range_sma_length=int(numbers.get("range_sma_length", defaults.range_sma_length)),
        zpf_fast_length=int(numbers.get("zpf_fast_length", defaults.zpf_fast_length)),
        zpf_slow_length=int(numbers.get("zpf_slow_length", defaults.zpf_slow_length)),
        htf_pivot_lookback=int(
            numbers.get("htf_pivot_lookback", defaults.htf_pivot_lookback)
        ),
        htf_ema_length=int(numbers.get("htf_ema_length", defaults.htf_ema_length)),
    )


def _volume_params(features_config: ConfigSection) -> VolumeParams:
    """Volume family params: config overrides on AICE defaults."""
    numbers = _family_numbers(features_config, "volume")
    defaults = VolumeParams()
    return VolumeParams(
        atr_length=int(numbers.get("atr_length", defaults.atr_length)),
        volume_sma_length=int(numbers.get("volume_sma_length", defaults.volume_sma_length)),
        range_sma_length=int(numbers.get("range_sma_length", defaults.range_sma_length)),
        normalization_window=int(
            numbers.get("normalization_window", defaults.normalization_window)
        ),
        rank_window=int(numbers.get("rank_window", defaults.rank_window)),
        forecast_length=int(numbers.get("forecast_length", defaults.forecast_length)),
        winsor_z=numbers.get("winsor_z", defaults.winsor_z),
        zpf_fast_length=int(numbers.get("zpf_fast_length", defaults.zpf_fast_length)),
        zpf_slow_length=int(numbers.get("zpf_slow_length", defaults.zpf_slow_length)),
        profile_length=int(numbers.get("profile_length", defaults.profile_length)),
        profile_bins=int(numbers.get("profile_bins", defaults.profile_bins)),
        delta_roll_length=int(numbers.get("delta_roll_length", defaults.delta_roll_length)),
        delta_bias_ema_length=int(
            numbers.get("delta_bias_ema_length", defaults.delta_bias_ema_length)
        ),
    )


def _timeframe_from_minutes(minutes: int, *, family: str, key: str) -> Timeframe:
    """Resolve a macro timeframe declared as minutes in config."""
    duration_ms = minutes * 60_000
    for timeframe in Timeframe:
        if timeframe.duration_ms == duration_ms:
            return timeframe
    raise ConfigurationError(
        f"market.features.{family}.{key} does not map to a known timeframe",
        code="CFG-026",
        details={"family": family, "key": key, "minutes": minutes},
    )


def _macro_timeframes(features_config: ConfigSection) -> tuple[Timeframe, Timeframe]:
    """Macro timeframes shared by the HTF family and OB/FVG context."""
    numbers = _family_numbers(features_config, "htf")
    macro1 = _timeframe_from_minutes(
        int(numbers.get("macro1_minutes", 60)), family="htf", key="macro1_minutes"
    )
    macro2 = _timeframe_from_minutes(
        int(numbers.get("macro2_minutes", 240)), family="htf", key="macro2_minutes"
    )
    return macro1, macro2


def _htf_params(features_config: ConfigSection) -> HtfParams:
    """HTF family params: config overrides on AICE defaults."""
    numbers = _family_numbers(features_config, "htf")
    defaults = HtfParams()
    return HtfParams(
        pivot_lookback=int(numbers.get("pivot_lookback", defaults.pivot_lookback)),
        ema_length=int(numbers.get("ema_length", defaults.ema_length)),
    )


def _smt_params(features_config: ConfigSection) -> SmtParams:
    """SMT family params: config overrides on AICE defaults."""
    numbers = _family_numbers(features_config, "smt")
    defaults = SmtParams()
    return SmtParams(
        pivot_lookback=int(numbers.get("pivot_lookback", defaults.pivot_lookback)),
        max_pivot_age=int(numbers.get("max_pivot_age", defaults.max_pivot_age)),
        correlation_length=int(
            numbers.get("correlation_length", defaults.correlation_length)
        ),
        correlation_minimum=numbers.get(
            "correlation_minimum", defaults.correlation_minimum
        ),
        correlation_slope_length=int(
            numbers.get("correlation_slope_length", defaults.correlation_slope_length)
        ),
        decay_rate=numbers.get("decay_rate", defaults.decay_rate),
        min_score=numbers.get("min_score", defaults.min_score),
    )


def _statistical_params(features_config: ConfigSection) -> StatisticalParams:
    """Statistical family params: config overrides on AICE defaults."""
    numbers = _family_numbers(features_config, "statistical")
    defaults = StatisticalParams()
    return StatisticalParams(
        atr_length=int(numbers.get("atr_length", defaults.atr_length)),
        adx_length=int(numbers.get("adx_length", defaults.adx_length)),
        adx_trend_threshold=numbers.get(
            "adx_trend_threshold", defaults.adx_trend_threshold
        ),
        efficiency_length=int(numbers.get("efficiency_length", defaults.efficiency_length)),
        entropy_window=int(numbers.get("entropy_window", defaults.entropy_window)),
        normalization_window=int(
            numbers.get("normalization_window", defaults.normalization_window)
        ),
        rank_window=int(numbers.get("rank_window", defaults.rank_window)),
        range_sma_length=int(numbers.get("range_sma_length", defaults.range_sma_length)),
        wavetrend_channel=int(numbers.get("wavetrend_channel", defaults.wavetrend_channel)),
        wavetrend_average=int(numbers.get("wavetrend_average", defaults.wavetrend_average)),
        stc_cycle=int(numbers.get("stc_cycle", defaults.stc_cycle)),
        stc_fast=int(numbers.get("stc_fast", defaults.stc_fast)),
        stc_slow=int(numbers.get("stc_slow", defaults.stc_slow)),
        cci_length=int(numbers.get("cci_length", defaults.cci_length)),
    )


def _smt_references(symbols: tuple[str, ...]) -> dict[str, str]:
    """Each symbol references its first peer (AICE auto-profile analog)."""
    references: dict[str, str] = {}
    for symbol in symbols:
        peers = [candidate for candidate in symbols if candidate != symbol]
        if peers:
            references[symbol] = peers[0]
    return references


class FeaturePlatformPlugin:
    """Builds the feature platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="feature_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.FEATURE,
            api_version=SemanticVersion(1, 0, 0),
            description="Feature registry, store, pipeline and the migrated AICE families",
            stability=StabilityLevel.BETA,
            requires=("storage_core", "toobit_connector"),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the feature platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]

        structure_params = _structure_params(config.market.features)
        liquidity_params = _liquidity_params(config.market.features)
        orderblock_params = _orderblock_params(config.market.features)
        volume_params = _volume_params(config.market.features)
        htf_params = _htf_params(config.market.features)
        smt_params = _smt_params(config.market.features)
        statistical_params = _statistical_params(config.market.features)
        macro = _macro_timeframes(config.market.features)
        references = _smt_references(config.market.symbols)
        engines = (
            MarketStructureEngine(params=structure_params, clock=clock),
            LiquidityEngine(params=liquidity_params, clock=clock),
            OrderBlockEngine(
                params=orderblock_params, clock=clock, macro_timeframes=macro
            ),
            VolumeEngine(params=volume_params, clock=clock),
            HtfContextEngine(params=htf_params, macro_timeframes=macro, clock=clock),
            SmtEngine(params=smt_params, references=references, clock=clock),
            StatisticalEngine(params=statistical_params, clock=clock),
        )
        registry = FeatureRegistry()
        registry.register_all(structure_definitions(structure_params))
        registry.register_all(liquidity_definitions(liquidity_params))
        registry.register_all(orderblock_definitions(orderblock_params))
        registry.register_all(volume_definitions(volume_params))
        registry.register_all(htf_definitions(htf_params))
        registry.register_all(smt_definitions(smt_params))
        registry.register_all(statistical_definitions(statistical_params))
        repository = SqliteFeatureRepository(
            database_path=Path(config.system.data_dir) / FEATURES_DATABASE_FILENAME,
        )
        pipeline = FeatureComputationPipeline(
            exchange_id="toobit",
            engines=engines,
            registry=registry,
            bar_repository=container.resolve(SqliteBarRepository),
            feature_repository=repository,
            bus=bus,
            clock=clock,
            logger=loggers.get("features.pipeline"),
        )
        container.register_instance(FeatureRegistry, registry)
        container.register_instance(SqliteFeatureRepository, repository)
        container.register_instance(FeatureComputationPipeline, pipeline)
        return [
            FeaturePlatformModule(
                repository=repository,
                logger=loggers.get("features.module"),
            )
        ]


APEX_PLUGIN = FeaturePlatformPlugin()

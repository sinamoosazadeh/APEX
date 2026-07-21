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
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.exceptions import ConfigurationError
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.features.liquidity.definitions import liquidity_definitions
from apex.features.liquidity.engine import LiquidityEngine, LiquidityParams
from apex.features.orderblocks.definitions import orderblock_definitions
from apex.features.orderblocks.engine import OrderBlockEngine, OrderBlockParams
from apex.features.pipeline import FeatureComputationPipeline
from apex.features.registry import FeatureRegistry
from apex.features.structure.definitions import structure_definitions
from apex.features.structure.engine import MarketStructureEngine, StructureParams
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
    )


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
        engines = (
            MarketStructureEngine(params=structure_params, clock=clock),
            LiquidityEngine(params=liquidity_params, clock=clock),
            OrderBlockEngine(params=orderblock_params, clock=clock),
        )
        registry = FeatureRegistry()
        registry.register_all(structure_definitions(structure_params))
        registry.register_all(liquidity_definitions(liquidity_params))
        registry.register_all(orderblock_definitions(orderblock_params))
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

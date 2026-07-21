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


def _structure_params(features_config: ConfigSection) -> StructureParams:
    """Build engine params from config overrides on AICE defaults."""
    raw = features_config.get("structure", {})
    if not isinstance(raw, dict):
        raise ConfigurationError(
            "market.features.structure must be a mapping",
            code="CFG-024",
        )
    defaults = StructureParams()
    def _number(key: str, fallback: float) -> float:
        value = raw.get(key, fallback)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(
                "market.features.structure values must be numbers",
                code="CFG-025",
                details={"key": key},
            )
        return float(value)

    return StructureParams(
        pivot_lookback=int(_number("pivot_lookback", defaults.pivot_lookback)),
        atr_length=int(_number("atr_length", defaults.atr_length)),
        displacement_body_atr=_number(
            "displacement_body_atr", defaults.displacement_body_atr
        ),
        equal_tolerance_atr=_number("equal_tolerance_atr", defaults.equal_tolerance_atr),
        break_decay=_number("break_decay", defaults.break_decay),
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
            description="Feature registry, store, pipeline and the structure family",
            stability=StabilityLevel.BETA,
            requires=("storage_core", "toobit_connector"),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the feature platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]

        params = _structure_params(config.market.features)
        engine = MarketStructureEngine(params=params, clock=clock)
        registry = FeatureRegistry()
        registry.register_all(structure_definitions(params))
        repository = SqliteFeatureRepository(
            database_path=Path(config.system.data_dir) / FEATURES_DATABASE_FILENAME,
        )
        pipeline = FeatureComputationPipeline(
            exchange_id="toobit",
            engines=(engine,),
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

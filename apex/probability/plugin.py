"""Probability platform plugin (Book II ch. 8/18, 3.23).

Wires the Phase 5 slice: confluence engine -> assessment store ->
computation service -> kernel module. Engine parameters come from the
``probability`` section of market.yaml, falling back to the AICE
defaults (Constitution 3.7: tunables are data).
"""

from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig, ConfigSection
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.exceptions import ConfigurationError
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest
from apex.probability.engine import ConfluenceParams, ConfluenceProbabilityEngine
from apex.probability.service import ProbabilityService
from apex.probability.store import SqliteProbabilityRepository
from apex.storage.bars import SqliteBarRepository
from apex.storage.features import SqliteFeatureRepository

PROBABILITY_DATABASE_FILENAME = "probability.sqlite"


class ProbabilityPlatformModule:
    """Kernel module owning the assessment store lifecycle."""

    MODULE_NAME = "probability_platform"

    def __init__(
        self,
        *,
        repository: SqliteProbabilityRepository,
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
        """Consumes stored features; starts after the feature platform."""
        return ("feature_platform",)

    async def start(self) -> None:
        """Open the assessment store."""
        await self._repository.open()
        self._running = True
        self._logger.info("probability_platform_started")

    async def stop(self) -> None:
        """Close the assessment store."""
        self._running = False
        await self._repository.close()
        self._logger.info("probability_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the store is open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


def probability_params_from_config(section: ConfigSection) -> ConfluenceParams:
    """Confluence params: config overrides on AICE defaults."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "market.probability must be a mapping",
            code="CFG-027",
            details={},
        )
    numbers: dict[str, float] = {}
    for key, value in section.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(
                "market.probability values must be numbers",
                code="CFG-028",
                details={"key": key},
            )
        numbers[key] = float(value)
    defaults = ConfluenceParams()
    return ConfluenceParams(
        momentum_length=int(numbers.get("momentum_length", defaults.momentum_length)),
        calibration_offset=numbers.get(
            "calibration_offset", defaults.calibration_offset
        ),
        calibration_gain_base=numbers.get(
            "calibration_gain_base", defaults.calibration_gain_base
        ),
        calibration_gain_slope=numbers.get(
            "calibration_gain_slope", defaults.calibration_gain_slope
        ),
        probability_floor=numbers.get("probability_floor", defaults.probability_floor),
        probability_ceiling=numbers.get(
            "probability_ceiling", defaults.probability_ceiling
        ),
        uncertainty_scale=numbers.get("uncertainty_scale", defaults.uncertainty_scale),
    )


class ProbabilityPlatformPlugin:
    """Builds the probability platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="probability_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Confluence probability engine, assessment store and service",
            stability=StabilityLevel.BETA,
            requires=("feature_platform",),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the probability platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        params = probability_params_from_config(config.market.probability)
        engine = ConfluenceProbabilityEngine(params=params, clock=clock)
        repository = SqliteProbabilityRepository(
            database_path=Path(config.system.data_dir) / PROBABILITY_DATABASE_FILENAME,
        )
        service = ProbabilityService(
            exchange_id="toobit",
            engine=engine,
            bar_repository=container.resolve(SqliteBarRepository),
            feature_repository=container.resolve(SqliteFeatureRepository),
            probability_repository=repository,
            bus=bus,
            clock=clock,
            logger=loggers.get("probability.service"),
        )
        container.register_instance(ConfluenceProbabilityEngine, engine)
        container.register_instance(SqliteProbabilityRepository, repository)
        container.register_instance(ProbabilityService, service)
        return [
            ProbabilityPlatformModule(
                repository=repository,
                logger=loggers.get("probability.module"),
            )
        ]


APEX_PLUGIN = ProbabilityPlatformPlugin()

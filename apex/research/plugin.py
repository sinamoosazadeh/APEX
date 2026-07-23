"""Research platform plugin (Book II ch. 14/23; Book V part 7).

Wires the Phase 11 slice: the research store (jobs, active versions,
experiments, learning artifacts) -> the research service (study +
orchestration + runtime injection) -> kernel module. Requires the
portfolio and execution platforms: studies read their durable records.
Learning parameters come from the ``learning`` section of
research.yaml, falling back to the AICE input defaults; the shadow
promotion inputs (Book II 14.24) come from its ``promotion`` section.
"""

from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig, ConfigSection
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.exceptions import ConfigurationError
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.decision.plugin import decision_params_from_config
from apex.decision.service import DecisionService
from apex.decision.store import SqliteDecisionRepository
from apex.domain.learning import LearningParams
from apex.execution.store import SqliteExecutionRepository
from apex.kernel.container import ServiceContainer
from apex.optimization.objective import ObjectiveWeights
from apex.optimization.risk.service import RiskOptimizationService
from apex.optimization.signal.service import SignalOptimizationService
from apex.plugins.contract import PluginManifest
from apex.portfolio.config import portfolio_settings
from apex.portfolio.store import SqlitePortfolioRepository
from apex.probability.store import SqliteProbabilityRepository
from apex.research.service import ResearchService
from apex.research.store import SqliteResearchRepository
from apex.security.service import SecurityService
from apex.storage.bars import SqliteBarRepository

RESEARCH_DATABASE_FILENAME = "research.sqlite"


def _learning_params(section: ConfigSection) -> LearningParams:
    """Learning inputs: numeric config overrides on AICE defaults."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "research.learning must be a mapping", code="CFG-039", details={}
        )
    numbers = {
        key: float(value)
        for key, value in section.items()
        if not isinstance(value, bool) and isinstance(value, (int, float))
    }
    defaults = LearningParams()
    return LearningParams(
        feature_prior=numbers.get("feature_prior", defaults.feature_prior),
        adapt_strength=numbers.get("adapt_strength", defaults.adapt_strength),
        feature_minimum_sample=numbers.get(
            "feature_minimum_sample", defaults.feature_minimum_sample
        ),
        calibration_minimum_sample=numbers.get(
            "calibration_minimum_sample", defaults.calibration_minimum_sample
        ),
        calibration_maximum_blend=numbers.get(
            "calibration_maximum_blend", defaults.calibration_maximum_blend
        ),
    )


def _promotion_number(section: ConfigSection, key: str, default: float) -> float:
    """One numeric shadow-promotion input with its default."""
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            f"research.promotion.{key} must be a number",
            code="CFG-042",
            details={"found": repr(value)},
        )
    return float(value)


class ResearchPlatformModule:
    """Kernel module owning the research store lifecycle."""

    MODULE_NAME = "research_platform"

    def __init__(
        self,
        *,
        repository: SqliteResearchRepository,
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
        """Studies read portfolio and execution records."""
        return ("portfolio_platform", "execution_platform")

    async def start(self) -> None:
        """Open the research store."""
        await self._repository.open()
        self._running = True
        self._logger.info("research_platform_started")

    async def stop(self) -> None:
        """Close the research store."""
        self._running = False
        await self._repository.close()
        self._logger.info("research_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the store is open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


class ResearchPlatformPlugin:
    """Builds the research platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="research_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Research studies, experiment registry, orchestrator",
            stability=StabilityLevel.BETA,
            requires=(
                "portfolio_platform",
                "execution_platform",
                "security_platform",
            ),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the research platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        research_section = config.section("research")
        learning_raw = research_section.get("learning", {})
        learning = _learning_params(
            learning_raw if isinstance(learning_raw, dict) else {}
        )
        promotion_raw = research_section.get("promotion", {})
        promotion = promotion_raw if isinstance(promotion_raw, dict) else {}
        repository = SqliteResearchRepository(
            database_path=Path(config.system.data_dir) / RESEARCH_DATABASE_FILENAME,
        )
        service = ResearchService(
            exchange_id="toobit",
            portfolio_id=portfolio_settings(
                config.section("portfolio")
            ).portfolio_id,
            learning_params=learning,
            store=repository,
            portfolio_repository=container.resolve(SqlitePortfolioRepository),
            decision_repository=container.resolve(SqliteDecisionRepository),
            probability_repository=container.resolve(SqliteProbabilityRepository),
            execution_repository=container.resolve(SqliteExecutionRepository),
            signal_service=container.resolve(SignalOptimizationService),
            risk_service=container.resolve(RiskOptimizationService),
            decision_service=container.resolve(DecisionService),
            bar_repository=container.resolve(SqliteBarRepository),
            base_params=decision_params_from_config(config.market.decision),
            weights=ObjectiveWeights(),
            shadow_min_bars=int(_promotion_number(promotion, "shadow_min_bars", 96)),
            shadow_horizon_bars=int(
                _promotion_number(promotion, "shadow_horizon_bars", 48)
            ),
            shadow_tolerance=_promotion_number(promotion, "shadow_tolerance", 0.05),
            artifact_verifier=container.resolve(SecurityService).verify,
            bus=bus,
            clock=clock,
            logger=loggers.get("research.service"),
        )
        container.register_instance(SqliteResearchRepository, repository)
        container.register_instance(ResearchService, service)
        return [
            ResearchPlatformModule(
                repository=repository,
                logger=loggers.get("research.module"),
            )
        ]


APEX_PLUGIN = ResearchPlatformPlugin()

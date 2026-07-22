"""Portfolio platform plugin (Book II ch. 13/21, Book I ch. 8).

Wires the Phase 9 slice: portfolio settings (portfolio.yaml) -> the
Portfolio Intelligence Engine -> portfolio store -> rebuild service ->
kernel module. The engine shares the kernel's same-bar collision
convention (market.yaml ``decision.conservative_resolver``), so the
durable positions never drift from the kernel's virtual ledger.
"""

from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.decision.store import SqliteDecisionRepository
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest
from apex.portfolio.config import portfolio_settings
from apex.portfolio.engine import PortfolioEngine
from apex.portfolio.service import PortfolioService
from apex.portfolio.store import SqlitePortfolioRepository
from apex.storage.bars import SqliteBarRepository

PORTFOLIO_DATABASE_FILENAME = "portfolio.sqlite"


class PortfolioPlatformModule:
    """Kernel module owning the portfolio store lifecycle."""

    MODULE_NAME = "portfolio_platform"

    def __init__(
        self,
        *,
        repository: SqlitePortfolioRepository,
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
        """Consumes decisions; starts after the decision platform."""
        return ("decision_platform",)

    async def start(self) -> None:
        """Open the portfolio store."""
        await self._repository.open()
        self._running = True
        self._logger.info("portfolio_platform_started")

    async def stop(self) -> None:
        """Close the portfolio store."""
        self._running = False
        await self._repository.close()
        self._logger.info("portfolio_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the store is open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


class PortfolioPlatformPlugin:
    """Builds the portfolio platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="portfolio_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Portfolio Intelligence Engine, store and rebuild service",
            stability=StabilityLevel.BETA,
            requires=("decision_platform",),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the portfolio platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        settings = portfolio_settings(config.section("portfolio"))
        decision_section = config.market.decision
        conservative = True
        if isinstance(decision_section, dict):
            value = decision_section.get("conservative_resolver", True)
            conservative = value if isinstance(value, bool) else True
        engine = PortfolioEngine(
            settings=settings, clock=clock, conservative_resolver=conservative
        )
        repository = SqlitePortfolioRepository(
            database_path=Path(config.system.data_dir) / PORTFOLIO_DATABASE_FILENAME,
        )
        service = PortfolioService(
            exchange_id="toobit",
            portfolio_id=settings.portfolio_id,
            engine=engine,
            bar_repository=container.resolve(SqliteBarRepository),
            decision_repository=container.resolve(SqliteDecisionRepository),
            portfolio_repository=repository,
            bus=bus,
            clock=clock,
            logger=loggers.get("portfolio.service"),
        )
        container.register_instance(PortfolioEngine, engine)
        container.register_instance(SqlitePortfolioRepository, repository)
        container.register_instance(PortfolioService, service)
        return [
            PortfolioPlatformModule(
                repository=repository,
                logger=loggers.get("portfolio.module"),
            )
        ]


APEX_PLUGIN = PortfolioPlatformPlugin()

"""Execution platform plugin (Book II ch. 12/20, Book VII).

Wires the Phase 10 slice: execution settings (exchange.yaml) -> the
signed Toobit trading client (env credentials; absent credentials
leave the platform paper-only) -> paper and live execution engines ->
execution audit store -> execution service -> kernel module. Requires
the portfolio platform: every execution re-checks admission there.
"""

from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.decision.store import SqliteDecisionRepository
from apex.execution.config import execution_settings
from apex.execution.engine import LiveExecutionEngine
from apex.execution.paper import PaperExecutionEngine
from apex.execution.service import ExecutionService
from apex.execution.store import SqliteExecutionRepository
from apex.execution.trading.client import ToobitTradingClient, TradingCredentials
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest
from apex.portfolio.config import portfolio_settings
from apex.portfolio.engine import PortfolioEngine
from apex.portfolio.store import SqlitePortfolioRepository
from apex.storage.bars import SqliteBarRepository

EXECUTION_DATABASE_FILENAME = "executions.sqlite"


class ExecutionPlatformModule:
    """Kernel module owning the trading client and audit store."""

    MODULE_NAME = "execution_platform"

    def __init__(
        self,
        *,
        client: ToobitTradingClient,
        repository: SqliteExecutionRepository,
        logger: StructuredLogger,
    ) -> None:
        self._client = client
        self._repository = repository
        self._logger = logger
        self._running = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Re-checks admission; starts after the portfolio platform."""
        return ("portfolio_platform",)

    async def start(self) -> None:
        """Open the audit store and the trading session."""
        await self._repository.open()
        await self._client.open()
        self._running = True
        self._logger.info(
            "execution_platform_started",
            trading_enabled=self._client.can_trade,
        )

    async def stop(self) -> None:
        """Close the trading session and the audit store."""
        self._running = False
        await self._client.close()
        await self._repository.close()
        self._logger.info("execution_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the store and session are open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


class ExecutionPlatformPlugin:
    """Builds the execution platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="execution_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Paper and live execution engines, trading client, audit",
            stability=StabilityLevel.BETA,
            requires=("portfolio_platform",),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the execution platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        exchange_section = config.section("exchange")
        raw_execution = exchange_section.get("execution", {})
        settings = execution_settings(
            raw_execution if isinstance(raw_execution, dict) else {}
        )
        client = ToobitTradingClient(
            base_url=config.toobit.base_url,
            request_timeout_ms=config.toobit.request_timeout_ms,
            recv_window_ms=settings.recv_window_ms,
            max_retries=settings.max_retries,
            retry_backoff_ms=config.toobit.retry_backoff_ms,
            clock=clock,
            logger=loggers.get("execution.client"),
            credentials=TradingCredentials.from_environment(),
        )
        paper = PaperExecutionEngine(
            settings=settings,
            bar_repository=container.resolve(SqliteBarRepository),
            clock=clock,
            logger=loggers.get("execution.paper"),
        )
        live = LiveExecutionEngine(
            client=client,
            settings=settings,
            clock=clock,
            logger=loggers.get("execution.live"),
        )
        repository = SqliteExecutionRepository(
            database_path=Path(config.system.data_dir) / EXECUTION_DATABASE_FILENAME,
        )
        service = ExecutionService(
            exchange_id="toobit",
            settings=settings,
            portfolio_settings=portfolio_settings(config.section("portfolio")),
            run_mode=config.system.run_mode,
            decision_repository=container.resolve(SqliteDecisionRepository),
            portfolio_repository=container.resolve(SqlitePortfolioRepository),
            portfolio_engine=container.resolve(PortfolioEngine),
            paper_engine=paper,
            live_engine=live,
            execution_repository=repository,
            bus=bus,
            clock=clock,
            logger=loggers.get("execution.service"),
        )
        container.register_instance(ToobitTradingClient, client)
        container.register_instance(PaperExecutionEngine, paper)
        container.register_instance(LiveExecutionEngine, live)
        container.register_instance(SqliteExecutionRepository, repository)
        container.register_instance(ExecutionService, service)
        return [
            ExecutionPlatformModule(
                client=client,
                repository=repository,
                logger=loggers.get("execution.module"),
            )
        ]


APEX_PLUGIN = ExecutionPlatformPlugin()

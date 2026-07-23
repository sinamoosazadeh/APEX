"""Monitoring platform plugin (Book II ch. 26; Book I ch. 10).

Wires the Phase 12 slice: telemetry settings (telemetry.yaml) -> the
monitoring store -> collector (bus-subscribed at module start) ->
health engine over the live module registry -> kill switch (with a
best-effort venue order canceller) -> alert engine -> error budget ->
monitoring service -> the live operational loop. Requires the
research platform (and transitively everything below): the loop
drives every platform and the ops feed reads their stores.
"""

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Final

from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.exceptions import ApexError
from apex.core.identity import IdProvider
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.time.clock import Clock
from apex.core.versioning import SemanticVersion
from apex.data.catchup import CatchUpService
from apex.data.streaming import MarketStreamService
from apex.decision.service import DecisionService
from apex.decision.store import SqliteDecisionRepository
from apex.execution.config import execution_settings
from apex.execution.flatten import flatten_positions
from apex.execution.service import ExecutionService
from apex.execution.store import SqliteExecutionRepository
from apex.execution.trading.client import ToobitTradingClient
from apex.execution.trading.translator import contract_symbol, unwrap
from apex.features.pipeline import FeatureComputationPipeline
from apex.kernel.container import ServiceContainer
from apex.kernel.health import HealthMonitor
from apex.kernel.modules import ModuleRegistry
from apex.monitoring.alerts import AlertEngine
from apex.monitoring.collector import TelemetryCollector
from apex.monitoring.config import monitoring_settings
from apex.monitoring.health import HealthEngine
from apex.monitoring.killswitch import (
    KillSwitchEngine,
    OrderCanceller,
    PositionFlattener,
    TransitionAuditor,
)
from apex.monitoring.loop import OperationsLoopService
from apex.monitoring.service import MonitoringService
from apex.monitoring.slo import ErrorBudgetTracker
from apex.monitoring.store import SqliteMonitoringRepository
from apex.plugins.contract import PluginManifest
from apex.portfolio.config import portfolio_settings
from apex.portfolio.store import SqlitePortfolioRepository
from apex.probability.service import ProbabilityService
from apex.research.service import ResearchService
from apex.research.store import SqliteResearchRepository
from apex.security.service import SecurityService
from apex.storage.bars import SqliteBarRepository

MONITORING_DATABASE_FILENAME: Final[str] = "monitoring.sqlite"
_OPEN_ORDERS_PATH: Final[str] = "/api/v2/futures/open-orders"


def _order_canceller(
    client: ToobitTradingClient,
    symbols: tuple[str, ...],
    contract_infix: str,
    logger: StructuredLogger,
) -> OrderCanceller:
    """Best-effort venue order cancellation for SAFE_MODE (10.25)."""

    async def cancel_all() -> int:
        if not client.can_trade:
            return 0
        canceled = 0
        for symbol in symbols:
            contract = contract_symbol(symbol, contract_infix)
            payload = unwrap(await client.open_orders(contract), path=_OPEN_ORDERS_PATH)
            orders = payload if isinstance(payload, list) else []
            for order in orders:
                if not isinstance(order, dict):
                    continue
                order_id = order.get("orderId")
                if order_id is None:
                    continue
                try:
                    await client.cancel_order(order_id=str(order_id))
                    canceled += 1
                except ApexError as error:
                    logger.failure("safe_mode_cancel_failed", error)
        return canceled

    return cancel_all


def _position_flattener(
    *,
    portfolio: SqlitePortfolioRepository,
    portfolio_id: str,
    bars: SqliteBarRepository,
    client: ToobitTradingClient,
    contract_infix: str,
    fee_rate: Decimal,
    ids: IdProvider,
    clock: Clock,
    logger: StructuredLogger,
) -> PositionFlattener:
    """The FLATTENED response: close every open position (25.29)."""

    async def flatten_all() -> int:
        return await flatten_positions(
            portfolio=portfolio,
            portfolio_id=portfolio_id,
            bars=bars,
            exchange_id="toobit",
            client=client,
            contract_infix=contract_infix,
            fee_rate=fee_rate,
            ids=ids,
            clock=clock,
            logger=logger,
        )

    return flatten_all


def _transition_auditor(security: SecurityService) -> TransitionAuditor:
    """Every kill-switch transition lands on the audit ledger (25.16)."""

    async def audit(actor: str, level: str, reason: str) -> None:
        await security.audit(
            actor=actor,
            action="kill.transition",
            target=level,
            result="ok",
            details={"reason": reason},
        )

    return audit


class MonitoringPlatformModule:
    """Kernel module owning the monitoring store and bus telemetry."""

    MODULE_NAME = "monitoring_platform"

    def __init__(
        self,
        *,
        repository: SqliteMonitoringRepository,
        collector: TelemetryCollector,
        bus: IEventBus,
        logger: StructuredLogger,
    ) -> None:
        self._repository = repository
        self._collector = collector
        self._bus = bus
        self._logger = logger
        self._running = False
        self._subscribed = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Observes every platform; starts after the research platform."""
        return ("research_platform", "execution_platform", "market_data")

    async def start(self) -> None:
        """Open the monitoring store and subscribe the collector."""
        await self._repository.open()
        if not self._subscribed:
            self._bus.subscribe_all(self._collector.observe_event)
            self._subscribed = True
        self._running = True
        self._logger.info("monitoring_platform_started")

    async def stop(self) -> None:
        """Flush pending telemetry and close the store."""
        self._running = False
        await self._collector.flush()
        await self._repository.close()
        self._logger.info("monitoring_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the store is open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


class MonitoringPlatformPlugin:
    """Builds the monitoring platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="monitoring_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Telemetry, health, alerts, kill switch, operational loop",
            stability=StabilityLevel.BETA,
            requires=(
                "research_platform",
                "execution_platform",
                "toobit_connector",
                "security_platform",
            ),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the monitoring platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        settings = monitoring_settings(config.section("telemetry"))
        repository = SqliteMonitoringRepository(
            database_path=Path(config.system.data_dir) / MONITORING_DATABASE_FILENAME,
        )
        collector = TelemetryCollector(
            store=repository, clock=clock, logger=loggers.get("monitoring.collector")
        )
        exchange_section = config.section("exchange")
        raw_execution = exchange_section.get("execution", {})
        exec_settings = execution_settings(
            raw_execution if isinstance(raw_execution, dict) else {}
        )
        canceller = _order_canceller(
            container.resolve(ToobitTradingClient),
            config.market.symbols,
            exec_settings.contract_infix,
            loggers.get("monitoring.killswitch"),
        )
        portfolio_config = portfolio_settings(config.section("portfolio"))
        portfolio_id = portfolio_config.portfolio_id
        flattener = _position_flattener(
            portfolio=container.resolve(SqlitePortfolioRepository),
            portfolio_id=portfolio_id,
            bars=container.resolve(SqliteBarRepository),
            client=container.resolve(ToobitTradingClient),
            contract_infix=exec_settings.contract_infix,
            fee_rate=Decimal(str(portfolio_config.account.fee_rate)),
            ids=container.resolve(IdProvider),
            clock=clock,
            logger=loggers.get("monitoring.killswitch"),
        )
        kill_switch = KillSwitchEngine(
            settings=settings,
            store=repository,
            bus=bus,
            clock=clock,
            logger=loggers.get("monitoring.killswitch"),
            order_canceller=canceller,
            position_flattener=flattener,
            auditor=_transition_auditor(container.resolve(SecurityService)),
        )
        alerts = AlertEngine(
            settings=settings,
            store=repository,
            kill_switch=kill_switch,
            bus=bus,
            clock=clock,
            logger=loggers.get("monitoring.alerts"),
        )
        health = HealthEngine(
            registry=container.resolve(ModuleRegistry),
            monitor=container.resolve(HealthMonitor),
        )
        slo = ErrorBudgetTracker(settings=settings, store=repository, clock=clock)
        service = MonitoringService(
            portfolio_id=portfolio_id,
            settings=settings,
            store=repository,
            collector=collector,
            health=health,
            alerts=alerts,
            kill_switch=kill_switch,
            slo=slo,
            portfolio_repository=container.resolve(SqlitePortfolioRepository),
            research_repository=container.resolve(SqliteResearchRepository),
            bus=bus,
            clock=clock,
            logger=loggers.get("monitoring.service"),
        )
        loop = OperationsLoopService(
            config=config,
            catchup=container.resolve(CatchUpService),
            stream=container.resolve(MarketStreamService),
            features=container.resolve(FeatureComputationPipeline),
            probability=container.resolve(ProbabilityService),
            decision=container.resolve(DecisionService),
            decision_repository=container.resolve(SqliteDecisionRepository),
            execution=container.resolve(ExecutionService),
            execution_repository=container.resolve(SqliteExecutionRepository),
            research=container.resolve(ResearchService),
            monitoring=service,
            portfolio_id=portfolio_id,
            bus=bus,
            clock=clock,
            id_provider=container.resolve(IdProvider),
            logger=loggers.get("monitoring.loop"),
        )
        container.register_instance(SqliteMonitoringRepository, repository)
        container.register_instance(MonitoringService, service)
        container.register_instance(OperationsLoopService, loop)
        return [
            MonitoringPlatformModule(
                repository=repository,
                collector=collector,
                bus=bus,
                logger=loggers.get("monitoring.module"),
            )
        ]


APEX_PLUGIN = MonitoringPlatformPlugin()

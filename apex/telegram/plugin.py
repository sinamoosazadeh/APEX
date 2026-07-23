"""Telegram console plugin (Book IV).

Wires the control layer: console settings (telegram.yaml) ->
vault-first credentials with an environment fallback (13.7; absent
credentials leave the console dormant - trading never depends on
Telegram) -> Bot API client -> console service -> kernel module.
Boot is network-free: the client session opens only when the console
runs.
"""

from collections.abc import Sequence

from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer
from apex.monitoring.service import MonitoringService
from apex.plugins.contract import PluginManifest
from apex.portfolio.config import portfolio_settings
from apex.portfolio.store import SqlitePortfolioRepository
from apex.research.service import ResearchService
from apex.security.service import SecurityService
from apex.security.vault import (
    SECRET_TELEGRAM_ADMINS,
    SECRET_TELEGRAM_TOKEN,
    SECRET_TELEGRAM_VIEWERS,
)
from apex.telegram.client import TelegramBotClient
from apex.telegram.config import telegram_settings
from apex.telegram.credentials import TelegramCredentials
from apex.telegram.service import TelegramConsoleService


def _credentials(security: SecurityService) -> TelegramCredentials | None:
    """Vault-first console credentials with environment fallback (13.7)."""
    token = security.secret(SECRET_TELEGRAM_TOKEN)
    if token:
        return TelegramCredentials.from_sources(
            token=token,
            admins_raw=security.secret(SECRET_TELEGRAM_ADMINS) or "",
            viewers_raw=security.secret(SECRET_TELEGRAM_VIEWERS) or "",
        )
    return TelegramCredentials.from_environment()


class TelegramConsoleModule:
    """Kernel module representing the console's presence."""

    MODULE_NAME = "telegram_console"

    def __init__(
        self,
        *,
        service: TelegramConsoleService,
        logger: StructuredLogger,
    ) -> None:
        self._service = service
        self._logger = logger
        self._running = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Renders the monitoring feed; starts after it."""
        return ("monitoring_platform",)

    async def start(self) -> None:
        """Mark the console present (network contact only on demand)."""
        self._running = True
        self._logger.info(
            "telegram_console_ready", available=self._service.available
        )

    async def stop(self) -> None:
        """Stop the console if a session is running."""
        self._running = False
        self._service.request_stop()
        self._logger.info("telegram_console_stopped")

    def health(self) -> HealthState:
        """Healthy while registered; the console itself runs on demand."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


class TelegramConsolePlugin:
    """Builds the Telegram console as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="telegram_console",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Telegram control layer: menus, reports, emergency center",
            stability=StabilityLevel.BETA,
            requires=("monitoring_platform", "security_platform"),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the console from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        settings = telegram_settings(config.section("telegram"))
        credentials = _credentials(container.resolve(SecurityService))
        client: TelegramBotClient | None = None
        if credentials is not None:
            client = TelegramBotClient(
                token=credentials.token,
                poll_timeout_s=settings.poll_timeout_s,
                logger=loggers.get("telegram.client"),
            )
        series = tuple(
            (symbol, timeframe)
            for symbol in config.market.symbols
            for timeframe in config.market.timeframes
        )
        service = TelegramConsoleService(
            settings=settings,
            credentials=credentials,
            client=client,
            monitoring=container.resolve(MonitoringService),
            research=container.resolve(ResearchService),
            portfolio_repository=container.resolve(SqlitePortfolioRepository),
            portfolio_id=portfolio_settings(
                config.section("portfolio")
            ).portfolio_id,
            series=series,
            bus=bus,
            clock=clock,
            logger=loggers.get("telegram.service"),
        )
        container.register_instance(TelegramConsoleService, service)
        return [
            TelegramConsoleModule(
                service=service,
                logger=loggers.get("telegram.module"),
            )
        ]


APEX_PLUGIN = TelegramConsolePlugin()

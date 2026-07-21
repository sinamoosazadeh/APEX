"""Toobit exchange connector plugin (Book II 3.23: connectors are plugins).

Wires the whole Phase 3 data platform slice from injected services:
REST client -> translator -> gateway -> quality inspector -> pipeline
-> kernel module. Registered via ``plugins.enabled`` in system.yaml.
"""

from collections.abc import Sequence
from pathlib import Path

from apex.contracts.engines import IMarketDataGateway
from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import PluginKind, StabilityLevel
from apex.core.logging import LoggerFactory
from apex.core.versioning import SemanticVersion
from apex.data.catchup import CatchUpService
from apex.data.module import MarketDataModule
from apex.data.pipeline import BarIngestionPipeline
from apex.data.quality import BarQualityInspector
from apex.data.streaming import MarketStreamService
from apex.data.toobit.client import ToobitRestClient
from apex.data.toobit.gateway import ToobitMarketDataGateway
from apex.data.toobit.stream import ToobitStreamClient
from apex.data.toobit.translator import ToobitTranslator
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest
from apex.storage.bars import SqliteBarRepository
from apex.storage.ticks import SqliteTickRepository

BARS_DATABASE_FILENAME = "bars.sqlite"
TICKS_DATABASE_FILENAME = "ticks.sqlite"


class ToobitConnectorPlugin:
    """Builds the Toobit market data stack as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="toobit_connector",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.EXCHANGE_CONNECTOR,
            api_version=SemanticVersion(1, 0, 0),
            description="Toobit market data gateway, ingestion pipeline and bar store",
            stability=StabilityLevel.BETA,
            requires=("storage_core",),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct and register the data platform services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]

        toobit = config.toobit
        client = ToobitRestClient(
            base_url=toobit.base_url,
            request_timeout_ms=toobit.request_timeout_ms,
            max_retries=toobit.max_retries,
            retry_backoff_ms=toobit.retry_backoff_ms,
            logger=loggers.get("data.toobit.client"),
        )
        translator = ToobitTranslator()
        gateway = ToobitMarketDataGateway(
            client=client,
            translator=translator,
            clock=clock,
            logger=loggers.get("data.toobit.gateway"),
            kline_page_limit=toobit.kline_page_limit,
        )
        repository = SqliteBarRepository(
            database_path=Path(config.system.data_dir) / BARS_DATABASE_FILENAME,
        )
        tick_repository = SqliteTickRepository(
            database_path=Path(config.system.data_dir) / TICKS_DATABASE_FILENAME,
        )
        pipeline = BarIngestionPipeline(
            gateway=gateway,
            repository=repository,
            inspector=BarQualityInspector(
                gap_penalty=config.market.gap_penalty,
                forming_bar_quality=config.market.forming_bar_quality,
            ),
            bus=bus,
            clock=clock,
            logger=loggers.get("data.pipeline"),
        )
        catchup = CatchUpService(
            pipeline=pipeline,
            repository=repository,
            config=config.market,
            exchange_id=gateway.exchange_id,
            clock=clock,
            logger=loggers.get("data.catchup"),
        )
        stream_client = ToobitStreamClient(
            url=toobit.ws_url,
            clock=clock,
            logger=loggers.get("data.toobit.stream"),
            ping_interval_ms=toobit.ws_ping_interval_ms,
            recv_timeout_ms=toobit.ws_recv_timeout_ms,
        )
        streaming = MarketStreamService(
            client=stream_client,
            translator=translator,
            bar_repository=repository,
            tick_repository=tick_repository,
            bus=bus,
            clock=clock,
            logger=loggers.get("data.streaming"),
            symbols=config.market.symbols,
            timeframes=config.market.timeframes,
            forming_flush_ms=config.market.stream_forming_flush_ms,
            reconnect_backoff_ms=config.market.stream_reconnect_backoff_ms,
            max_reconnects=config.market.stream_max_reconnects,
        )
        container.register_instance(SqliteBarRepository, repository)
        container.register_instance(SqliteTickRepository, tick_repository)
        container.register_instance(BarIngestionPipeline, pipeline)
        container.register_instance(CatchUpService, catchup)
        container.register_instance(MarketStreamService, streaming)
        self._register_gateway(container, gateway)
        return [
            MarketDataModule(
                gateway=gateway,
                repository=repository,
                tick_repository=tick_repository,
                logger=loggers.get("data.module"),
            )
        ]

    @staticmethod
    def _register_gateway(container: ServiceContainer, gateway: ToobitMarketDataGateway) -> None:
        container.register_instance(IMarketDataGateway, gateway)  # type: ignore[type-abstract]


APEX_PLUGIN = ToobitConnectorPlugin()

"""Core storage plugin.

Provides the platform key/value store (IStorage) and the durable
event archive module. Loaded first: other plugins may depend on
``storage_core`` for persistence.
"""

from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IEventBus, IModule, IStorage
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.events.journal import EventJournal
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest
from apex.storage.archive import EventArchiveModule
from apex.storage.sqlite import SqliteKeyValueStorage

KV_DATABASE_FILENAME = "apex.sqlite"


class StorageLifecycleModule:
    """Kernel module owning the key/value store lifecycle."""

    MODULE_NAME = "storage_core"

    def __init__(self, *, storage: SqliteKeyValueStorage, logger: StructuredLogger) -> None:
        self._storage = storage
        self._logger = logger
        self._running = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """No dependencies; storage starts first."""
        return ()

    async def start(self) -> None:
        """Open the database."""
        await self._storage.open()
        self._running = True
        self._logger.info("storage_started")

    async def stop(self) -> None:
        """Close the database."""
        self._running = False
        await self._storage.close()
        self._logger.info("storage_stopped")

    def health(self) -> HealthState:
        """Healthy while open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


class StoragePlugin:
    """Builds the key/value store and the event archive."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="storage_core",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="SQLite key/value storage and durable event archive",
            stability=StabilityLevel.BETA,
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct storage services from injected configuration."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        storage = SqliteKeyValueStorage(
            database_path=Path(config.system.data_dir) / KV_DATABASE_FILENAME,
        )
        container.register_instance(SqliteKeyValueStorage, storage)
        container.register_instance(IStorage, storage)  # type: ignore[type-abstract]
        lifecycle = StorageLifecycleModule(
            storage=storage,
            logger=loggers.get("storage.lifecycle"),
        )
        archive = EventArchiveModule(
            storage=storage,
            bus=bus,
            journal=container.resolve(EventJournal),
            logger=loggers.get("storage.archive"),
        )
        return [lifecycle, archive]


APEX_PLUGIN = StoragePlugin()

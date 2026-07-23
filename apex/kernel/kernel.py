"""The APEX kernel: boot and shutdown orchestration.

Implements the foundation slice of the startup sequence (Book II
29.21): Configuration -> Logger -> Dependency Injection -> Event Bus ->
Modules -> Health -> Ready, and the reverse shutdown sequence (29.22).
Engine platforms of later phases join as kernel modules without
changing this orchestrator.
"""

import uuid
from dataclasses import dataclass
from pathlib import Path

from apex.core.config import AppConfig, load_config
from apex.core.context import SessionContext
from apex.core.contracts.interfaces import IClock, IEventBus, ILogger
from apex.core.enums import HealthState, ModuleState
from apex.core.events.bus import InProcessEventBus
from apex.core.events.catalog import SystemEvent, system_event
from apex.core.events.journal import EventJournal
from apex.core.exceptions import ApexError, KernelError
from apex.core.identity import IdProvider
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.time.clock import Clock, SystemClock
from apex.kernel.container import ServiceContainer
from apex.kernel.health import HealthMonitor
from apex.kernel.modules import ModuleRegistry
from apex.plugins.loader import PluginLoader, safe_load

_SOURCE = "apex.kernel"


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelStatus:
    """Snapshot of the kernel after boot (for CLI and telemetry)."""

    session_id: uuid.UUID
    app_name: str
    environment: str
    run_mode: str
    config_hash: str
    plugins_loaded: tuple[str, ...]
    modules_started: tuple[str, ...]
    services_registered: tuple[str, ...]
    health: HealthState
    events_journaled: int


class Kernel:
    """Owns the platform lifecycle from boot to shutdown."""

    def __init__(
        self,
        *,
        config_dir: Path,
        clock: Clock | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._config_dir = config_dir
        self._clock: Clock = clock if clock is not None else SystemClock()
        self._env = env
        self._container = ServiceContainer()
        self._registry = ModuleRegistry()
        self._started_modules: list[str] = []
        self._running = False
        self._config: AppConfig | None = None
        self._logger: StructuredLogger | None = None
        self._bus: InProcessEventBus | None = None
        self._health: HealthMonitor | None = None
        self._session_id: uuid.UUID | None = None
        self._plugins: tuple[str, ...] = ()

    # --- Accessors -------------------------------------------------------------

    @property
    def container(self) -> ServiceContainer:
        """The kernel's service container."""
        return self._container

    @property
    def modules(self) -> ModuleRegistry:
        """The kernel's module registry (register before ``boot``)."""
        return self._registry

    @property
    def is_running(self) -> bool:
        """Whether boot completed and shutdown has not begun."""
        return self._running

    # --- Boot (Book II 29.21) ----------------------------------------------------

    async def boot(self) -> KernelStatus:
        """Run the startup sequence; returns the ready status."""
        if self._running:
            raise KernelError("kernel is already running", code="KRN-030")
        config = self._stage_configuration()
        logger = self._stage_logger(config)
        session_id = self._stage_dependency_injection(config, logger)
        bus = self._stage_event_bus(config, logger)
        await bus.publish(
            system_event(
                SystemEvent.KERNEL_BOOTING,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={"app_name": config.system.app_name},
            )
        )
        await bus.publish(
            system_event(
                SystemEvent.CONFIG_LOADED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={"config_hash": config.config_hash, "config_dir": config.config_dir},
            )
        )
        self._stage_plugins(config, logger)
        await self._stage_modules(bus, logger)
        health = self._stage_health(logger)
        self._running = True
        await bus.publish(
            system_event(
                SystemEvent.KERNEL_STARTED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={"session_id": str(session_id), "health": health.value},
            )
        )
        logger.info("kernel_ready", session_id=str(session_id), health=health.value)
        return self.status()

    def _stage_configuration(self) -> AppConfig:
        config = load_config(self._config_dir, env=self._env)
        self._config = config
        return config

    def _stage_logger(self, config: AppConfig) -> StructuredLogger:
        factory = LoggerFactory(
            clock=self._clock,
            level=config.logging.level,
            log_format=config.logging.output_format,
        )
        logger = factory.get("kernel")
        self._logger = logger
        self._container.register_instance(LoggerFactory, factory)
        logger.info(
            "logger_initialized",
            level=config.logging.level.value,
            format=config.logging.output_format.value,
        )
        return logger

    def _stage_dependency_injection(
        self,
        config: AppConfig,
        logger: StructuredLogger,
    ) -> uuid.UUID:
        id_provider = (
            IdProvider(seed=config.system.id_seed)
            if config.system.deterministic_ids
            else IdProvider()
        )
        session_id = id_provider.new_id()
        self._session_id = session_id
        self._container.register_instance(AppConfig, config)
        self._container.register_instance(IdProvider, id_provider)
        self._container.register_instance(HealthMonitor, HealthMonitor(clock=self._clock))
        self._container.register_instance(ModuleRegistry, self._registry)
        self._register_protocol(IClock, self._clock)
        self._register_protocol(ILogger, logger)
        self._container.register_instance(
            SessionContext,
            SessionContext(
                session_id=session_id,
                environment=config.system.environment,
                run_mode=config.system.run_mode,
                started_at=self._clock.now(),
                config_hash=config.config_hash,
            ),
        )
        logger.info("dependency_injection_ready", session_id=str(session_id))
        return session_id

    def _register_protocol(self, protocol: type, instance: object) -> None:
        # Protocols are registered under their protocol type as the key.
        self._container.register_instance(protocol, instance)

    def _stage_plugins(self, config: AppConfig, logger: StructuredLogger) -> None:
        """Load configured plugins (Book II 29.24); failures abort boot."""
        factory = self._container.resolve(LoggerFactory)
        loader = PluginLoader(
            container=self._container,
            registry=self._registry,
            logger=factory.get("kernel.plugins"),
        )
        loaded = safe_load(loader, config.system.plugin_modules)
        self._plugins = tuple(record.manifest.name for record in loaded)
        logger.info("plugins_loaded", count=len(loaded), plugins=", ".join(self._plugins))

    def _stage_event_bus(self, config: AppConfig, logger: StructuredLogger) -> InProcessEventBus:
        journal = EventJournal(capacity=config.system.event_journal_capacity)
        factory = self._container.resolve(LoggerFactory)
        bus = InProcessEventBus(
            journal=journal,
            clock=self._clock,
            logger=factory.get("core.events.bus"),
            fail_fast=config.system.event_fail_fast,
        )
        self._bus = bus
        self._container.register_instance(EventJournal, journal)
        self._register_protocol(IEventBus, bus)
        logger.info("event_bus_ready", journal_capacity=journal.capacity)
        return bus

    async def _stage_modules(self, bus: InProcessEventBus, logger: StructuredLogger) -> None:
        for name in self._registry.start_order():
            module = self._registry.get(name)
            self._registry.set_state(name, ModuleState.STARTING)
            try:
                await module.start()
            except ApexError as error:
                self._registry.set_state(name, ModuleState.FAILED)
                logger.failure("module_start_failed", error, module=name)
                await bus.publish(
                    system_event(
                        SystemEvent.MODULE_FAILED,
                        occurred_at=self._clock.now(),
                        source=_SOURCE,
                        payload={"module": name, "error_code": error.code},
                    )
                )
                raise KernelError(
                    "module failed to start; boot aborted",
                    code="KRN-031",
                    details={"module": name, "error_code": error.code},
                ) from error
            self._registry.set_state(name, ModuleState.RUNNING)
            self._started_modules.append(name)
            logger.info("module_started", module=name)
            await bus.publish(
                system_event(
                    SystemEvent.MODULE_STARTED,
                    occurred_at=self._clock.now(),
                    source=_SOURCE,
                    payload={"module": name},
                )
            )

    def _stage_health(self, logger: StructuredLogger) -> HealthState:
        monitor = self._container.resolve(HealthMonitor)
        monitor.report("kernel", HealthState.HEALTHY, modules=len(self._started_modules))
        for name in self._started_modules:
            monitor.report(f"module.{name}", self._registry.get(name).health())
        self._health = monitor
        overall = monitor.overall()
        logger.info("health_check_complete", overall=overall.value)
        return overall

    # --- Shutdown (Book II 29.22) --------------------------------------------------

    async def shutdown(self) -> None:
        """Run the reverse shutdown sequence. Idempotent."""
        if not self._running:
            return
        logger = self._require_logger()
        bus = self._require_bus()
        self._running = False
        await bus.publish(
            system_event(
                SystemEvent.KERNEL_STOPPING,
                occurred_at=self._clock.now(),
                source=_SOURCE,
            )
        )
        for name in reversed(self._started_modules):
            module = self._registry.get(name)
            self._registry.set_state(name, ModuleState.STOPPING)
            try:
                await module.stop()
                self._registry.set_state(name, ModuleState.STOPPED)
                logger.info("module_stopped", module=name)
                await bus.publish(
                    system_event(
                        SystemEvent.MODULE_STOPPED,
                        occurred_at=self._clock.now(),
                        source=_SOURCE,
                        payload={"module": name},
                    )
                )
            except ApexError as error:
                self._registry.set_state(name, ModuleState.FAILED)
                logger.failure("module_stop_failed", error, module=name)
        self._started_modules.clear()
        await bus.publish(
            system_event(
                SystemEvent.KERNEL_STOPPED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
            )
        )
        bus.close()
        logger.info("kernel_stopped")

    # --- Introspection -----------------------------------------------------------

    def status(self) -> KernelStatus:
        """Current kernel status; requires a completed boot."""
        config = self._config
        health = self._health
        bus = self._require_bus()
        if config is None or health is None or self._session_id is None:
            raise KernelError("kernel has not booted", code="KRN-032")
        return KernelStatus(
            session_id=self._session_id,
            app_name=config.system.app_name,
            environment=config.system.environment.value,
            run_mode=config.system.run_mode.value,
            config_hash=config.config_hash,
            plugins_loaded=self._plugins,
            modules_started=tuple(self._started_modules),
            services_registered=self._container.registered_types(),
            health=health.overall(),
            events_journaled=bus.journal.total_appended,
        )

    def _require_logger(self) -> StructuredLogger:
        if self._logger is None:
            raise KernelError("kernel logger not initialized", code="KRN-033")
        return self._logger

    def _require_bus(self) -> InProcessEventBus:
        if self._bus is None:
            raise KernelError("kernel event bus not initialized", code="KRN-034")
        return self._bus

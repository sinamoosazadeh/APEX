"""Security platform plugin (Book II ch. 25; Book I ch. 13).

Wires the Phase 13 slice: the encrypted secret vault (built only when
the ``APEX_MASTER_KEY`` environment variable is present - the model's
single root secret), the immutable audit ledger, the access policy
and the security service. Loads directly after the storage core so
every later platform can resolve vault-first credentials.
"""

import os
from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.exceptions import ConfigurationError
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest
from apex.security.access import AccessPolicy
from apex.security.audit import SqliteAuditLedger
from apex.security.config import SecuritySettings, security_settings
from apex.security.service import SecurityService
from apex.security.vault import MASTER_KEY_ENV, SecretVault


class SecurityPlatformModule:
    """Kernel module owning the audit ledger lifecycle."""

    MODULE_NAME = "security_platform"

    def __init__(
        self,
        *,
        ledger: SqliteAuditLedger,
        logger: StructuredLogger,
    ) -> None:
        self._ledger = ledger
        self._logger = logger
        self._running = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """The ledger lives beside the storage core's databases."""
        return ("storage_core",)

    async def start(self) -> None:
        """Open the audit ledger."""
        await self._ledger.open()
        self._running = True
        self._logger.info("security_platform_started")

    async def stop(self) -> None:
        """Close the audit ledger."""
        self._running = False
        await self._ledger.close()
        self._logger.info("security_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the ledger is open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


class SecurityPlatformPlugin:
    """Builds the security platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="security_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Secret vault, audit ledger, access policy, preflight",
            stability=StabilityLevel.BETA,
            requires=("storage_core",),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the security platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        section = config.section("security")
        settings = security_settings(section)
        policy_raw = section.get("policy", {})
        if not isinstance(policy_raw, dict):
            raise ConfigurationError(
                "security.policy must be a mapping", code="CFG-043", details={}
            )
        policy = AccessPolicy.from_config(policy_raw)
        data_dir = Path(config.system.data_dir)
        master_key = os.environ.get(MASTER_KEY_ENV, "")
        vault = (
            SecretVault(
                path=data_dir / settings.vault_filename, master_key=master_key
            )
            if master_key
            else None
        )
        ledger = SqliteAuditLedger(
            database_path=data_dir / settings.audit_filename
        )
        service = SecurityService(
            settings=settings,
            vault=vault,
            ledger=ledger,
            policy=policy,
            bus=bus,
            clock=clock,
            logger=loggers.get("security.service"),
        )
        container.register_instance(SecuritySettings, settings)
        container.register_instance(SqliteAuditLedger, ledger)
        container.register_instance(SecurityService, service)
        return [
            SecurityPlatformModule(
                ledger=ledger,
                logger=loggers.get("security.module"),
            )
        ]


APEX_PLUGIN = SecurityPlatformPlugin()

"""Market data kernel module.

Owns the lifecycle of the data platform's resources: the bar
repository and the live gateway's HTTP session. Boot stays offline by
design - ingestion runs on demand (CLI, scheduler in Phase 11), so
``python -m apex --check`` never touches the network.
"""

from apex.core.enums import HealthState
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.data.toobit.gateway import ToobitMarketDataGateway
from apex.storage.bars import SqliteBarRepository


class MarketDataModule:
    """Kernel module for the data platform (Phase 3)."""

    MODULE_NAME = "market_data"

    def __init__(
        self,
        *,
        gateway: ToobitMarketDataGateway,
        repository: SqliteBarRepository,
        logger: StructuredLogger,
    ) -> None:
        self._gateway = gateway
        self._repository = repository
        self._logger = logger
        self._running = False
        self._degraded = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Starts after the event archive so ingestion events persist."""
        return ("event_archive",)

    async def start(self) -> None:
        """Open repository and gateway resources."""
        await self._repository.open()
        await self._gateway.open()
        self._running = True
        self._logger.info("market_data_started", exchange=self._gateway.exchange_id)

    async def stop(self) -> None:
        """Release gateway and repository resources; idempotent."""
        self._running = False
        try:
            await self._gateway.close()
        except ApexError as error:
            self._degraded = True
            self._logger.failure("gateway_close_failed", error)
        await self._repository.close()
        self._logger.info("market_data_stopped")

    def health(self) -> HealthState:
        """Healthy while resources are open."""
        if not self._running:
            return HealthState.OFFLINE
        return HealthState.WARNING if self._degraded else HealthState.HEALTHY

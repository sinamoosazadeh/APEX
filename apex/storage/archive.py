"""Event archive.

Durable event persistence (Book II 5.32): a kernel module that
subscribes to the whole bus and writes every event to storage as
canonical JSON, keyed by sequence number. Replays survive process
restarts; the in-memory journal remains the fast path.
"""

from apex.core.contracts.interfaces import IEventBus, IStorage
from apex.core.enums import HealthState
from apex.core.events.event import Event
from apex.core.events.journal import EventJournal
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.core.serialization import canonical_json

ARCHIVE_NAMESPACE = "events"


class EventArchiveModule:
    """Kernel module persisting every published event.

    On start it first replays the in-memory journal (catching up on
    boot-time events published before modules started), then subscribes
    for everything that follows. Writes are keyed by sequence, so the
    catch-up is idempotent.
    """

    MODULE_NAME = "event_archive"

    def __init__(
        self,
        *,
        storage: IStorage,
        bus: IEventBus,
        journal: EventJournal,
        logger: StructuredLogger,
    ) -> None:
        self._storage = storage
        self._bus = bus
        self._journal = journal
        self._logger = logger
        self._archived = 0
        self._failed = 0
        self._running = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Storage must be open before events can be persisted."""
        return ("storage_core",)

    @property
    def archived_count(self) -> int:
        """Events successfully archived this run."""
        return self._archived

    async def start(self) -> None:
        """Catch up on journaled events, then subscribe to the bus."""
        self._running = True
        for event in self._journal.replay():
            await self._archive(event)
        self._bus.subscribe_all(self._archive)
        self._logger.info("event_archive_started", caught_up=self._archived)

    async def stop(self) -> None:
        """Stop archiving (bus itself closes during kernel shutdown)."""
        self._running = False
        self._logger.info("event_archive_stopped", archived=self._archived)

    def health(self) -> HealthState:
        """Healthy while running and not accumulating failures."""
        if not self._running:
            return HealthState.OFFLINE
        return HealthState.HEALTHY if self._failed == 0 else HealthState.WARNING

    async def _archive(self, event: Event) -> None:
        if not self._running:
            # Post-stop shutdown events are deliberately not archived:
            # storage is already closed. The archive covers start->stop.
            return
        if event.sequence is None:
            # Cannot happen for bus-delivered events; guard the contract.
            self._failed += 1
            self._logger.error("event_missing_sequence", event_type=event.event_type)
            return
        try:
            await self._storage.write(
                ARCHIVE_NAMESPACE,
                f"{event.sequence:020d}",
                canonical_json(event.to_dict()).encode("utf-8"),
            )
            self._archived += 1
        except ApexError as error:
            self._failed += 1
            self._logger.failure("event_archive_failed", error, sequence=event.sequence)

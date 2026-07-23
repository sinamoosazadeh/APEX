"""Kill-switch engine (the Phase 12 monitoring-driven surfaces).

The multi-trigger kill switch of Book I 8.27 / Book II 10.25, scoped
to what monitoring owns in this phase: a durable, auditable state
ladder (NONE -> ENTRIES_DISABLED -> PAUSED -> SAFE_MODE) that the
orchestration surfaces consult before decisions and executions.
Transitions come from operators (Telegram/CLI) or automatically from
the alert engine's severity policy. SAFE_MODE additionally cancels
resting venue orders best-effort through an injected canceller (10.25
"Cancel Pending Orders"). Position flattening and the five-scope
kill-switch matrix belong to the Phase 13 security platform (25.29).
"""

from collections.abc import Awaitable, Callable
from typing import Final

from apex.core.contracts.interfaces import IEventBus
from apex.core.exceptions import ApexError, MonitoringError
from apex.core.logging import StructuredLogger
from apex.core.time.clock import Clock
from apex.monitoring.config import MonitoringSettings
from apex.monitoring.events import MonitoringEvent, monitoring_event
from apex.monitoring.records import AlertSeverity, KillSwitchLevel, KillSwitchRecord
from apex.monitoring.store import SqliteMonitoringRepository

_SOURCE: Final[str] = "apex.monitoring.killswitch"

type OrderCanceller = Callable[[], Awaitable[int]]


class KillSwitchEngine:
    """Durable trading-permission ladder with auto-engage policy."""

    def __init__(
        self,
        *,
        settings: MonitoringSettings,
        store: SqliteMonitoringRepository,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
        order_canceller: OrderCanceller | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._bus = bus
        self._clock = clock
        self._logger = logger
        self._order_canceller = order_canceller

    # --- State ---------------------------------------------------------------------

    async def current(self) -> KillSwitchRecord | None:
        """The latest transition entry; None before any transition."""
        return await self._store.current_kill_switch()

    async def level(self) -> KillSwitchLevel:
        """The effective level (NONE before any transition)."""
        record = await self.current()
        return record.level if record is not None else KillSwitchLevel.NONE

    async def allows_new_entries(self) -> bool:
        """Whether new positions may be entered."""
        return (await self.level()) is KillSwitchLevel.NONE

    async def allows_processing(self) -> bool:
        """Whether decision/execution stages may run at all."""
        return (await self.level()).rank < KillSwitchLevel.PAUSED.rank

    # --- Transitions ---------------------------------------------------------------

    async def engage(
        self, level: KillSwitchLevel, *, reason: str, actor: str
    ) -> KillSwitchRecord:
        """Move to a restrictive level; SAFE_MODE cancels resting orders."""
        if level is KillSwitchLevel.NONE:
            raise MonitoringError(
                "engage requires a restrictive level; use release",
                code="MON-001",
                details={"level": level.value},
            )
        record = await self._transition(level, reason=reason, actor=actor)
        if level is KillSwitchLevel.SAFE_MODE:
            await self.cancel_resting_orders()
        return record

    async def release(self, *, reason: str, actor: str) -> KillSwitchRecord:
        """Return to normal trading (an audited transition like any)."""
        return await self._transition(KillSwitchLevel.NONE, reason=reason, actor=actor)

    async def auto_engage(self, *, severity: AlertSeverity, reason: str) -> bool:
        """Alert-driven engagement per the configured policy."""
        if not self._settings.kill_switch_auto_engage:
            return False
        if severity.rank < self._settings.kill_switch_engage_severity.rank:
            return False
        target = self._settings.kill_switch_engage_level
        if (await self.level()).rank >= target.rank:
            return False
        await self.engage(target, reason=f"auto: {reason}", actor="monitoring")
        return True

    async def _transition(
        self, level: KillSwitchLevel, *, reason: str, actor: str
    ) -> KillSwitchRecord:
        now = self._clock.now()
        entry_id = await self._store.insert_kill_switch(
            level=level, reason=reason, actor=actor, at=now
        )
        await self._bus.publish(
            monitoring_event(
                MonitoringEvent.KILL_SWITCH_CHANGED,
                occurred_at=now,
                source=_SOURCE,
                payload={"level": level.value, "reason": reason, "actor": actor},
            )
        )
        self._logger.warning(
            "kill_switch_changed", level=level.value, reason=reason, actor=actor
        )
        return KillSwitchRecord(
            entry_id=entry_id, level=level, reason=reason, actor=actor, changed_at=now
        )

    async def cancel_resting_orders(self) -> int:
        """Best-effort venue order cancellation (10.25 step two).

        Public: SAFE_MODE calls it on engagement and the Telegram
        Emergency Center exposes it as Cancel All Orders. Returns how
        many orders were canceled (0 without a canceller or on error).
        """
        if self._order_canceller is None:
            self._logger.info("kill_switch_no_canceller")
            return 0
        try:
            canceled = await self._order_canceller()
        except ApexError as error:
            self._logger.failure("kill_switch_cancel_failed", error)
            return 0
        self._logger.info("kill_switch_orders_canceled", canceled=canceled)
        return canceled

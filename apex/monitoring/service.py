"""Monitoring service (Book II ch. 26; Book I ch. 10).

The observability facade every surface talks to: the unified
operations status (26.29 - one aggregate of health, kill switch,
alerts, error budget, portfolio headline, research queue and
heartbeats), periodic state snapshots (10.17: the whole system's
state, durable and replayable), the alert tick, and config-driven
retention pruning. Ingestion stays with the collector; storage with
the monitoring store; this service composes them.
"""

import json
from typing import Final

from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import HealthState, PositionStatus
from apex.core.logging import StructuredLogger
from apex.core.time.clock import Clock
from apex.monitoring.alerts import AlertEngine, PortfolioPulse
from apex.monitoring.collector import TelemetryCollector
from apex.monitoring.config import MonitoringSettings
from apex.monitoring.events import MonitoringEvent, monitoring_event
from apex.monitoring.health import HealthEngine
from apex.monitoring.killswitch import KillSwitchEngine
from apex.monitoring.records import (
    AlertRecord,
    AlertSeverity,
    KillSwitchLevel,
    OperationsStatus,
    StateSnapshotRecord,
)
from apex.monitoring.slo import ErrorBudgetTracker
from apex.monitoring.store import SqliteMonitoringRepository
from apex.portfolio.store import SqlitePortfolioRepository
from apex.research.store import (
    JOB_PENDING,
    JOB_RUNNING,
    PROMOTION_PASSED,
    PROMOTION_SHADOW,
    SqliteResearchRepository,
)

_SOURCE: Final[str] = "apex.monitoring.service"
_DAY_MS: Final[int] = 86_400_000


class MonitoringService:
    """Composes the observability engines into one operations feed."""

    def __init__(
        self,
        *,
        portfolio_id: str,
        settings: MonitoringSettings,
        store: SqliteMonitoringRepository,
        collector: TelemetryCollector,
        health: HealthEngine,
        alerts: AlertEngine,
        kill_switch: KillSwitchEngine,
        slo: ErrorBudgetTracker,
        portfolio_repository: SqlitePortfolioRepository,
        research_repository: SqliteResearchRepository,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._portfolio_id = portfolio_id
        self._settings = settings
        self._store = store
        self._collector = collector
        self._health = health
        self._alerts = alerts
        self._kill_switch = kill_switch
        self._slo = slo
        self._portfolio = portfolio_repository
        self._research = research_repository
        self._bus = bus
        self._clock = clock
        self._logger = logger

    # --- Accessors ---------------------------------------------------------------

    @property
    def settings(self) -> MonitoringSettings:
        """The validated monitoring configuration."""
        return self._settings

    @property
    def collector(self) -> TelemetryCollector:
        """The telemetry ingestion path."""
        return self._collector

    @property
    def kill_switch(self) -> KillSwitchEngine:
        """The kill-switch surfaces."""
        return self._kill_switch

    @property
    def slo(self) -> ErrorBudgetTracker:
        """The error-budget tracker (26.28)."""
        return self._slo

    async def recent_alerts(self, *, limit: int = 10) -> list[AlertRecord]:
        """Most recent alerts, newest first."""
        return await self._store.alerts(limit=limit)

    async def raise_alert(
        self,
        *,
        severity: AlertSeverity,
        category: str,
        message: str,
        dedup_key: str,
    ) -> bool:
        """Raise one alert through the deduplicating engine."""
        return await self._alerts.raise_alert(
            severity=severity, category=category, message=message, dedup_key=dedup_key
        )

    # --- Operations center (26.29) --------------------------------------------------

    async def ops_status(self) -> OperationsStatus:
        """The unified operations feed every dashboard renders."""
        now = self._clock.now()
        components = self._health.assess()
        overall = self._health.overall(components)
        beats = self._health.heartbeat_ages(
            await self._store.heartbeats(),
            now=now,
            stale_ms=self._settings.heartbeat_stale_ms,
        )
        switch = await self._kill_switch.current()
        pulse = await self.portfolio_pulse()
        statistics = await self._portfolio.statistics(self._portfolio_id)
        open_positions = await self._portfolio.get_positions(
            self._portfolio_id, status=PositionStatus.OPEN.value
        )
        snapshots = await self._portfolio.get_snapshots(self._portfolio_id)
        equity = str(snapshots[-1].equity) if snapshots else "0"
        cash = str(snapshots[-1].cash) if snapshots else "0"
        return OperationsStatus(
            as_of=now,
            overall_health=overall if components else HealthState.OFFLINE,
            components=components,
            heartbeats=beats,
            kill_switch=switch.level if switch else KillSwitchLevel.NONE,
            kill_switch_reason=switch.reason if switch else "",
            alerts_recent=tuple(await self._store.alerts(limit=5)),
            incidents_open=len(await self._store.open_incidents()),
            error_budget=await self._slo.status(),
            equity=equity,
            cash=cash,
            drawdown=pulse.drawdown,
            open_positions=len(open_positions),
            closed_trades=statistics.trades,
            win_rate=statistics.win_rate,
            r_sum=statistics.r_sum,
            jobs_pending=len(await self._research.jobs(status=JOB_PENDING)),
            jobs_running=len(await self._research.jobs(status=JOB_RUNNING)),
            promotions_shadow=len(
                await self._research.promotions(status=PROMOTION_SHADOW)
            ),
            promotions_pending_approval=len(
                await self._research.promotions(status=PROMOTION_PASSED)
            ),
            snapshots_stored=await self._store.snapshot_count(),
        )

    async def portfolio_pulse(self) -> PortfolioPulse:
        """The portfolio figures the alert rules read."""
        snapshots = await self._portfolio.get_snapshots(self._portfolio_id)
        statistics = await self._portfolio.statistics(self._portfolio_id)
        drawdown = snapshots[-1].drawdown if snapshots else 0.0
        return PortfolioPulse(
            drawdown=drawdown,
            consecutive_losses=statistics.consecutive_losses,
        )

    # --- Ticks -------------------------------------------------------------------------

    async def alert_tick(self) -> int:
        """Flush telemetry, then run every alert rule once."""
        await self._collector.flush()
        pulse = await self.portfolio_pulse()
        beats = self._health.heartbeat_ages(
            await self._store.heartbeats(),
            now=self._clock.now(),
            stale_ms=self._settings.heartbeat_stale_ms,
        )
        return await self._alerts.evaluate(portfolio=pulse, heartbeats=beats)

    async def capture_snapshot(self) -> StateSnapshotRecord:
        """Persist one full-system state snapshot (Book I 10.17)."""
        status = await self.ops_status()
        payload = json.dumps(_snapshot_payload(status), sort_keys=True)
        now = self._clock.now()
        snapshot_id = await self._store.insert_snapshot(taken_at=now, payload=payload)
        await self._announce_snapshot(snapshot_id)
        return StateSnapshotRecord(
            snapshot_id=snapshot_id, taken_at=now, payload=payload
        )

    async def _announce_snapshot(self, snapshot_id: int) -> None:
        await self._bus.publish(
            monitoring_event(
                MonitoringEvent.SNAPSHOT_STORED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={"snapshot_id": snapshot_id},
            )
        )

    async def prune(self) -> int:
        """Apply the configured retention to metrics and snapshots."""
        cutoff = (
            self._clock.now().epoch_ms
            - self._settings.metric_retention_days * _DAY_MS
        )
        removed = await self._store.prune(older_than_ms=cutoff)
        if removed:
            self._logger.info("monitoring_pruned", rows=removed)
        return removed


def _snapshot_payload(status: OperationsStatus) -> dict[str, object]:
    """The serialized form of one operations snapshot."""
    return {
        "as_of_ms": status.as_of.epoch_ms,
        "overall_health": status.overall_health.value,
        "components": {
            component.component: component.state.value
            for component in status.components
        },
        "kill_switch": status.kill_switch.value,
        "kill_switch_reason": status.kill_switch_reason,
        "incidents_open": status.incidents_open,
        "error_budget": {
            "operations": status.error_budget.operations,
            "errors": status.error_budget.errors,
            "error_rate": status.error_budget.error_rate,
            "exhausted": status.error_budget.exhausted,
        },
        "portfolio": {
            "equity": status.equity,
            "cash": status.cash,
            "drawdown": status.drawdown,
            "open_positions": status.open_positions,
            "closed_trades": status.closed_trades,
            "win_rate": status.win_rate,
            "r_sum": status.r_sum,
        },
        "research": {
            "jobs_pending": status.jobs_pending,
            "jobs_running": status.jobs_running,
            "promotions_shadow": status.promotions_shadow,
            "promotions_pending_approval": status.promotions_pending_approval,
        },
        "heartbeats": {
            beat.component: beat.age_ms for beat in status.heartbeats
        },
    }

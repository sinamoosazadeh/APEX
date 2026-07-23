"""Alert engine (Book II 26.20-26.22, 26.26).

Threshold rules AND pattern rules (26.20: an alert is not only a
threshold breach - "latency increasing for N observations" is one
too), the six-level severity ladder (26.21), mandatory deduplication
("if an error occurs a thousand times, a thousand alerts must not be
sent" - 26.22: recurrences within the window fold into one alert with
a count), and incident creation on critical alerts (26.26). Every
raised alert publishes a catalog event so downstream surfaces (the
Telegram console) deliver it.
"""

from dataclasses import dataclass
from itertools import pairwise
from typing import Final

from apex.core.contracts.interfaces import IEventBus
from apex.core.logging import StructuredLogger
from apex.core.time.clock import Clock
from apex.monitoring.collector import (
    METRIC_ERRORS_TOTAL,
    METRIC_STREAM_DISCONNECTS,
)
from apex.monitoring.config import MonitoringSettings
from apex.monitoring.events import MonitoringEvent, monitoring_event
from apex.monitoring.killswitch import KillSwitchEngine
from apex.monitoring.records import AlertSeverity, HeartbeatAge
from apex.monitoring.store import SqliteMonitoringRepository

_SOURCE: Final[str] = "apex.monitoring.alerts"


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioPulse:
    """The portfolio figures the alert rules read each tick."""

    drawdown: float
    consecutive_losses: int


class AlertEngine:
    """Evaluates alert rules and manages deduplicated delivery."""

    def __init__(
        self,
        *,
        settings: MonitoringSettings,
        store: SqliteMonitoringRepository,
        kill_switch: KillSwitchEngine,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._settings = settings
        self._store = store
        self._kill_switch = kill_switch
        self._bus = bus
        self._clock = clock
        self._logger = logger

    # --- Raising -----------------------------------------------------------------

    async def raise_alert(
        self,
        *,
        severity: AlertSeverity,
        category: str,
        message: str,
        dedup_key: str,
    ) -> bool:
        """Raise one alert; dedups within the window. True when new."""
        now = self._clock.now()
        cutoff = now.epoch_ms - self._settings.dedup_window_ms
        existing = await self._store.recent_alert(dedup_key, since_ms=cutoff)
        if existing is not None:
            escalated = severity.rank > existing.severity.rank
            kept = severity if escalated else existing.severity
            await self._store.bump_alert(existing.alert_id, at=now, severity=kept)
            if not escalated:
                return False
        incident_id = None
        if severity.rank >= AlertSeverity.CRITICAL.rank:
            incident_id = await self._ensure_incident(severity, message, dedup_key)
        if existing is None:
            await self._store.insert_alert(
                severity=severity,
                category=category,
                message=message,
                dedup_key=dedup_key,
                at=now,
                incident_id=incident_id,
            )
        await self._announce(severity, category, message, dedup_key)
        await self._kill_switch.auto_engage(severity=severity, reason=dedup_key)
        return True

    async def _ensure_incident(
        self, severity: AlertSeverity, message: str, dedup_key: str
    ) -> int:
        """Open an incident for a critical alert unless one is open."""
        existing = await self._store.open_incident_for(dedup_key)
        if existing is not None:
            return existing.incident_id
        incident_id = await self._store.insert_incident(
            opened_at=self._clock.now(),
            severity=severity,
            summary=message,
            dedup_key=dedup_key,
        )
        await self._bus.publish(
            monitoring_event(
                MonitoringEvent.INCIDENT_OPENED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "incident_id": incident_id,
                    "severity": severity.value,
                    "summary": message,
                },
            )
        )
        return incident_id

    async def _announce(
        self, severity: AlertSeverity, category: str, message: str, dedup_key: str
    ) -> None:
        await self._bus.publish(
            monitoring_event(
                MonitoringEvent.ALERT_RAISED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "severity": severity.value,
                    "category": category,
                    "message": message,
                    "dedup_key": dedup_key,
                },
            )
        )
        self._logger.warning(
            "alert_raised",
            severity=severity.value,
            category=category,
            dedup_key=dedup_key,
        )

    # --- Rules --------------------------------------------------------------------

    async def evaluate(
        self,
        *,
        portfolio: PortfolioPulse,
        heartbeats: tuple[HeartbeatAge, ...],
    ) -> int:
        """Run every rule once; returns how many alerts were raised."""
        raised = 0
        raised += await self._rule_error_burst()
        raised += await self._rule_disconnects()
        raised += await self._rule_drawdown(portfolio)
        raised += await self._rule_loss_streak(portfolio)
        raised += await self._rule_stage_latency()
        raised += await self._rule_latency_trend()
        raised += await self._rule_heartbeats(heartbeats)
        return raised

    async def _rule_error_burst(self) -> int:
        now_ms = self._clock.now().epoch_ms
        since = now_ms - self._settings.error_burst_window_ms
        errors = await self._store.count_metric(METRIC_ERRORS_TOTAL, since_ms=since)
        if errors < self._settings.error_burst_count:
            return 0
        raised = await self.raise_alert(
            severity=AlertSeverity.CRITICAL,
            category="system",
            message=f"error burst: {errors} errors in the window",
            dedup_key="system.error_burst",
        )
        return int(raised)

    async def _rule_disconnects(self) -> int:
        now_ms = self._clock.now().epoch_ms
        since = now_ms - self._settings.error_burst_window_ms
        drops = await self._store.count_metric(
            METRIC_STREAM_DISCONNECTS, since_ms=since
        )
        if drops < self._settings.disconnect_burst_count:
            return 0
        raised = await self.raise_alert(
            severity=AlertSeverity.HIGH,
            category="exchange",
            message=f"stream instability: {drops} disconnects in the window",
            dedup_key="exchange.stream_disconnects",
        )
        return int(raised)

    async def _rule_drawdown(self, portfolio: PortfolioPulse) -> int:
        if portfolio.drawdown >= self._settings.drawdown_critical:
            raised = await self.raise_alert(
                severity=AlertSeverity.EMERGENCY,
                category="portfolio",
                message=f"portfolio drawdown {portfolio.drawdown:.2%} at critical",
                dedup_key="portfolio.drawdown_critical",
            )
            return int(raised)
        if portfolio.drawdown >= self._settings.drawdown_warning:
            raised = await self.raise_alert(
                severity=AlertSeverity.HIGH,
                category="portfolio",
                message=f"portfolio drawdown {portfolio.drawdown:.2%} at warning",
                dedup_key="portfolio.drawdown_warning",
            )
            return int(raised)
        return 0

    async def _rule_loss_streak(self, portfolio: PortfolioPulse) -> int:
        if portfolio.consecutive_losses < self._settings.loss_streak_high:
            return 0
        raised = await self.raise_alert(
            severity=AlertSeverity.HIGH,
            category="portfolio",
            message=f"{portfolio.consecutive_losses} consecutive losing trades",
            dedup_key="portfolio.loss_streak",
        )
        return int(raised)

    async def _rule_stage_latency(self) -> int:
        now_ms = self._clock.now().epoch_ms
        since = now_ms - self._settings.error_burst_window_ms
        values = await self._store.metric_values("loop.bar.total_ms", since_ms=since)
        if not values:
            return 0
        latest = values[-1][1]
        if latest >= self._settings.stage_latency_critical_ms:
            raised = await self.raise_alert(
                severity=AlertSeverity.HIGH,
                category="infrastructure",
                message=f"bar processing took {latest:.0f}ms (critical threshold)",
                dedup_key="infrastructure.bar_latency_critical",
            )
            return int(raised)
        if latest >= self._settings.stage_latency_warning_ms:
            raised = await self.raise_alert(
                severity=AlertSeverity.MEDIUM,
                category="infrastructure",
                message=f"bar processing took {latest:.0f}ms (warning threshold)",
                dedup_key="infrastructure.bar_latency_warning",
            )
            return int(raised)
        return 0

    async def _rule_latency_trend(self) -> int:
        """The 26.20 pattern rule: latency strictly increasing."""
        window = self._settings.trend_window
        now_ms = self._clock.now().epoch_ms
        since = now_ms - self._settings.slo_window_ms
        values = await self._store.metric_values("loop.bar.total_ms", since_ms=since)
        if len(values) < window:
            return 0
        tail = [value for _, value in values[-window:]]
        if not all(later > earlier for earlier, later in pairwise(tail)):
            return 0
        raised = await self.raise_alert(
            severity=AlertSeverity.MEDIUM,
            category="infrastructure",
            message=f"bar processing latency increasing across {window} bars",
            dedup_key="infrastructure.latency_trend",
        )
        return int(raised)

    async def _rule_heartbeats(self, heartbeats: tuple[HeartbeatAge, ...]) -> int:
        raised = 0
        for beat in heartbeats:
            if not beat.stale:
                continue
            new = await self.raise_alert(
                severity=AlertSeverity.HIGH,
                category="health",
                message=f"heartbeat lost: {beat.component} ({beat.age_ms}ms old)",
                dedup_key=f"health.heartbeat.{beat.component}",
            )
            raised += int(new)
        return raised

"""Alert engine: dedup, escalation, incidents, rules, auto-engage."""

import asyncio
from pathlib import Path

from apex.core.time.clock import ManualClock
from apex.monitoring.alerts import AlertEngine, PortfolioPulse
from apex.monitoring.collector import METRIC_ERRORS_TOTAL, TelemetryCollector
from apex.monitoring.events import MonitoringEvent
from apex.monitoring.killswitch import KillSwitchEngine
from apex.monitoring.records import AlertSeverity, HeartbeatAge, KillSwitchLevel
from apex.monitoring.store import SqliteMonitoringRepository

from tests.conftest import T0
from tests.unit.monitoring.support import logger, make_bus, settings, store_at


def build(
    tmp_path: Path, clock: ManualClock
) -> tuple[AlertEngine, SqliteMonitoringRepository, KillSwitchEngine, object]:
    store = store_at(tmp_path)
    bus = make_bus(clock)
    config = settings()
    kill_switch = KillSwitchEngine(
        settings=config, store=store, bus=bus, clock=clock, logger=logger()
    )
    engine = AlertEngine(
        settings=config,
        store=store,
        kill_switch=kill_switch,
        bus=bus,
        clock=clock,
        logger=logger(),
    )
    return engine, store, kill_switch, bus


def calm() -> PortfolioPulse:
    return PortfolioPulse(drawdown=0.0, consecutive_losses=0)


class TestDeduplication:
    def test_recurrence_bumps_instead_of_new_alert(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, _, _ = build(tmp_path, clock)
            await store.open()
            first = await engine.raise_alert(
                severity=AlertSeverity.HIGH,
                category="portfolio",
                message="drawdown",
                dedup_key="portfolio.drawdown_warning",
            )
            clock.advance_ms(1_000)
            second = await engine.raise_alert(
                severity=AlertSeverity.HIGH,
                category="portfolio",
                message="drawdown",
                dedup_key="portfolio.drawdown_warning",
            )
            assert first is True and second is False
            alerts = await store.alerts()
            assert len(alerts) == 1
            assert alerts[0].count == 2
            await store.close()

        asyncio.run(scenario())

    def test_escalation_re_announces(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, _, _ = build(tmp_path, clock)
            await store.open()
            await engine.raise_alert(
                severity=AlertSeverity.MEDIUM,
                category="system",
                message="latency",
                dedup_key="infra.latency",
            )
            clock.advance_ms(1_000)
            escalated = await engine.raise_alert(
                severity=AlertSeverity.HIGH,
                category="system",
                message="latency",
                dedup_key="infra.latency",
            )
            assert escalated is True
            alerts = await store.alerts()
            assert alerts[0].severity is AlertSeverity.HIGH
            await store.close()

        asyncio.run(scenario())

    def test_new_alert_after_window_elapses(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, _, _ = build(tmp_path, clock)
            await store.open()
            await engine.raise_alert(
                severity=AlertSeverity.LOW,
                category="system",
                message="x",
                dedup_key="k",
            )
            clock.advance_ms(120_000)  # beyond the 60s dedup window
            fresh = await engine.raise_alert(
                severity=AlertSeverity.LOW,
                category="system",
                message="x",
                dedup_key="k",
            )
            assert fresh is True
            assert len(await store.alerts()) == 2
            await store.close()

        asyncio.run(scenario())


class TestIncidentsAndAutoEngage:
    def test_critical_opens_incident_once(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, _, _ = build(tmp_path, clock)
            await store.open()
            await engine.raise_alert(
                severity=AlertSeverity.CRITICAL,
                category="system",
                message="burst",
                dedup_key="system.error_burst",
            )
            clock.advance_ms(120_000)
            await engine.raise_alert(
                severity=AlertSeverity.CRITICAL,
                category="system",
                message="burst",
                dedup_key="system.error_burst",
            )
            assert len(await store.open_incidents()) == 1
            await store.close()

        asyncio.run(scenario())

    def test_emergency_auto_engages_kill_switch(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, kill_switch, bus = build(tmp_path, clock)
            await store.open()
            await engine.raise_alert(
                severity=AlertSeverity.EMERGENCY,
                category="portfolio",
                message="drawdown critical",
                dedup_key="portfolio.drawdown_critical",
            )
            assert (await kill_switch.level()) is KillSwitchLevel.ENTRIES_DISABLED
            journal_types = [
                event.event_type
                for event in bus.journal.replay()  # type: ignore[attr-defined]
            ]
            assert MonitoringEvent.KILL_SWITCH_CHANGED.value in journal_types
            await store.close()

        asyncio.run(scenario())


class TestRules:
    def test_error_burst_rule_fires_critical(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, _, _ = build(tmp_path, clock)
            await store.open()
            collector = TelemetryCollector(store=store, clock=clock, logger=logger())
            for _ in range(3):
                collector.error()
            await collector.flush()
            assert await store.count_metric(METRIC_ERRORS_TOTAL, since_ms=0) == 3
            raised = await engine.evaluate(portfolio=calm(), heartbeats=())
            assert raised >= 1
            alerts = await store.alerts()
            assert any(alert.dedup_key == "system.error_burst" for alert in alerts)
            await store.close()

        asyncio.run(scenario())

    def test_drawdown_rules_tier(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, _, _ = build(tmp_path, clock)
            await store.open()
            await engine.evaluate(
                portfolio=PortfolioPulse(drawdown=0.06, consecutive_losses=0),
                heartbeats=(),
            )
            warning = await store.recent_alert(
                "portfolio.drawdown_warning", since_ms=0
            )
            assert warning is not None
            assert warning.severity is AlertSeverity.HIGH
            await engine.evaluate(
                portfolio=PortfolioPulse(drawdown=0.12, consecutive_losses=0),
                heartbeats=(),
            )
            critical = await store.recent_alert(
                "portfolio.drawdown_critical", since_ms=0
            )
            assert critical is not None
            assert critical.severity is AlertSeverity.EMERGENCY
            await store.close()

        asyncio.run(scenario())

    def test_latency_trend_pattern_rule(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, _, _ = build(tmp_path, clock)
            await store.open()
            collector = TelemetryCollector(store=store, clock=clock, logger=logger())
            for value in (10.0, 20.0, 30.0, 40.0, 50.0):
                collector.metric("loop.bar.total_ms", value)
                clock.advance_ms(1_000)
            await collector.flush()
            await engine.evaluate(portfolio=calm(), heartbeats=())
            trend = await store.recent_alert(
                "infrastructure.latency_trend", since_ms=0
            )
            assert trend is not None
            await store.close()

        asyncio.run(scenario())

    def test_stale_heartbeat_alerts(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            engine, store, _, _ = build(tmp_path, clock)
            await store.open()
            beats = (
                HeartbeatAge(component="operations_loop", age_ms=60_000, stale=True),
                HeartbeatAge(component="fresh", age_ms=1_000, stale=False),
            )
            raised = await engine.evaluate(portfolio=calm(), heartbeats=beats)
            assert raised == 1
            alert = await store.recent_alert(
                "health.heartbeat.operations_loop", since_ms=0
            )
            assert alert is not None
            await store.close()

        asyncio.run(scenario())

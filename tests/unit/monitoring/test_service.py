"""Monitoring service: ops feed, snapshots, retention (kernel-booted)."""

import asyncio
import json
from pathlib import Path

from apex.core.enums import HealthState
from apex.core.time.clock import ManualClock
from apex.kernel.kernel import Kernel
from apex.monitoring.records import AlertSeverity, KillSwitchLevel
from apex.monitoring.service import MonitoringService

from tests.conftest import T0


class TestOpsStatus:
    def test_fresh_platform_reports_clean_status(self, config_dir: Path) -> None:
        async def scenario() -> None:
            kernel = Kernel(config_dir=config_dir, clock=ManualClock(T0))
            await kernel.boot()
            try:
                service = kernel.container.resolve(MonitoringService)
                status = await service.ops_status()
                assert status.overall_health is HealthState.HEALTHY
                assert len(status.components) == 12  # every kernel module
                assert status.kill_switch is KillSwitchLevel.NONE
                assert status.incidents_open == 0
                assert status.open_positions == 0
                assert status.jobs_pending == 0
                assert not status.error_budget.exhausted
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())

    def test_snapshot_persists_full_state(self, config_dir: Path) -> None:
        async def scenario() -> None:
            kernel = Kernel(config_dir=config_dir, clock=ManualClock(T0))
            await kernel.boot()
            try:
                service = kernel.container.resolve(MonitoringService)
                snapshot = await service.capture_snapshot()
                payload = json.loads(snapshot.payload)
                assert payload["overall_health"] == "healthy"
                assert payload["kill_switch"] == "none"
                assert "monitoring_platform" in payload["components"]
                assert "telegram_console" in payload["components"]
                status = await service.ops_status()
                assert status.snapshots_stored == 1
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())

    def test_alert_tick_raises_and_ops_feed_carries_it(
        self, config_dir: Path
    ) -> None:
        async def scenario() -> None:
            kernel = Kernel(config_dir=config_dir, clock=ManualClock(T0))
            await kernel.boot()
            try:
                service = kernel.container.resolve(MonitoringService)
                raised = await service.raise_alert(
                    severity=AlertSeverity.HIGH,
                    category="system",
                    message="synthetic",
                    dedup_key="test.synthetic",
                )
                assert raised is True
                status = await service.ops_status()
                assert any(
                    alert.dedup_key == "test.synthetic"
                    for alert in status.alerts_recent
                )
                # A quiet platform tick raises nothing further.
                assert await service.alert_tick() == 0
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())

    def test_prune_respects_retention(self, config_dir: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            kernel = Kernel(config_dir=config_dir, clock=clock)
            await kernel.boot()
            try:
                service = kernel.container.resolve(MonitoringService)
                service.collector.metric("loop.bar.total_ms", 5.0)
                await service.collector.flush()
                assert await service.prune() == 0  # young samples stay
                clock.advance_ms(15 * 86_400_000)  # beyond 14-day retention
                assert await service.prune() >= 1
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())

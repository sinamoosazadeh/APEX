"""Shared helpers for the monitoring test suite (existing conventions)."""

import io
from pathlib import Path

from apex.core.events.bus import InProcessEventBus
from apex.core.events.journal import EventJournal
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.time.clock import ManualClock
from apex.monitoring.config import MonitoringSettings
from apex.monitoring.store import SqliteMonitoringRepository

from tests.conftest import T0


def logger() -> StructuredLogger:
    """A quiet structured logger for tests."""
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.monitoring")


def make_bus(clock: ManualClock) -> InProcessEventBus:
    """A real in-process bus over a small journal."""
    return InProcessEventBus(
        journal=EventJournal(capacity=200),
        clock=clock,
        logger=logger(),
        fail_fast=False,
    )


def store_at(tmp_path: Path) -> SqliteMonitoringRepository:
    """An unopened monitoring store under the test's tmp dir."""
    return SqliteMonitoringRepository(database_path=tmp_path / "monitoring.sqlite")


def settings(**overrides: object) -> MonitoringSettings:
    """Test settings with small, fast windows."""
    base: dict[str, object] = {
        "dedup_window_ms": 60_000,
        "error_burst_count": 3,
        "error_burst_window_ms": 60_000,
        "disconnect_burst_count": 2,
        "heartbeat_stale_ms": 10_000,
        "slo_window_ms": 120_000,
        "slo_max_error_rate": 0.2,
        "slo_min_operations": 5,
        "snapshot_interval_ms": 10_000,
    }
    base.update(overrides)
    return MonitoringSettings(**base)  # type: ignore[arg-type]

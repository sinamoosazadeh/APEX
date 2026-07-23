"""Monitoring store: metrics, heartbeats, alerts, incidents, kill switch."""

import asyncio
from pathlib import Path

import pytest
from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp
from apex.monitoring.records import AlertSeverity, KillSwitchLevel, MetricSample

from tests.conftest import T0
from tests.unit.monitoring.support import store_at


def at(offset_ms: int) -> Timestamp:
    return Timestamp(epoch_ms=T0.epoch_ms + offset_ms)


def sample(name: str, value: float, offset_ms: int) -> MetricSample:
    return MetricSample(name=name, value=value, recorded_at=at(offset_ms), tags={})


class TestLifecycle:
    def test_double_open_rejected(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            with pytest.raises(StorageError):
                await store.open()
            await store.close()

        asyncio.run(scenario())

    def test_unopened_store_rejected(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            with pytest.raises(StorageError):
                await store.count_metric("x", since_ms=0)

        asyncio.run(scenario())


class TestMetrics:
    def test_insert_count_values_and_prune(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            stored = await store.insert_metrics(
                [
                    sample("loop.bar.total_ms", 10.0, 0),
                    sample("loop.bar.total_ms", 20.0, 1_000),
                    sample("errors.total", 1.0, 2_000),
                ]
            )
            assert stored == 3
            assert await store.count_metric("loop.bar.total_ms", since_ms=0) == 2
            assert (
                await store.count_metric(
                    "loop.bar.total_ms", since_ms=T0.epoch_ms + 500
                )
                == 1
            )
            values = await store.metric_values("loop.bar.total_ms", since_ms=0)
            assert [value for _, value in values] == [10.0, 20.0]
            removed = await store.prune(older_than_ms=T0.epoch_ms + 1_500)
            assert removed == 2  # two old metric samples, no snapshots
            assert await store.count_metric("loop.bar.total_ms", since_ms=0) == 0
            await store.close()

        asyncio.run(scenario())

    def test_empty_batch_is_noop(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            assert await store.insert_metrics([]) == 0
            await store.close()

        asyncio.run(scenario())


class TestHeartbeats:
    def test_beat_upserts_latest(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            await store.beat("operations_loop", at(0))
            await store.beat("operations_loop", at(5_000))
            beats = await store.heartbeats()
            assert len(beats) == 1
            assert beats[0].component == "operations_loop"
            assert beats[0].beat_at.epoch_ms == T0.epoch_ms + 5_000
            await store.close()

        asyncio.run(scenario())


class TestAlerts:
    def test_insert_recent_and_bump(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            alert_id = await store.insert_alert(
                severity=AlertSeverity.HIGH,
                category="portfolio",
                message="drawdown",
                dedup_key="portfolio.drawdown_warning",
                at=at(0),
            )
            found = await store.recent_alert(
                "portfolio.drawdown_warning", since_ms=0
            )
            assert found is not None and found.alert_id == alert_id
            assert found.count == 1
            await store.bump_alert(
                alert_id, at=at(1_000), severity=AlertSeverity.CRITICAL
            )
            bumped = await store.recent_alert(
                "portfolio.drawdown_warning", since_ms=0
            )
            assert bumped is not None
            assert bumped.count == 2
            assert bumped.severity is AlertSeverity.CRITICAL
            assert bumped.last_at.epoch_ms == T0.epoch_ms + 1_000
            assert await store.recent_alert("other.key", since_ms=0) is None
            await store.close()

        asyncio.run(scenario())


class TestIncidents:
    def test_open_and_resolve(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            incident_id = await store.insert_incident(
                opened_at=at(0),
                severity=AlertSeverity.CRITICAL,
                summary="error burst",
                dedup_key="system.error_burst",
            )
            found = await store.open_incident_for("system.error_burst")
            assert found is not None and found.incident_id == incident_id
            assert len(await store.open_incidents()) == 1
            await store.resolve_incident(incident_id, at=at(2_000))
            assert await store.open_incident_for("system.error_burst") is None
            assert await store.open_incidents() == []
            await store.close()

        asyncio.run(scenario())


class TestSnapshots:
    def test_snapshot_roundtrip_and_count(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            await store.insert_snapshot(taken_at=at(0), payload='{"a": 1}')
            await store.insert_snapshot(taken_at=at(1_000), payload='{"a": 2}')
            snapshots = await store.snapshots(limit=1)
            assert len(snapshots) == 1
            assert snapshots[0].payload == '{"a": 2}'
            assert await store.snapshot_count() == 2
            await store.close()

        asyncio.run(scenario())


class TestKillSwitch:
    def test_history_appends_and_current_is_latest(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = store_at(tmp_path)
            await store.open()
            assert await store.current_kill_switch() is None
            await store.insert_kill_switch(
                level=KillSwitchLevel.PAUSED, reason="op", actor="a", at=at(0)
            )
            await store.insert_kill_switch(
                level=KillSwitchLevel.NONE, reason="resume", actor="a", at=at(1_000)
            )
            current = await store.current_kill_switch()
            assert current is not None
            assert current.level is KillSwitchLevel.NONE
            history = await store.kill_switch_history()
            assert [record.level for record in history] == [
                KillSwitchLevel.NONE,
                KillSwitchLevel.PAUSED,
            ]
            await store.close()

        asyncio.run(scenario())

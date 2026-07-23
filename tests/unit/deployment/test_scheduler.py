"""Scheduler: due computation, durable stamps, pressure deferral."""

import asyncio
from pathlib import Path

from apex.core.exceptions import DeploymentError
from apex.core.time.clock import ManualClock
from apex.deployment.config import DeviceSettings, device_settings, schedule_settings
from apex.deployment.scheduler import DeploymentScheduler

from tests.conftest import T0
from tests.unit.monitoring.support import logger


class MemoryStorage:
    """Dict-backed IStorage stand-in."""

    def __init__(self) -> None:
        self.data: dict[tuple[str, str], bytes] = {}

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def write(self, namespace: str, key: str, payload: bytes) -> None:
        self.data[(namespace, key)] = payload

    async def read(self, namespace: str, key: str) -> bytes | None:
        return self.data.get((namespace, key))

    async def exists(self, namespace: str, key: str) -> bool:
        return (namespace, key) in self.data

    async def delete(self, namespace: str, key: str) -> bool:
        return self.data.pop((namespace, key), None) is not None


class FixedProbe:
    """Injected pressure readings."""

    def __init__(self, *, load: float | None = 0.1, disk: float = 10_000.0) -> None:
        self._load = load
        self._disk = disk

    def load_ratio(self) -> float | None:
        return self._load

    def free_disk_mb(self, path: Path) -> float:
        return self._disk


def build(
    tmp_path: Path,
    clock: ManualClock,
    probe: FixedProbe,
    device: DeviceSettings | None = None,
) -> tuple[DeploymentScheduler, MemoryStorage]:
    storage = MemoryStorage()
    scheduler = DeploymentScheduler(
        device=device if device is not None else device_settings({}),
        schedule=schedule_settings(
            {"jobs": {"study": {"enabled": False}}}
        ),
        storage=storage,
        data_dir=tmp_path,
        clock=clock,
        probe=probe,
        logger=logger(),
    )
    return scheduler, storage


class TestScheduler:
    def test_runs_due_jobs_and_stamps(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            scheduler, _storage = build(tmp_path, clock, FixedProbe())
            ran: list[str] = []

            async def runner(name: str) -> str:
                ran.append(name)
                return f"{name} done"

            runners = {
                name: (lambda bound=name: runner(bound))
                for name in ("sync", "snapshot", "optimize", "backup")
            }
            outcomes = await scheduler.run_due(runners)
            assert sorted(ran) == ["backup", "optimize", "snapshot", "sync"]
            assert all(outcome.ran for outcome in outcomes)
            # A disabled job never runs; stamps make nothing due now.
            assert "study" not in ran
            assert await scheduler.run_due(runners) == []
            # Advance past the shortest cadence: only sync becomes due.
            clock.advance_ms(61 * 60_000)
            second = await scheduler.run_due(runners)
            assert [outcome.name for outcome in second] == ["sync"]

        asyncio.run(scenario())

    def test_pressure_defers_without_stamping(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            scheduler, storage = build(
                tmp_path, clock, FixedProbe(load=3.0)
            )
            outcomes = await scheduler.run_due({})
            assert outcomes and all(o.deferred for o in outcomes)
            assert storage.data == {}  # deferred jobs stay due
            assert scheduler.pressure() is not None

        asyncio.run(scenario())

    def test_low_disk_defers_and_failures_do_not_stamp(
        self, tmp_path: Path
    ) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            low_disk, _ = build(tmp_path, clock, FixedProbe(disk=1.0))
            assert low_disk.pressure() is not None
            scheduler, storage = build(tmp_path, clock, FixedProbe())

            async def failing() -> str:
                raise DeploymentError("boom", code="DEP-003")

            outcomes = await scheduler.run_due({"sync": failing})
            failed = next(o for o in outcomes if o.name == "sync")
            assert not failed.ran and not failed.deferred
            assert "DEP-003" in failed.detail
            assert ("scheduler", "last_run.sync") not in storage.data

        asyncio.run(scenario())

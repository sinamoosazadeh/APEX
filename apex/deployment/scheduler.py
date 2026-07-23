"""Resource-aware recurring jobs (Book V part 7; Appendix A).

The long-horizon planner beside the per-bar operational loop: each
configured job (sync, snapshot, study, optimize, backup) carries a
cadence and a durable last-run stamp in the key/value store. Under
device pressure (load per core or free disk beyond the device.yaml
guards) due jobs are DEFERRED - never run partially (part 7: "the job
is postponed, not executed incompletely"). Battery awareness rides
the same guard on Termux through the OS load signal; a dedicated
battery probe is documented device work, not platform logic.
"""

import os
import shutil
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from apex.core.contracts.interfaces import IStorage
from apex.core.exceptions import ApexError
from apex.core.logging import StructuredLogger
from apex.core.time.clock import Clock
from apex.deployment.config import DeviceSettings, ScheduleSettings

_NAMESPACE: Final[str] = "scheduler"

type JobRunner = Callable[[], Awaitable[str]]


class ResourceProbe(Protocol):
    """Device pressure readings (injectable for tests)."""

    def load_ratio(self) -> float | None:
        """1-minute load average per core; None when unreadable."""
        ...

    def free_disk_mb(self, path: Path) -> float:
        """Free space at ``path`` in megabytes."""
        ...


class SystemResourceProbe:
    """Real readings from the operating system."""

    def load_ratio(self) -> float | None:
        """1-minute load average per core; None when unreadable."""
        try:
            load = os.getloadavg()[0]
        except OSError:
            return None
        return load / (os.cpu_count() or 1)

    def free_disk_mb(self, path: Path) -> float:
        """Free space at ``path`` in megabytes."""
        return shutil.disk_usage(path).free / (1024 * 1024)


@dataclass(frozen=True, slots=True, kw_only=True)
class JobStatus:
    """One job's schedule position."""

    name: str
    enabled: bool
    cadence_minutes: int
    last_run_ms: int | None
    due: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class JobOutcome:
    """One planning pass's verdict for a due job."""

    name: str
    ran: bool
    deferred: bool
    detail: str


class DeploymentScheduler:
    """Durable, resource-guarded recurring-job planner."""

    def __init__(
        self,
        *,
        device: DeviceSettings,
        schedule: ScheduleSettings,
        storage: IStorage,
        data_dir: Path,
        clock: Clock,
        probe: ResourceProbe,
        logger: StructuredLogger,
    ) -> None:
        self._device = device
        self._schedule = schedule
        self._storage = storage
        self._data_dir = data_dir
        self._clock = clock
        self._probe = probe
        self._logger = logger

    async def status(self) -> list[JobStatus]:
        """Every configured job with its due verdict."""
        now_ms = self._clock.now().epoch_ms
        statuses: list[JobStatus] = []
        for job in self._schedule.jobs:
            last = await self._last_run(job.name)
            due = job.enabled and (
                last is None or now_ms - last >= job.cadence_minutes * 60_000
            )
            statuses.append(
                JobStatus(
                    name=job.name,
                    enabled=job.enabled,
                    cadence_minutes=job.cadence_minutes,
                    last_run_ms=last,
                    due=due,
                )
            )
        return statuses

    def pressure(self) -> str | None:
        """The active resource-guard reason, if the device is pressured."""
        ratio = self._probe.load_ratio()
        if ratio is not None and ratio > self._device.max_load_ratio:
            return (
                f"load {ratio:.2f} per core exceeds "
                f"{self._device.max_load_ratio:.2f}"
            )
        free = self._probe.free_disk_mb(self._data_dir)
        if free < self._device.min_free_disk_mb:
            return (
                f"free disk {free:.0f}MB below "
                f"{self._device.min_free_disk_mb}MB"
            )
        return None

    async def run_due(
        self, runners: Mapping[str, JobRunner]
    ) -> list[JobOutcome]:
        """Run every due job (or defer them all under pressure)."""
        outcomes: list[JobOutcome] = []
        guard = self.pressure()
        for status in await self.status():
            if not status.due:
                continue
            if guard is not None:
                self._logger.warning(
                    "job_deferred", job=status.name, reason=guard
                )
                outcomes.append(
                    JobOutcome(
                        name=status.name, ran=False, deferred=True, detail=guard
                    )
                )
                continue
            outcomes.append(await self._run_one(status.name, runners))
        return outcomes

    async def _run_one(
        self, name: str, runners: Mapping[str, JobRunner]
    ) -> JobOutcome:
        runner = runners.get(name)
        if runner is None:
            return JobOutcome(
                name=name, ran=False, deferred=False, detail="no runner wired"
            )
        try:
            detail = await runner()
        except ApexError as error:
            self._logger.failure("scheduled_job_failed", error, job=name)
            return JobOutcome(
                name=name,
                ran=False,
                deferred=False,
                detail=f"{error.code}: {error}",
            )
        await self._stamp(name, self._clock.now().epoch_ms)
        self._logger.info("scheduled_job_completed", job=name, detail=detail)
        return JobOutcome(name=name, ran=True, deferred=False, detail=detail)

    async def _last_run(self, name: str) -> int | None:
        payload = await self._storage.read(_NAMESPACE, f"last_run.{name}")
        if payload is None:
            return None
        try:
            return int(payload.decode("utf-8"))
        except ValueError:
            return None

    async def _stamp(self, name: str, now_ms: int) -> None:
        await self._storage.write(
            _NAMESPACE, f"last_run.{name}", str(now_ms).encode("utf-8")
        )

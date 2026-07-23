"""Deployment CLI runners (Phase 14): package, backup, restore, schedule.

Kernel-booting runners behind ``apex package``, ``apex backup`` and
``apex schedule``; ``apex restore`` deliberately boots NOTHING - state
must never be replaced under a running platform (13.20: recovery
happens before the system comes back up).
"""

from pathlib import Path

from apex import __version__
from apex.core.config import AppConfig, load_config
from apex.core.contracts.interfaces import IClock, IStorage
from apex.core.enums import Timeframe
from apex.core.exceptions import DeploymentError
from apex.core.logging import LoggerFactory
from apex.core.time.clock import Clock, SystemClock
from apex.data.catchup import CatchUpService
from apex.deployment.backup import (
    create_backup,
    prune_backups,
    restore_backup,
    verify_backup,
)
from apex.deployment.config import (
    DeviceSettings,
    device_settings,
    schedule_settings,
)
from apex.deployment.package import write_release
from apex.deployment.scheduler import (
    DeploymentScheduler,
    JobRunner,
    SystemResourceProbe,
)
from apex.kernel.kernel import Kernel
from apex.monitoring.service import MonitoringService
from apex.research.service import ResearchService
from apex.security.audit import SqliteAuditLedger
from apex.security.config import security_settings
from apex.security.service import SecurityService

_STUDY_WINDOW_BARS = 480
_DRAIN_LIMIT = 2


async def run_package(config_dir: Path, *, root: Path) -> list[str]:
    """Boot, publish the signed release package, audit, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        security = kernel.container.resolve(SecurityService)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        manifest_path, archive_path = write_release(
            root,
            root / "dist",
            version=__version__,
            created_at=clock.now(),
            signer=security.sign,
        )
        await security.audit(
            actor="operator",
            action="deployment.package",
            target=archive_path.name,
            result="ok",
            details={"version": __version__},
        )
        signed = "signed" if security.signing_enabled else "no signing key"
        return [
            f"release manifest : {manifest_path}",
            f"release archive  : {archive_path}",
            f"signature        : {signed}",
        ]
    finally:
        await kernel.shutdown()


async def run_backup(config_dir: Path) -> list[str]:
    """Boot, back up the durable state, self-verify, prune, audit."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        device = device_settings(config.section("device"))
        archive = create_backup(
            Path(config.system.data_dir),
            Path(device.backup_dir),
            created_at=clock.now(),
        )
        ok, files, reason = verify_backup(archive)
        if not ok:
            raise DeploymentError(
                "fresh backup failed self-verification",
                code="DEP-004",
                details={"archive": archive.name, "reason": str(reason)},
            )
        pruned = prune_backups(
            Path(device.backup_dir), keep=device.backup_retention
        )
        security = kernel.container.resolve(SecurityService)
        await security.audit(
            actor="operator",
            action="deployment.backup",
            target=archive.name,
            result="ok",
            details={"files": files, "pruned": pruned},
        )
        return [
            f"backup archive : {archive}",
            f"files          : {files} (all checksums verified)",
            f"pruned         : {pruned} old archive(s)",
        ]
    finally:
        await kernel.shutdown()


async def run_restore(
    config_dir: Path, *, archive: Path, force: bool, into: Path | None
) -> list[str]:
    """Verified restore WITHOUT booting the platform (13.20)."""
    config = load_config(config_dir)
    target = into if into is not None else Path(config.system.data_dir)
    restored = restore_backup(archive, target, force=force)
    settings = security_settings(config.section("security"))
    ledger = SqliteAuditLedger(database_path=target / settings.audit_filename)
    await ledger.open()
    try:
        await ledger.append(
            actor="operator",
            action="deployment.restore",
            target=archive.name,
            result="ok",
            details={"files": restored, "target": str(target)},
            occurred_at=SystemClock().now(),
        )
    finally:
        await ledger.close()
    return [f"restored {restored} file(s) into {target} (checksums verified)"]


async def run_schedule(config_dir: Path, *, execute: bool) -> list[str]:
    """Boot, report (and optionally run) the recurring-job table."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        storage = kernel.container.resolve(IStorage)  # type: ignore[type-abstract]
        device = device_settings(config.section("device"))
        scheduler = DeploymentScheduler(
            device=device,
            schedule=schedule_settings(config.section("scheduler")),
            storage=storage,
            data_dir=Path(config.system.data_dir),
            clock=clock,
            probe=SystemResourceProbe(),
            logger=kernel.container.resolve(LoggerFactory).get(
                "deployment.scheduler"
            ),
        )
        lines = [f"pressure   : {scheduler.pressure() or 'none'}"]
        for status in await scheduler.status():
            state = "due" if status.due else ("idle" if status.enabled else "off")
            lines.append(
                f"  {status.name:<9}: {state:<5} every "
                f"{status.cadence_minutes}m"
            )
        if not execute:
            return lines
        outcomes = await scheduler.run_due(
            _runners(kernel, config, device, clock)
        )
        if not outcomes:
            lines.append("nothing due")
        for outcome in outcomes:
            verdict = (
                "ran" if outcome.ran else
                "DEFERRED" if outcome.deferred else "FAILED"
            )
            lines.append(f"  {outcome.name}: {verdict} - {outcome.detail}")
        return lines
    finally:
        await kernel.shutdown()


def _runners(
    kernel: Kernel,
    config: AppConfig,
    device: DeviceSettings,
    clock: Clock,
) -> dict[str, JobRunner]:
    """The wired job implementations (Book V part 7 lifecycle)."""
    research = kernel.container.resolve(ResearchService)
    monitoring = kernel.container.resolve(MonitoringService)
    catchup = kernel.container.resolve(CatchUpService)
    symbols = tuple(config.market.symbols)

    async def sync() -> str:
        report = await catchup.run_once()
        return f"{report.succeeded}/{len(report.results)} series caught up"

    async def snapshot() -> str:
        await monitoring.capture_snapshot()
        return "state snapshot stored"

    async def study() -> str:
        end = clock.now()
        start = end.add_ms(-_STUDY_WINDOW_BARS * Timeframe.H1.duration_ms)
        summary = (
            await research.study(symbols, Timeframe.H1, start=start, end=end)
        ).unwrap()
        return f"{len(summary.studies)} series studied"

    async def optimize() -> str:
        queued = await research.enqueue_cycle(symbols, (Timeframe.H1,))
        summary = (
            await research.orchestrate(
                limit=_DRAIN_LIMIT, default_window_bars=_STUDY_WINDOW_BARS
            )
        ).unwrap()
        return f"queued {queued}, drained {summary.drained}"

    async def backup() -> str:
        archive = create_backup(
            Path(config.system.data_dir),
            Path(device.backup_dir),
            created_at=clock.now(),
        )
        prune_backups(Path(device.backup_dir), keep=device.backup_retention)
        return archive.name

    return {
        "sync": sync,
        "snapshot": snapshot,
        "study": study,
        "optimize": optimize,
        "backup": backup,
    }

"""Deployment platform (Phase 14): packaging, backup, scheduling.

The Book II 29.20/29.25 production layer around the running system:
signed, checksummed release packages; consistent backup and verified
restore of the durable state (stores, vault, optimizer artifacts);
and the resource-aware job scheduler (Book V part 7: on a pressured
device jobs are DEFERRED, never run partially). The service lifecycle
itself ships as Termux scripts under ``deploy/`` - the OS supervises,
APEX stays restart-safe (state recovery is durable by design).
"""

from apex.deployment.backup import create_backup, restore_backup, verify_backup
from apex.deployment.config import (
    DeviceSettings,
    JobSettings,
    ScheduleSettings,
    device_settings,
    schedule_settings,
)
from apex.deployment.package import build_manifest, write_release
from apex.deployment.scheduler import (
    DeploymentScheduler,
    JobOutcome,
    JobStatus,
    SystemResourceProbe,
)

__all__ = [
    "DeploymentScheduler",
    "DeviceSettings",
    "JobOutcome",
    "JobSettings",
    "JobStatus",
    "ScheduleSettings",
    "SystemResourceProbe",
    "build_manifest",
    "create_backup",
    "device_settings",
    "restore_backup",
    "schedule_settings",
    "verify_backup",
    "write_release",
]

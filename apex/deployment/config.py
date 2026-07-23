"""Deployment configuration (``device.yaml`` + ``scheduler.yaml``).

Deep-validates the Phase 14 sections: the device profile with its
resource guards (Book V part 7 Termux budgets - jobs defer under
pressure, they never run partially) and the recurring job table with
per-job cadences. Everything-is-config (Constitution 3.7).
"""

from dataclasses import dataclass, field

from apex.core.config import ConfigSection
from apex.core.exceptions import ConfigurationError

_CODE = "CFG-044"

DEFAULT_JOBS: dict[str, tuple[int, bool]] = {
    # name -> (cadence_minutes, enabled): the Book V part 7 lifecycle.
    "sync": (60, True),         # bar catch-up
    "snapshot": (360, True),    # monitoring state snapshot
    "study": (1_440, True),     # research study (learning fold)
    "optimize": (10_080, True),  # optimization cycle enqueue + drain
    "backup": (1_440, True),    # durable-state backup
}


@dataclass(frozen=True, slots=True, kw_only=True)
class DeviceSettings:
    """The validated device profile (device.yaml)."""

    profile: str = "default"
    max_load_ratio: float = 0.8
    min_free_disk_mb: int = 512
    backup_dir: str = "backups"
    backup_retention: int = 14

    def __post_init__(self) -> None:
        if not self.profile:
            raise ConfigurationError(
                "device.profile must be non-empty", code=_CODE, details={}
            )
        if not 0.0 < self.max_load_ratio <= 4.0:
            raise ConfigurationError(
                "device.resources.max_load_ratio must be in (0, 4]",
                code=_CODE,
                details={},
            )
        if self.min_free_disk_mb < 16:
            raise ConfigurationError(
                "device.resources.min_free_disk_mb must be >= 16",
                code=_CODE,
                details={},
            )
        if not self.backup_dir:
            raise ConfigurationError(
                "device.backup.dir must be non-empty", code=_CODE, details={}
            )
        if self.backup_retention < 1:
            raise ConfigurationError(
                "device.backup.retention must be >= 1", code=_CODE, details={}
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class JobSettings:
    """One recurring job's schedule."""

    name: str
    cadence_minutes: int
    enabled: bool

    def __post_init__(self) -> None:
        if self.cadence_minutes < 1:
            raise ConfigurationError(
                f"scheduler.jobs.{self.name}.cadence_minutes must be >= 1",
                code=_CODE,
                details={},
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScheduleSettings:
    """The validated recurring-job table (scheduler.yaml)."""

    jobs: tuple[JobSettings, ...] = field(default_factory=tuple)

    def job(self, name: str) -> JobSettings | None:
        """One job by name, if configured."""
        for entry in self.jobs:
            if entry.name == name:
                return entry
        return None


def _mapping(section: ConfigSection, key: str) -> ConfigSection:
    value = section.get(key, {})
    if not isinstance(value, dict):
        raise ConfigurationError(
            f"deployment section {key} must be a mapping",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def _number(section: ConfigSection, key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            f"deployment value {key} must be a number",
            code=_CODE,
            details={"found": repr(value)},
        )
    return float(value)


def _integer(section: ConfigSection, key: str, default: int) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"deployment value {key} must be an integer",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def _string(section: ConfigSection, key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(
            f"deployment value {key} must be a string",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def device_settings(section: ConfigSection) -> DeviceSettings:
    """Parse and validate device.yaml."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "device configuration must be a mapping", code=_CODE, details={}
        )
    defaults = DeviceSettings()
    resources = _mapping(section, "resources")
    backup = _mapping(section, "backup")
    return DeviceSettings(
        profile=_string(section, "profile", defaults.profile),
        max_load_ratio=_number(
            resources, "max_load_ratio", defaults.max_load_ratio
        ),
        min_free_disk_mb=_integer(
            resources, "min_free_disk_mb", defaults.min_free_disk_mb
        ),
        backup_dir=_string(backup, "dir", defaults.backup_dir),
        backup_retention=_integer(backup, "retention", defaults.backup_retention),
    )


def schedule_settings(section: ConfigSection) -> ScheduleSettings:
    """Parse and validate scheduler.yaml (defaults for absent jobs)."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "scheduler configuration must be a mapping", code=_CODE, details={}
        )
    configured = _mapping(section, "jobs")
    jobs: list[JobSettings] = []
    for name, (cadence, enabled) in DEFAULT_JOBS.items():
        raw = configured.get(name, {})
        if not isinstance(raw, dict):
            raise ConfigurationError(
                f"scheduler.jobs.{name} must be a mapping",
                code=_CODE,
                details={"found": repr(raw)},
            )
        jobs.append(
            JobSettings(
                name=name,
                cadence_minutes=_integer(raw, "cadence_minutes", cadence),
                enabled=bool(raw.get("enabled", enabled)),
            )
        )
    unknown = set(configured) - set(DEFAULT_JOBS)
    if unknown:
        raise ConfigurationError(
            "scheduler.jobs carries unknown job names",
            code=_CODE,
            details={"unknown": ", ".join(sorted(unknown))},
        )
    return ScheduleSettings(jobs=tuple(jobs))

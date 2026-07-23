"""Deployment configuration: defaults, overrides, guards."""

import pytest
from apex.core.exceptions import ConfigurationError
from apex.deployment.config import device_settings, schedule_settings


class TestDeviceSettings:
    def test_defaults_and_overrides(self) -> None:
        default = device_settings({})
        assert default.max_load_ratio == 0.8
        assert default.backup_retention == 14
        tuned = device_settings(
            {
                "profile": "termux",
                "resources": {"max_load_ratio": 0.5, "min_free_disk_mb": 256},
                "backup": {"dir": "vaulted", "retention": 7},
            }
        )
        assert tuned.profile == "termux"
        assert tuned.max_load_ratio == 0.5
        assert tuned.min_free_disk_mb == 256
        assert tuned.backup_dir == "vaulted"
        assert tuned.backup_retention == 7

    def test_guards(self) -> None:
        with pytest.raises(ConfigurationError):
            device_settings({"resources": {"max_load_ratio": 0}})
        with pytest.raises(ConfigurationError):
            device_settings({"backup": {"retention": 0}})


class TestScheduleSettings:
    def test_defaults_cover_the_lifecycle(self) -> None:
        schedule = schedule_settings({"jobs": {}})
        names = {job.name for job in schedule.jobs}
        assert names == {"sync", "snapshot", "study", "optimize", "backup"}
        sync = schedule.job("sync")
        assert sync is not None and sync.cadence_minutes == 60 and sync.enabled

    def test_overrides_and_unknown_jobs(self) -> None:
        schedule = schedule_settings(
            {"jobs": {"sync": {"cadence_minutes": 15, "enabled": False}}}
        )
        sync = schedule.job("sync")
        assert sync is not None
        assert sync.cadence_minutes == 15 and not sync.enabled
        with pytest.raises(ConfigurationError):
            schedule_settings({"jobs": {"mystery": {}}})
        with pytest.raises(ConfigurationError):
            schedule_settings({"jobs": {"sync": {"cadence_minutes": 0}}})

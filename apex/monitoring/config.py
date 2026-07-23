"""Monitoring platform configuration (``telemetry.yaml``, Phase 12).

Deep-validates the monitoring sections: metric retention, heartbeat
staleness, alert thresholds and deduplication, the kill-switch
auto-engage policy, the SLO error budget (Book II 26.28), snapshot
cadence and the operational loop's guards. Everything-is-config
(Constitution 3.7): the engines hardcode no threshold, window or
cadence. The spec states the requirements but not the numbers
(26.22/10.17 silences) - the defaults here are the platform's
documented choices.
"""

from dataclasses import dataclass

from apex.core.config import ConfigSection
from apex.core.exceptions import ConfigurationError
from apex.monitoring.records import AlertSeverity, KillSwitchLevel

_CODE = "CFG-040"


@dataclass(frozen=True, slots=True, kw_only=True)
class MonitoringSettings:
    """The validated monitoring platform configuration."""

    metric_retention_days: int = 14
    heartbeat_stale_ms: int = 900_000
    dedup_window_ms: int = 300_000
    error_burst_count: int = 5
    error_burst_window_ms: int = 600_000
    disconnect_burst_count: int = 3
    drawdown_warning: float = 0.05
    drawdown_critical: float = 0.10
    loss_streak_high: int = 4
    stage_latency_warning_ms: float = 15_000.0
    stage_latency_critical_ms: float = 60_000.0
    trend_window: int = 5
    kill_switch_auto_engage: bool = True
    kill_switch_engage_severity: AlertSeverity = AlertSeverity.EMERGENCY
    kill_switch_engage_level: KillSwitchLevel = KillSwitchLevel.ENTRIES_DISABLED
    slo_window_ms: int = 86_400_000
    slo_max_error_rate: float = 0.05
    slo_min_operations: int = 20
    snapshot_interval_ms: int = 300_000
    promotion_guard_trades: int = 10
    promotion_guard_floor_r: float = -5.0

    def __post_init__(self) -> None:
        _require(self.metric_retention_days >= 1, "metric_retention_days must be >= 1")
        _require(self.heartbeat_stale_ms >= 1_000, "heartbeat_stale_ms must be >= 1000")
        _require(self.dedup_window_ms >= 1_000, "dedup_window_ms must be >= 1000")
        _require(self.error_burst_count >= 1, "error_burst_count must be >= 1")
        _require(
            self.error_burst_window_ms >= 1_000, "error_burst_window_ms must be >= 1000"
        )
        _require(self.disconnect_burst_count >= 1, "disconnect_burst_count must be >= 1")
        _require(
            0.0 < self.drawdown_warning < self.drawdown_critical <= 1.0,
            "drawdown thresholds must satisfy 0 < warning < critical <= 1",
        )
        _require(self.loss_streak_high >= 1, "loss_streak_high must be >= 1")
        _require(
            0.0 < self.stage_latency_warning_ms < self.stage_latency_critical_ms,
            "stage latency thresholds must satisfy 0 < warning < critical",
        )
        _require(self.trend_window >= 3, "trend_window must be >= 3")
        _require(self.slo_window_ms >= 60_000, "slo_window_ms must be >= 60000")
        _require(
            0.0 < self.slo_max_error_rate < 1.0, "slo_max_error_rate must be in (0, 1)"
        )
        _require(self.slo_min_operations >= 1, "slo_min_operations must be >= 1")
        _require(
            self.snapshot_interval_ms >= 10_000, "snapshot_interval_ms must be >= 10000"
        )
        _require(self.promotion_guard_trades >= 1, "promotion_guard_trades must be >= 1")
        _require(
            self.promotion_guard_floor_r < 0.0, "promotion_guard_floor_r must be < 0"
        )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigurationError(message, code=_CODE, details={})


def _mapping(section: ConfigSection, key: str) -> ConfigSection:
    value = section.get(key, {})
    if not isinstance(value, dict):
        raise ConfigurationError(
            f"telemetry.{key} must be a mapping",
            code="CFG-040",
            details={"found": repr(value)},
        )
    return value


def _number(section: ConfigSection, key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            f"telemetry value {key} must be a number",
            code="CFG-040",
            details={"found": repr(value)},
        )
    return float(value)


def _integer(section: ConfigSection, key: str, default: int) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"telemetry value {key} must be an integer",
            code="CFG-040",
            details={"found": repr(value)},
        )
    return value


def _boolean(section: ConfigSection, key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(
            f"telemetry value {key} must be a boolean",
            code="CFG-040",
            details={"found": repr(value)},
        )
    return value


def _severity(section: ConfigSection, key: str, default: AlertSeverity) -> AlertSeverity:
    value = section.get(key, default.value)
    values = {severity.value: severity for severity in AlertSeverity}
    if not isinstance(value, str) or value not in values:
        raise ConfigurationError(
            f"telemetry value {key} must be one of {sorted(values)}",
            code="CFG-040",
            details={"found": repr(value)},
        )
    return values[value]


def _level(section: ConfigSection, key: str, default: KillSwitchLevel) -> KillSwitchLevel:
    value = section.get(key, default.value)
    values = {level.value: level for level in KillSwitchLevel}
    if not isinstance(value, str) or value not in values:
        raise ConfigurationError(
            f"telemetry value {key} must be one of {sorted(values)}",
            code="CFG-040",
            details={"found": repr(value)},
        )
    return values[value]


def monitoring_settings(section: ConfigSection) -> MonitoringSettings:
    """Parse and validate the monitoring sections of telemetry.yaml."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "telemetry configuration must be a mapping", code="CFG-040", details={}
        )
    defaults = MonitoringSettings()
    metrics = _mapping(section, "metrics")
    heartbeat = _mapping(section, "heartbeat")
    alerts = _mapping(section, "alerts")
    kill_switch = _mapping(section, "kill_switch")
    slo = _mapping(section, "slo")
    snapshots = _mapping(section, "snapshots")
    loop = _mapping(section, "loop")
    return MonitoringSettings(
        metric_retention_days=_integer(
            metrics, "retention_days", defaults.metric_retention_days
        ),
        heartbeat_stale_ms=_integer(heartbeat, "stale_ms", defaults.heartbeat_stale_ms),
        dedup_window_ms=_integer(alerts, "dedup_window_ms", defaults.dedup_window_ms),
        error_burst_count=_integer(
            alerts, "error_burst_count", defaults.error_burst_count
        ),
        error_burst_window_ms=_integer(
            alerts, "error_burst_window_ms", defaults.error_burst_window_ms
        ),
        disconnect_burst_count=_integer(
            alerts, "disconnect_burst_count", defaults.disconnect_burst_count
        ),
        drawdown_warning=_number(alerts, "drawdown_warning", defaults.drawdown_warning),
        drawdown_critical=_number(
            alerts, "drawdown_critical", defaults.drawdown_critical
        ),
        loss_streak_high=_integer(alerts, "loss_streak_high", defaults.loss_streak_high),
        stage_latency_warning_ms=_number(
            alerts, "stage_latency_warning_ms", defaults.stage_latency_warning_ms
        ),
        stage_latency_critical_ms=_number(
            alerts, "stage_latency_critical_ms", defaults.stage_latency_critical_ms
        ),
        trend_window=_integer(alerts, "trend_window", defaults.trend_window),
        kill_switch_auto_engage=_boolean(
            kill_switch, "auto_engage", defaults.kill_switch_auto_engage
        ),
        kill_switch_engage_severity=_severity(
            kill_switch, "engage_severity", defaults.kill_switch_engage_severity
        ),
        kill_switch_engage_level=_level(
            kill_switch, "engage_level", defaults.kill_switch_engage_level
        ),
        slo_window_ms=_integer(slo, "window_ms", defaults.slo_window_ms),
        slo_max_error_rate=_number(
            slo, "max_error_rate", defaults.slo_max_error_rate
        ),
        slo_min_operations=_integer(
            slo, "min_operations", defaults.slo_min_operations
        ),
        snapshot_interval_ms=_integer(
            snapshots, "interval_ms", defaults.snapshot_interval_ms
        ),
        promotion_guard_trades=_integer(
            loop, "promotion_guard_trades", defaults.promotion_guard_trades
        ),
        promotion_guard_floor_r=_number(
            loop, "promotion_guard_floor_r", defaults.promotion_guard_floor_r
        ),
    )

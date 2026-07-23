"""Monitoring domain records (Book II ch. 26; Book I ch. 10).

The observability layer's value objects: metric samples, heartbeats,
alerts with the six-level severity ladder (26.21), incidents (26.26),
state snapshots (10.17), kill-switch state entries and the unified
operations status (26.29) the dashboards and the Telegram console
render. All frozen, all explicit - no monitoring record is ever a
loose dict.
"""

from dataclasses import dataclass, field
from enum import Enum, unique

from apex.core.enums import HealthState
from apex.core.time.timestamp import Timestamp


@unique
class AlertSeverity(Enum):
    """Smart-alert severity ladder (Book II 26.21), low to high."""

    INFORMATION = "information"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

    @property
    def rank(self) -> int:
        """Ordering key: higher means more severe."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK: dict[AlertSeverity, int] = {
    AlertSeverity.INFORMATION: 0,
    AlertSeverity.LOW: 1,
    AlertSeverity.MEDIUM: 2,
    AlertSeverity.HIGH: 3,
    AlertSeverity.CRITICAL: 4,
    AlertSeverity.EMERGENCY: 5,
}


@unique
class KillSwitchLevel(Enum):
    """Kill-switch escalation ladder (Book II 10.25 response order).

    ``NONE`` trades normally; ``ENTRIES_DISABLED`` blocks new entries
    while everything else runs; ``PAUSED`` stands the decision and
    execution stages aside; ``SAFE_MODE`` pauses AND cancels resting
    venue orders. Position flattening belongs to the Phase 13 security
    platform (Book II 25.29 kill-switch levels).
    """

    NONE = "none"
    ENTRIES_DISABLED = "entries_disabled"
    PAUSED = "paused"
    SAFE_MODE = "safe_mode"

    @property
    def rank(self) -> int:
        """Ordering key: higher means more restrictive."""
        return _KILL_RANK[self]


_KILL_RANK: dict[KillSwitchLevel, int] = {
    KillSwitchLevel.NONE: 0,
    KillSwitchLevel.ENTRIES_DISABLED: 1,
    KillSwitchLevel.PAUSED: 2,
    KillSwitchLevel.SAFE_MODE: 3,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricSample:
    """One recorded metric observation (26.5)."""

    name: str
    value: float
    recorded_at: Timestamp
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class HeartbeatRecord:
    """One component's latest liveness beat (Book I 10.8)."""

    component: str
    beat_at: Timestamp


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertRecord:
    """One deduplicated alert (26.20-26.22)."""

    alert_id: int
    severity: AlertSeverity
    category: str
    message: str
    dedup_key: str
    count: int
    first_at: Timestamp
    last_at: Timestamp
    incident_id: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class IncidentRecord:
    """One incident opened from a critical alert (26.26)."""

    incident_id: int
    opened_at: Timestamp
    severity: AlertSeverity
    summary: str
    dedup_key: str
    status: str
    resolved_at: Timestamp | None


INCIDENT_OPEN = "open"
INCIDENT_RESOLVED = "resolved"


@dataclass(frozen=True, slots=True, kw_only=True)
class StateSnapshotRecord:
    """One periodic full-system state snapshot (Book I 10.17)."""

    snapshot_id: int
    taken_at: Timestamp
    payload: str


@dataclass(frozen=True, slots=True, kw_only=True)
class KillSwitchRecord:
    """One kill-switch state transition (append-only history)."""

    entry_id: int
    level: KillSwitchLevel
    reason: str
    actor: str
    changed_at: Timestamp


@dataclass(frozen=True, slots=True, kw_only=True)
class SloStatus:
    """One error-budget verdict over a sliding window (26.28)."""

    name: str
    window_ms: int
    operations: int
    errors: int
    error_rate: float
    budget: float
    exhausted: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ComponentHealth:
    """One component's live health for the operations center."""

    component: str
    state: HealthState
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class HeartbeatAge:
    """One component's heartbeat age for the operations center."""

    component: str
    age_ms: int
    stale: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationsStatus:
    """The unified operations center feed (Book II 26.29).

    One aggregate every surface renders: overall and per-component
    health, kill-switch state, open alerts, the error budget, the
    portfolio's headline account figures, the research queue and
    promotion pipeline, and heartbeat freshness.
    """

    as_of: Timestamp
    overall_health: HealthState
    components: tuple[ComponentHealth, ...]
    heartbeats: tuple[HeartbeatAge, ...]
    kill_switch: KillSwitchLevel
    kill_switch_reason: str
    alerts_recent: tuple[AlertRecord, ...]
    incidents_open: int
    error_budget: SloStatus
    equity: str
    cash: str
    drawdown: float
    open_positions: int
    closed_trades: int
    win_rate: float
    r_sum: float
    jobs_pending: int
    jobs_running: int
    promotions_shadow: int
    promotions_pending_approval: int
    snapshots_stored: int

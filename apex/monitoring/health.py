"""Health engine (Book I 10.6-10.8; Book II 5.22).

Live health over the running platform: every kernel module's current
:class:`HealthState`, heartbeat freshness, and dependency propagation
(10.7) - a module whose dependency is degraded is itself at least
WARNING; a module whose dependency is offline is itself at least
CRITICAL. The four-state core ladder stays authoritative (never a
parallel enum): the spec's Healthy/Stable collapse onto HEALTHY.
"""

from apex.core.enums import HealthState
from apex.core.time.timestamp import Timestamp
from apex.kernel.health import HealthMonitor
from apex.kernel.modules import ModuleRegistry
from apex.monitoring.records import ComponentHealth, HeartbeatAge, HeartbeatRecord

_SEVERITY_ORDER: dict[HealthState, int] = {
    HealthState.HEALTHY: 0,
    HealthState.WARNING: 1,
    HealthState.CRITICAL: 2,
    HealthState.OFFLINE: 3,
}


def _worse(first: HealthState, second: HealthState) -> HealthState:
    return first if _SEVERITY_ORDER[first] >= _SEVERITY_ORDER[second] else second


class HealthEngine:
    """Aggregates live module health with dependency propagation."""

    def __init__(
        self,
        *,
        registry: ModuleRegistry,
        monitor: HealthMonitor,
    ) -> None:
        self._registry = registry
        self._monitor = monitor

    def assess(self) -> tuple[ComponentHealth, ...]:
        """Every module's live health, dependency-propagated (10.7)."""
        raw: dict[str, HealthState] = {
            name: self._registry.get(name).health() for name in self._registry.names
        }
        effective: dict[str, HealthState] = {}
        for name in self._registry.start_order():
            state = raw[name]
            for dependency in self._registry.get(name).dependencies:
                upstream = effective.get(dependency, raw.get(dependency))
                if upstream is None:
                    continue
                state = _worse(state, _propagated(upstream))
            effective[name] = state
        reports = tuple(
            ComponentHealth(
                component=name,
                state=effective[name],
                detail=(
                    "degraded via dependency"
                    if effective[name] is not raw[name]
                    else "direct"
                ),
            )
            for name in sorted(effective)
        )
        for report in reports:
            self._monitor.report(f"module.{report.component}", report.state)
        return reports

    def overall(self, components: tuple[ComponentHealth, ...]) -> HealthState:
        """Platform verdict: the worst component state wins."""
        state = HealthState.HEALTHY
        for component in components:
            state = _worse(state, component.state)
        return state

    @staticmethod
    def heartbeat_ages(
        beats: list[HeartbeatRecord], *, now: Timestamp, stale_ms: int
    ) -> tuple[HeartbeatAge, ...]:
        """Heartbeat freshness per component (Book I 10.8)."""
        return tuple(
            HeartbeatAge(
                component=beat.component,
                age_ms=max(now.epoch_ms - beat.beat_at.epoch_ms, 0),
                stale=(now.epoch_ms - beat.beat_at.epoch_ms) > stale_ms,
            )
            for beat in beats
        )


def _propagated(upstream: HealthState) -> HealthState:
    """How an upstream state degrades a dependent (10.7)."""
    if upstream is HealthState.OFFLINE:
        return HealthState.CRITICAL
    if upstream is HealthState.CRITICAL:
        return HealthState.WARNING
    if upstream is HealthState.WARNING:
        return HealthState.WARNING
    return HealthState.HEALTHY

"""Health monitoring.

Book II 5.22: components report one of four health states - never a
raw boolean. The monitor aggregates component reports into a platform
verdict: the worst component state wins.
"""

from dataclasses import dataclass, field

from apex.core.enums import HealthState
from apex.core.exceptions import KernelError
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp


@dataclass(frozen=True, slots=True, kw_only=True)
class HealthReport:
    """One component's health at one instant (health contract)."""

    component: str
    state: HealthState
    checked_at: Timestamp
    details: dict[str, str | int | float | bool | None] = field(default_factory=dict)


class HealthMonitor:
    """Aggregates component health into a platform-level verdict."""

    def __init__(self, *, clock: Clock) -> None:
        self._clock = clock
        self._reports: dict[str, HealthReport] = {}

    def report(
        self,
        component: str,
        state: HealthState,
        **details: str | int | float | bool | None,
    ) -> HealthReport:
        """Record a component's current health."""
        if not component:
            raise KernelError("health component name must not be empty", code="KRN-020")
        entry = HealthReport(
            component=component,
            state=state,
            checked_at=self._clock.now(),
            details=dict(details),
        )
        self._reports[component] = entry
        return entry

    def component(self, name: str) -> HealthReport:
        """Latest report for one component."""
        if name not in self._reports:
            raise KernelError(
                "no health report for component",
                code="KRN-021",
                details={"component": name},
            )
        return self._reports[name]

    def overall(self) -> HealthState:
        """Platform verdict: worst reported state (OFFLINE when empty)."""
        if not self._reports:
            return HealthState.OFFLINE
        return max(
            (report.state for report in self._reports.values()),
            key=lambda state: state.severity,
        )

    def snapshot(self) -> tuple[HealthReport, ...]:
        """All current reports, ordered by component name."""
        return tuple(self._reports[name] for name in sorted(self._reports))

"""SLO error budget (Book II 26.28).

One sliding-window error budget over the platform's operations: the
error rate (``errors.total`` / ``operations.total``) against the
configured budget. The binding consequence when the budget is
consumed: the optimizer is not permitted to deploy - promotion
approvals consult :meth:`ErrorBudgetTracker.promotion_permitted`
before activating any artifact.
"""

from apex.core.time.clock import Clock
from apex.monitoring.collector import METRIC_ERRORS_TOTAL, METRIC_OPERATIONS_TOTAL
from apex.monitoring.config import MonitoringSettings
from apex.monitoring.records import SloStatus
from apex.monitoring.store import SqliteMonitoringRepository


class ErrorBudgetTracker:
    """Computes the platform error budget over the config window."""

    def __init__(
        self,
        *,
        settings: MonitoringSettings,
        store: SqliteMonitoringRepository,
        clock: Clock,
    ) -> None:
        self._settings = settings
        self._store = store
        self._clock = clock

    async def status(self) -> SloStatus:
        """The current error-budget verdict."""
        since = self._clock.now().epoch_ms - self._settings.slo_window_ms
        operations = await self._store.count_metric(
            METRIC_OPERATIONS_TOTAL, since_ms=since
        )
        errors = await self._store.count_metric(METRIC_ERRORS_TOTAL, since_ms=since)
        error_rate = errors / operations if operations > 0 else 0.0
        exhausted = (
            operations >= self._settings.slo_min_operations
            and error_rate > self._settings.slo_max_error_rate
        )
        return SloStatus(
            name="platform",
            window_ms=self._settings.slo_window_ms,
            operations=operations,
            errors=errors,
            error_rate=error_rate,
            budget=self._settings.slo_max_error_rate,
            exhausted=exhausted,
        )

    async def promotion_permitted(self) -> bool:
        """26.28: a consumed error budget blocks optimizer deploys."""
        return not (await self.status()).exhausted

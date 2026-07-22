"""Signal Optimizer engine (Book V part 5; Book II ch. 9).

A thin adapter over the shared ten-stage core (``staged.py``): the
evaluation core applies candidate overrides to the base
``DecisionParams``, folds the Central Decision Kernel over the stored
snapshots, simulates the fired signals to R outcomes and reduces them
to the multi-objective score. Candidate-level validation scores a
*fixed* winner on each out-of-sample window; per-fold re-optimization
belongs to the research platform's orchestrator (Book V part 7).

Acceptance (Book V): the winner must pass every validation stage and
show no out-of-sample collapse; otherwise the run is recorded as
rejected and no parameter artifact may be published.
"""

from collections.abc import Mapping, Sequence

from apex.contracts.engines import DecisionSnapshot
from apex.core.context import MarketContext
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.decision.kernel import CentralDecisionKernel, DecisionParams
from apex.optimization.metrics import SimulationMetrics, compute_metrics
from apex.optimization.objective import ObjectiveWeights, objective_score
from apex.optimization.parameters import OptimizableParameter
from apex.optimization.signal.space import SIGNAL_SEARCH_SPACE
from apex.optimization.simulator import SimulatedTrade, simulate_signals
from apex.optimization.staged import (
    OptimizationReport,
    StagedSearch,
    StageSettings,
    Trial,
    ValidationReport,
)

OPTIMIZER_VERSION = "signal-1.0.0"

# Compatibility aliases: the report shapes live in the shared core.
OptimizerSettings = StageSettings
SignalOptimizationReport = OptimizationReport
__all__ = [
    "OPTIMIZER_VERSION",
    "OptimizerSettings",
    "SignalOptimizationReport",
    "SignalOptimizer",
    "Trial",
    "ValidationReport",
]


class _SignalCore:
    """Evaluation core: kernel fold + signal simulation per candidate."""

    def __init__(
        self,
        *,
        snapshots: list[DecisionSnapshot],
        base_params: DecisionParams,
        context: MarketContext,
        clock: Clock,
        horizon_bars: int,
        weights: ObjectiveWeights,
    ) -> None:
        self._snapshots = snapshots
        self._base_params = base_params
        self._context = context
        self._clock = clock
        self._horizon = horizon_bars
        self._weights = weights

    @property
    def total(self) -> int:
        return len(self._snapshots)

    @property
    def window_bounds(self) -> tuple[int, int]:
        if not self._snapshots:
            return 0, 0
        return (
            self._snapshots[0].bar.open_time.epoch_ms,
            self._snapshots[-1].bar.open_time.epoch_ms,
        )

    def _simulate(
        self, overrides: Mapping[str, float], start: int, end: int
    ) -> list[SimulatedTrade]:
        params = self._base_params.with_overrides(overrides)
        kernel = CentralDecisionKernel(params=params, clock=self._clock)
        window = self._snapshots[start:end]
        outcomes = kernel.decide_series(window, self._context).unwrap()
        return simulate_signals(
            outcomes,
            [snapshot.bar for snapshot in window],
            base_risk_reward=params.base_risk_reward,
            fee_r=params.fee_slippage_r,
            horizon_bars=self._horizon,
        )

    def evaluate(
        self, overrides: Mapping[str, float], start: int, end: int
    ) -> tuple[float, SimulationMetrics]:
        metrics = compute_metrics(self._simulate(overrides, start, end))
        return objective_score(metrics, self._weights), metrics

    def r_series(self, overrides: Mapping[str, float]) -> list[float]:
        return [
            trade.r_multiple for trade in self._simulate(overrides, 0, self.total)
        ]


class SignalOptimizer:
    """Deterministic ten-stage search over the decision search space."""

    def __init__(
        self,
        *,
        snapshots: Sequence[DecisionSnapshot],
        base_params: DecisionParams,
        context: MarketContext,
        settings: StageSettings,
        weights: ObjectiveWeights,
        clock: Clock,
        space: tuple[OptimizableParameter, ...] = SIGNAL_SEARCH_SPACE,
    ) -> None:
        core = _SignalCore(
            snapshots=list(snapshots),
            base_params=base_params,
            context=context,
            clock=clock,
            horizon_bars=settings.horizon_bars,
            weights=weights,
        )
        self._search = StagedSearch(
            space=space,
            core=core,
            settings=settings,
            weights=weights,
            optimizer_version=OPTIMIZER_VERSION,
            symbol=context.symbol,
            timeframe=context.timeframe.value,
        )

    @property
    def optimizer_version(self) -> str:
        """Version tag stamped onto optimized outputs."""
        return OPTIMIZER_VERSION

    def optimize(self, *, seed: int) -> Result[Mapping[str, float]]:
        """Contract surface: the winning overrides (empty if rejected)."""
        detailed = self.optimize_detailed(seed=seed)
        if not detailed.ok:
            assert detailed.error is not None
            return Result.failure(detailed.error)
        report = detailed.unwrap()
        return Result.success(dict(report.best_overrides) if report.accepted else {})

    def optimize_detailed(self, *, seed: int) -> Result[OptimizationReport]:
        """Run all ten stages and produce the full report."""
        return self._search.run(seed=seed)

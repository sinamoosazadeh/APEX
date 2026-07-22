"""Risk Optimizer engine (Book V part 6; Book II ch. 10).

A thin adapter over the shared ten-stage core: the evaluation core
consumes the *fixed* decision stream (part 6: the risk optimizer never
touches probability, evidence or signal logic - its input is only the
final Decision) and re-manages the same fired signals under each
candidate risk plan - stop model, TP ladder with allocations,
breakeven/trailing and exposure shaping.
"""

from collections.abc import Mapping

from apex.core.result import Result
from apex.decision.kernel import DecisionOutcome
from apex.domain.market import Bar
from apex.features.calculations import wilder_atr
from apex.optimization.metrics import SimulationMetrics, compute_metrics
from apex.optimization.objective import ObjectiveWeights, objective_score
from apex.optimization.parameters import OptimizableParameter
from apex.optimization.risk.simulator import decode_plan, manage_trades
from apex.optimization.risk.space import RISK_SEARCH_SPACE
from apex.optimization.simulator import SimulatedTrade
from apex.optimization.staged import OptimizationReport, StagedSearch, StageSettings

OPTIMIZER_VERSION = "risk-1.0.0"
_ATR_LENGTH = 14


class _RiskCore:
    """Evaluation core: fixed decisions, candidate-managed outcomes."""

    def __init__(
        self,
        *,
        outcomes: tuple[DecisionOutcome, ...],
        bars: list[Bar],
        fee_r: float,
        horizon_bars: int,
        weights: ObjectiveWeights,
    ) -> None:
        self._outcomes = outcomes
        self._bars = bars
        self._atr = wilder_atr(bars, _ATR_LENGTH)
        self._fee_r = fee_r
        self._horizon = horizon_bars
        self._weights = weights
        self._open_ms = [bar.open_time.epoch_ms for bar in bars]

    @property
    def total(self) -> int:
        return len(self._bars)

    @property
    def window_bounds(self) -> tuple[int, int]:
        if not self._bars:
            return 0, 0
        return self._open_ms[0], self._open_ms[-1]

    def _simulate(
        self, overrides: Mapping[str, float], start: int, end: int
    ) -> list[SimulatedTrade]:
        plan = decode_plan(overrides)
        if start == 0 and end >= len(self._bars):
            window = self._outcomes
        else:
            low = self._open_ms[start]
            high = self._open_ms[end - 1] if end - 1 < len(self._open_ms) else self._open_ms[-1]
            window = tuple(
                outcome
                for outcome in self._outcomes
                if low <= outcome.bar_open_ms <= high
            )
        return manage_trades(
            window,
            self._bars,
            plan,
            atr=self._atr,
            fee_r=self._fee_r,
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


class RiskOptimizer:
    """Deterministic ten-stage search over the risk plan space."""

    def __init__(
        self,
        *,
        outcomes: tuple[DecisionOutcome, ...],
        bars: list[Bar],
        symbol: str,
        timeframe: str,
        fee_r: float,
        settings: StageSettings,
        weights: ObjectiveWeights,
        space: tuple[OptimizableParameter, ...] = RISK_SEARCH_SPACE,
    ) -> None:
        core = _RiskCore(
            outcomes=outcomes,
            bars=bars,
            fee_r=fee_r,
            horizon_bars=settings.horizon_bars,
            weights=weights,
        )
        self._search = StagedSearch(
            space=space,
            core=core,
            settings=settings,
            weights=weights,
            optimizer_version=OPTIMIZER_VERSION,
            symbol=symbol,
            timeframe=timeframe,
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

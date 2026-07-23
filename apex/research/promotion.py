"""Shadow-mode evaluation (Book II 14.24/22.19; Book V shadow deployment).

An accepted optimizer artifact never goes straight to production: it
registers as a SHADOW promotion and waits for genuinely unseen data -
bars that closed *after* registration. Once enough forward bars
accumulated, the candidate parameters and the incumbent (the active
artifact, or the config baseline when none is active) are folded over
the same forward window - decision-generation only, no order is ever
sent (14.24: "it produces a decision, but no trade is executed") -
and their simulated outcomes are compared. The candidate passes when
its objective score does not fall below the incumbent's beyond the
configured tolerance ("benchmark better than baseline" - the Book V
acceptance checklist).

Passing never auto-activates: Approval is its own pipeline stage
(19.28), owned by an operator through the CLI or the Telegram console.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from apex.contracts.engines import DecisionSnapshot
from apex.core.context import MarketContext
from apex.core.time.clock import Clock
from apex.decision.kernel import CentralDecisionKernel, DecisionParams
from apex.optimization.metrics import compute_metrics
from apex.optimization.objective import ObjectiveWeights, objective_score
from apex.optimization.simulator import simulate_signals


@dataclass(frozen=True, slots=True, kw_only=True)
class ShadowReport:
    """One shadow-window comparison of candidate vs incumbent."""

    bars: int
    candidate_signals: int
    candidate_net_r: float
    candidate_expectancy: float
    candidate_score: float
    baseline_signals: int
    baseline_net_r: float
    baseline_expectancy: float
    baseline_score: float
    tolerance: float
    passed: bool
    reason: str

    def to_json(self) -> str:
        """Serialized report for the promotion record."""
        return json.dumps(
            {
                "bars": self.bars,
                "candidate": {
                    "signals": self.candidate_signals,
                    "net_r": self.candidate_net_r,
                    "expectancy": self.candidate_expectancy,
                    "score": self.candidate_score,
                },
                "baseline": {
                    "signals": self.baseline_signals,
                    "net_r": self.baseline_net_r,
                    "expectancy": self.baseline_expectancy,
                    "score": self.baseline_score,
                },
                "tolerance": self.tolerance,
                "passed": self.passed,
                "reason": self.reason,
            },
            sort_keys=True,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _SideOutcome:
    """One side's simulated shadow outcome."""

    signals: int
    net_r: float
    expectancy: float
    score: float


def _fold_side(
    snapshots: Sequence[DecisionSnapshot],
    params: DecisionParams,
    context: MarketContext,
    clock: Clock,
    weights: ObjectiveWeights,
    horizon_bars: int,
) -> _SideOutcome:
    """Fold one parameter set over the shadow window (decisions only)."""
    kernel = CentralDecisionKernel(params=params, clock=clock)
    outcomes = kernel.decide_series(list(snapshots), context).unwrap()
    trades = simulate_signals(
        outcomes,
        [snapshot.bar for snapshot in snapshots],
        base_risk_reward=params.base_risk_reward,
        fee_r=params.fee_slippage_r,
        horizon_bars=horizon_bars,
    )
    metrics = compute_metrics(trades)
    return _SideOutcome(
        signals=len(trades),
        net_r=metrics.net_r,
        expectancy=metrics.expectancy,
        score=objective_score(metrics, weights),
    )


def evaluate_shadow(
    *,
    snapshots: Sequence[DecisionSnapshot],
    base_params: DecisionParams,
    candidate_overrides: Mapping[str, float],
    baseline_overrides: Mapping[str, float] | None,
    context: MarketContext,
    clock: Clock,
    weights: ObjectiveWeights,
    horizon_bars: int,
    min_bars: int,
    tolerance: float,
) -> ShadowReport:
    """Compare candidate vs incumbent over the forward shadow window."""
    if len(snapshots) < min_bars:
        return ShadowReport(
            bars=len(snapshots),
            candidate_signals=0,
            candidate_net_r=0.0,
            candidate_expectancy=0.0,
            candidate_score=0.0,
            baseline_signals=0,
            baseline_net_r=0.0,
            baseline_expectancy=0.0,
            baseline_score=0.0,
            tolerance=tolerance,
            passed=False,
            reason=f"insufficient forward bars ({len(snapshots)} < {min_bars})",
        )
    candidate = _fold_side(
        snapshots,
        base_params.with_overrides(candidate_overrides),
        context,
        clock,
        weights,
        horizon_bars,
    )
    baseline_params = (
        base_params.with_overrides(baseline_overrides)
        if baseline_overrides
        else base_params
    )
    baseline = _fold_side(
        snapshots, baseline_params, context, clock, weights, horizon_bars
    )
    passed = candidate.score >= baseline.score - tolerance
    reason = (
        "candidate score holds the incumbent's within tolerance"
        if passed
        else "candidate underperforms the incumbent beyond tolerance"
    )
    return ShadowReport(
        bars=len(snapshots),
        candidate_signals=candidate.signals,
        candidate_net_r=candidate.net_r,
        candidate_expectancy=candidate.expectancy,
        candidate_score=candidate.score,
        baseline_signals=baseline.signals,
        baseline_net_r=baseline.net_r,
        baseline_expectancy=baseline.expectancy,
        baseline_score=baseline.score,
        tolerance=tolerance,
        passed=passed,
        reason=reason,
    )

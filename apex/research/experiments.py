"""Experiment statistics (Book II 23.11-23.12; Book I 12.16).

The seeded statistical core behind the experiment registry: bootstrap
comparison of two R series (p-value for the candidate improving on
the baseline) with a standardized effect size, and the per-fold
walk-forward re-optimization that Phase 7 deferred here - each fold
re-runs the staged search on its train segment and is judged only on
its untouched test segment.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt

from apex.contracts.engines import DecisionSnapshot
from apex.core.context import MarketContext
from apex.core.time.clock import Clock
from apex.decision.kernel import CentralDecisionKernel, DecisionParams
from apex.optimization.objective import ObjectiveWeights
from apex.optimization.signal.engine import SignalOptimizer
from apex.optimization.simulator import simulate_signals
from apex.optimization.staged import StageSettings
from apex.optimization.validation import walk_forward_splits


@dataclass(frozen=True, slots=True, kw_only=True)
class ComparisonResult:
    """Bootstrap verdict on candidate-vs-baseline R series."""

    baseline_mean: float
    candidate_mean: float
    p_value: float
    effect_size: float


def bootstrap_comparison(
    baseline: Sequence[float],
    candidate: Sequence[float],
    *,
    resamples: int = 1_000,
    seed: int = 7,
) -> ComparisonResult:
    """Seeded bootstrap of the mean difference (23.11).

    ``p_value`` is the share of resampled differences at or below
    zero (small = the candidate's edge is unlikely to be luck);
    ``effect_size`` is the mean difference over the pooled standard
    deviation. Degenerate inputs return the honest neutral verdict.
    """
    if not baseline or not candidate:
        return ComparisonResult(
            baseline_mean=0.0, candidate_mean=0.0, p_value=1.0, effect_size=0.0
        )
    base_mean = sum(baseline) / len(baseline)
    cand_mean = sum(candidate) / len(candidate)
    pooled = [*baseline, *candidate]
    pooled_mean = sum(pooled) / len(pooled)
    variance = sum((v - pooled_mean) ** 2 for v in pooled) / len(pooled)
    pooled_std = sqrt(variance)
    effect = (cand_mean - base_mean) / pooled_std if pooled_std > 0 else 0.0
    rng = random.Random(seed)
    at_or_below = 0
    for _ in range(resamples):
        base_sample = [rng.choice(baseline) for _ in baseline]
        cand_sample = [rng.choice(candidate) for _ in candidate]
        difference = (
            sum(cand_sample) / len(cand_sample)
            - sum(base_sample) / len(base_sample)
        )
        if difference <= 0.0:
            at_or_below += 1
    return ComparisonResult(
        baseline_mean=base_mean,
        candidate_mean=cand_mean,
        p_value=at_or_below / resamples,
        effect_size=effect,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldReoptimization:
    """One walk-forward fold's re-optimized out-of-sample verdict."""

    fold: int
    accepted: bool
    trades: int
    total_r: float


@dataclass(frozen=True, slots=True, kw_only=True)
class WalkForwardReport:
    """Per-fold re-optimization outcome (the Phase 7 deferral)."""

    folds: tuple[FoldReoptimization, ...]
    accepted_folds: int
    total_r: float


def walk_forward_reoptimize(
    snapshots: Sequence[DecisionSnapshot],
    *,
    base_params: DecisionParams,
    context: MarketContext,
    clock: Clock,
    settings: StageSettings,
    weights: ObjectiveWeights,
    folds: int,
    seed: int,
) -> WalkForwardReport:
    """Re-optimize every fold on its train slice, judge on its test.

    Each fold runs the full staged search (Book V) over only its
    training snapshots with a fold-derived seed; the winner (or the
    base parameters when the fold rejects) folds the kernel over the
    train+test window and only test-window signals score - strictly
    out-of-sample, exactly the deferred part of the Phase 7 protocol.
    """
    window = list(snapshots)
    splits = walk_forward_splits(len(window), folds, settings.test_share)
    results: list[FoldReoptimization] = []
    total_r = 0.0
    for fold_index, split in enumerate(splits):
        train = window[split.train_start : split.train_end]
        optimizer = SignalOptimizer(
            snapshots=train,
            base_params=base_params,
            context=context,
            settings=settings,
            weights=weights,
            clock=clock,
        )
        best = optimizer.optimize(seed=seed + fold_index)
        overrides = best.unwrap() if best.ok else {}
        params = base_params.with_overrides(overrides) if overrides else base_params
        kernel = CentralDecisionKernel(params=params, clock=clock)
        segment = window[split.train_start : split.test_end]
        decided = kernel.decide_series(segment, context)
        if not decided.ok:
            results.append(
                FoldReoptimization(
                    fold=fold_index, accepted=False, trades=0, total_r=0.0
                )
            )
            continue
        bars = [snapshot.bar for snapshot in segment]
        test_low = window[split.test_start].bar.open_time.epoch_ms
        fired = tuple(
            outcome
            for outcome in decided.unwrap()
            if outcome.action == "signal" and outcome.bar_open_ms >= test_low
        )
        trades = simulate_signals(
            fired,
            bars,
            base_risk_reward=params.base_risk_reward,
            fee_r=params.fee_slippage_r,
            horizon_bars=settings.horizon_bars,
        )
        fold_r = sum(trade.r_multiple for trade in trades)
        results.append(
            FoldReoptimization(
                fold=fold_index,
                accepted=bool(overrides),
                trades=len(trades),
                total_r=fold_r,
            )
        )
        total_r += fold_r
    return WalkForwardReport(
        folds=tuple(results),
        accepted_folds=sum(1 for result in results if result.accepted),
        total_r=total_r,
    )

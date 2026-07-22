"""Signal Optimizer engine (Book V part 5; Book II ch. 9).

Runs the mandated ten-stage pipeline over the decision kernel's
published search space, entirely deterministic under one seed:

1.  Random exploration (seeded uniform grid samples)
2.  Latin hypercube sampling (seeded stratified samples)
3.  Bayesian optimization (Optuna TPE, seeded sampler)
4.  Local refinement (grid neighbors of the incumbent)
5.  Sensitivity analysis (per-parameter one-step perturbation)
6.  Stability analysis (score dispersion across the top candidates)
7.  Walk-forward validation (anchored folds, out-of-sample scoring)
8.  Rolling-window validation (fixed-width folds)
9.  Monte Carlo validation (seeded bootstrap of the R series)
10. Final ranking and acceptance

Every trial evaluates the same pure core: apply the candidate
overrides to the base ``DecisionParams``, fold the Central Decision
Kernel over the stored snapshots, simulate the fired signals to R
outcomes and reduce them to the multi-objective score. Candidate-level
validation scores a *fixed* winner on each out-of-sample window;
per-fold re-optimization belongs to the research platform's
orchestrator (Book V part 7).

Acceptance (Book V): the winner must pass every validation stage and
show no out-of-sample collapse; otherwise the run is recorded as
rejected and no parameter artifact may be published.
"""

import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import optuna

from apex.contracts.engines import DecisionSnapshot
from apex.core.context import MarketContext
from apex.core.exceptions import ApexError
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.validation import ensure_in_range, ensure_positive
from apex.decision.kernel import CentralDecisionKernel, DecisionParams
from apex.optimization.metrics import SimulationMetrics, compute_metrics
from apex.optimization.objective import ObjectiveWeights, objective_score
from apex.optimization.parameters import (
    OptimizableParameter,
    neighbors,
    sample_latin_hypercube,
    sample_random,
)
from apex.optimization.signal.space import SIGNAL_SEARCH_SPACE
from apex.optimization.simulator import simulate_signals
from apex.optimization.validation import (
    Split,
    expanding_splits,
    monte_carlo_positive_share,
    rolling_splits,
    walk_forward_splits,
)

OPTIMIZER_VERSION = "signal-1.0.0"


@dataclass(frozen=True, slots=True, kw_only=True)
class OptimizerSettings:
    """Stage sizes and validation thresholds (Book V defaults)."""

    random_trials: int = 24
    latin_trials: int = 16
    bayesian_trials: int = 32
    refinement_rounds: int = 2
    validation_folds: int = 4
    test_share: float = 0.2
    monte_carlo_resamples: int = 200
    monte_carlo_minimum: float = 0.55
    validation_minimum_score: float = 0.0
    degradation_maximum: float = 0.60
    stability_minimum: float = 0.40
    horizon_bars: int = 96
    top_candidates: int = 5

    def __post_init__(self) -> None:
        ensure_positive(self.random_trials, "random_trials")
        ensure_positive(self.latin_trials, "latin_trials")
        ensure_positive(self.bayesian_trials, "bayesian_trials")
        ensure_positive(self.refinement_rounds, "refinement_rounds")
        ensure_positive(self.validation_folds, "validation_folds")
        ensure_in_range(self.test_share, 0.05, 0.5, "test_share")
        ensure_positive(self.monte_carlo_resamples, "monte_carlo_resamples")
        ensure_in_range(self.monte_carlo_minimum, 0.0, 1.0, "monte_carlo_minimum")
        ensure_in_range(self.degradation_maximum, 0.0, 1.0, "degradation_maximum")
        ensure_in_range(self.stability_minimum, 0.0, 1.0, "stability_minimum")
        ensure_positive(self.horizon_bars, "horizon_bars")
        ensure_positive(self.top_candidates, "top_candidates")


@dataclass(frozen=True, slots=True, kw_only=True)
class Trial:
    """One evaluated candidate."""

    overrides: Mapping[str, float]
    score: float
    metrics: SimulationMetrics
    stage: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationReport:
    """Out-of-sample scores for one split family."""

    name: str
    fold_scores: tuple[float, ...]
    mean_score: float
    passed: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SignalOptimizationReport:
    """The Book V output record for one optimization run."""

    symbol: str
    timeframe: str
    optimizer_version: str
    seed: int
    trials: int
    best_overrides: Mapping[str, float]
    best_score: float
    best_metrics: SimulationMetrics
    walk_forward: ValidationReport
    rolling: ValidationReport
    expanding: ValidationReport
    monte_carlo_share: float
    monte_carlo_passed: bool
    sensitivity: tuple[tuple[str, float], ...]
    stability_score: float
    stability_passed: bool
    degradation: float
    overfit_passed: bool
    confidence: float
    accepted: bool
    bars_evaluated: int
    window_start_ms: int
    window_end_ms: int


class SignalOptimizer:
    """Deterministic ten-stage search over the decision search space."""

    def __init__(
        self,
        *,
        snapshots: Sequence[DecisionSnapshot],
        base_params: DecisionParams,
        context: MarketContext,
        settings: OptimizerSettings,
        weights: ObjectiveWeights,
        clock: Clock,
        space: tuple[OptimizableParameter, ...] = SIGNAL_SEARCH_SPACE,
    ) -> None:
        self._snapshots = list(snapshots)
        self._base_params = base_params
        self._context = context
        self._settings = settings
        self._weights = weights
        self._clock = clock
        self._space = space

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

    def optimize_detailed(self, *, seed: int) -> Result[SignalOptimizationReport]:
        """Run all ten stages and produce the full report."""
        try:
            report = self._run(seed)
        except ApexError as error:
            return Result.failure(error)
        return Result.success(report)

    # --- Evaluation core -------------------------------------------------------

    def _evaluate(
        self, overrides: Mapping[str, float], start: int, end: int
    ) -> tuple[float, SimulationMetrics]:
        params = self._base_params.with_overrides(overrides)
        kernel = CentralDecisionKernel(params=params, clock=self._clock)
        window = self._snapshots[start:end]
        outcomes = kernel.decide_series(window, self._context).unwrap()
        trades = simulate_signals(
            outcomes,
            [snapshot.bar for snapshot in window],
            base_risk_reward=params.base_risk_reward,
            fee_r=params.fee_slippage_r,
            horizon_bars=self._settings.horizon_bars,
        )
        metrics = compute_metrics(trades)
        return objective_score(metrics, self._weights), metrics

    def _full(self, overrides: Mapping[str, float]) -> tuple[float, SimulationMetrics]:
        return self._evaluate(overrides, 0, len(self._snapshots))

    # --- Stages ------------------------------------------------------------------

    def _run(self, seed: int) -> SignalOptimizationReport:
        settings = self._settings
        trials: list[Trial] = []
        rng = random.Random(seed)
        # Stage 1: random exploration.
        for _ in range(settings.random_trials):
            overrides = sample_random(self._space, rng)
            trials.append(self._trial(overrides, "random"))
        # Stage 2: Latin hypercube sampling.
        for overrides in sample_latin_hypercube(
            self._space, settings.latin_trials, rng
        ):
            trials.append(self._trial(overrides, "latin"))
        # Stage 3: Bayesian optimization (Optuna TPE, seeded).
        trials.extend(self._bayesian(seed))
        # Stage 4: local refinement around the incumbent.
        for _ in range(settings.refinement_rounds):
            incumbent = max(trials, key=lambda trial: trial.score)
            for overrides in neighbors(self._space, dict(incumbent.overrides)):
                trials.append(self._trial(overrides, "refine"))
        best = max(trials, key=lambda trial: trial.score)
        # Stage 5: sensitivity analysis.
        sensitivity = self._sensitivity(best)
        # Stage 6: stability analysis.
        stability = self._stability(trials)
        # Stages 7-8: walk-forward and rolling validation (+ expanding
        # per the Book V validation protocol).
        walk = self._validate("walk_forward", walk_forward_splits, best)
        roll = self._validate("rolling", rolling_splits, best)
        expand = self._validate("expanding", expanding_splits, best)
        # Stage 9: Monte Carlo resampling of the winner's R series.
        monte_share = self._monte_carlo(best, seed)
        # Stage 10: final ranking and acceptance.
        return self._rank(
            seed, trials, best, sensitivity, stability, walk, roll, expand, monte_share
        )

    def _trial(self, overrides: Mapping[str, float], stage: str) -> Trial:
        score, metrics = self._full(overrides)
        return Trial(overrides=dict(overrides), score=score, metrics=metrics, stage=stage)

    def _bayesian(self, seed: int) -> list[Trial]:
        settings = self._settings
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        sampler = optuna.samplers.TPESampler(seed=seed)
        study = optuna.create_study(direction="maximize", sampler=sampler)
        collected: list[Trial] = []

        def suggest(optuna_trial: optuna.Trial) -> float:
            overrides: dict[str, float] = {}
            for parameter in self._space:
                if parameter.integer:
                    overrides[parameter.name] = float(
                        optuna_trial.suggest_int(
                            parameter.name,
                            int(parameter.minimum),
                            int(parameter.maximum),
                            step=max(int(parameter.step), 1),
                        )
                    )
                else:
                    overrides[parameter.name] = optuna_trial.suggest_float(
                        parameter.name,
                        parameter.minimum,
                        parameter.maximum,
                        step=parameter.step,
                    )
            quantized = {
                parameter.name: parameter.quantize(overrides[parameter.name])
                for parameter in self._space
            }
            trial = self._trial(quantized, "bayesian")
            collected.append(trial)
            return trial.score

        study.optimize(suggest, n_trials=settings.bayesian_trials)
        return collected

    def _sensitivity(self, best: Trial) -> tuple[tuple[str, float], ...]:
        """Per-parameter score impact of a one-step perturbation."""
        impacts: list[tuple[str, float]] = []
        for parameter in self._space:
            deltas: list[float] = []
            for direction in (-1, 1):
                candidate = dict(best.overrides)
                candidate[parameter.name] = parameter.quantize(
                    candidate[parameter.name] + direction * parameter.step
                )
                score, _ = self._full(candidate)
                deltas.append(abs(score - best.score))
            impacts.append((parameter.name, max(deltas)))
        impacts.sort(key=lambda item: item[1], reverse=True)
        return tuple(impacts)

    def _stability(self, trials: list[Trial]) -> float:
        """1 minus the normalized score dispersion of the top candidates."""
        top = sorted(trials, key=lambda trial: trial.score, reverse=True)
        chosen = [trial.score for trial in top[: self._settings.top_candidates]]
        if len(chosen) < 2:
            return 1.0
        mean = sum(chosen) / len(chosen)
        variance = sum((score - mean) ** 2 for score in chosen) / len(chosen)
        deviation: float = variance**0.5
        scale = max(abs(top[0].score), 1e-6)
        return max(0.0, 1.0 - deviation / scale)

    def _validate(
        self,
        name: str,
        splitter: Callable[[int, int, float], list[Split]],
        best: Trial,
    ) -> ValidationReport:
        settings = self._settings
        splits = splitter(
            len(self._snapshots), settings.validation_folds, settings.test_share
        )
        scores = tuple(
            self._evaluate(best.overrides, split.test_start, split.test_end)[0]
            for split in splits
        )
        mean = sum(scores) / len(scores)
        return ValidationReport(
            name=name,
            fold_scores=scores,
            mean_score=mean,
            passed=mean >= settings.validation_minimum_score,
        )

    def _monte_carlo(self, best: Trial, seed: int) -> float:
        params = self._base_params.with_overrides(best.overrides)
        kernel = CentralDecisionKernel(params=params, clock=self._clock)
        outcomes = kernel.decide_series(self._snapshots, self._context).unwrap()
        trades = simulate_signals(
            outcomes,
            [snapshot.bar for snapshot in self._snapshots],
            base_risk_reward=params.base_risk_reward,
            fee_r=params.fee_slippage_r,
            horizon_bars=self._settings.horizon_bars,
        )
        return monte_carlo_positive_share(
            [trade.r_multiple for trade in trades],
            resamples=self._settings.monte_carlo_resamples,
            seed=seed,
        )

    def _rank(
        self,
        seed: int,
        trials: list[Trial],
        best: Trial,
        sensitivity: tuple[tuple[str, float], ...],
        stability: float,
        walk: ValidationReport,
        roll: ValidationReport,
        expand: ValidationReport,
        monte_share: float,
    ) -> SignalOptimizationReport:
        settings = self._settings
        out_of_sample = (walk.mean_score + roll.mean_score + expand.mean_score) / 3.0
        degradation = (
            (best.score - out_of_sample) / abs(best.score) if best.score != 0 else 1.0
        )
        overfit_passed = degradation <= settings.degradation_maximum
        stability_passed = stability >= settings.stability_minimum
        monte_passed = monte_share >= settings.monte_carlo_minimum
        checks = (
            walk.passed, roll.passed, expand.passed,
            monte_passed, stability_passed, overfit_passed,
            best.metrics.trade_count >= self._weights.minimum_trades,
        )
        confidence = sum(1.0 for check in checks if check) / len(checks)
        first = self._snapshots[0].bar.open_time.epoch_ms if self._snapshots else 0
        last = self._snapshots[-1].bar.open_time.epoch_ms if self._snapshots else 0
        return SignalOptimizationReport(
            symbol=self._context.symbol,
            timeframe=self._context.timeframe.value,
            optimizer_version=OPTIMIZER_VERSION,
            seed=seed,
            trials=len(trials),
            best_overrides=dict(best.overrides),
            best_score=best.score,
            best_metrics=best.metrics,
            walk_forward=walk,
            rolling=roll,
            expanding=expand,
            monte_carlo_share=monte_share,
            monte_carlo_passed=monte_passed,
            sensitivity=sensitivity,
            stability_score=stability,
            stability_passed=stability_passed,
            degradation=degradation,
            overfit_passed=overfit_passed,
            confidence=confidence,
            accepted=all(checks),
            bars_evaluated=len(self._snapshots),
            window_start_ms=first,
            window_end_ms=last,
        )

"""The Book V ten-stage search core, shared across optimizers.

Both the Signal Optimizer (part 5) and the Risk Optimizer (part 6) run
the same mandated pipeline - random exploration, Latin hypercube,
Bayesian TPE, local refinement, sensitivity, stability, walk-forward,
rolling (+ expanding) and Monte Carlo validation, final ranking - over
different evaluation cores. The core is a pure object exposing a
window length, deterministic per-window scoring and the winner's R
series; one seed fully determines every trial.
"""

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

import optuna

from apex.core.exceptions import ApexError
from apex.core.result import Result
from apex.core.validation import ensure_in_range, ensure_positive
from apex.optimization.metrics import SimulationMetrics
from apex.optimization.objective import ObjectiveWeights
from apex.optimization.parameters import (
    OptimizableParameter,
    neighbors,
    sample_latin_hypercube,
    sample_random,
)
from apex.optimization.validation import (
    Split,
    expanding_splits,
    monte_carlo_positive_share,
    rolling_splits,
    walk_forward_splits,
)


class EvaluationCore(Protocol):
    """What an optimizer must provide to the staged pipeline."""

    @property
    def total(self) -> int:
        """Number of evaluation units (bars) in the window."""
        ...

    @property
    def window_bounds(self) -> tuple[int, int]:
        """(first, last) bar open epoch-ms of the window."""
        ...

    def evaluate(
        self, overrides: Mapping[str, float], start: int, end: int
    ) -> tuple[float, SimulationMetrics]:
        """Deterministic (score, metrics) for one candidate and range."""
        ...

    def r_series(self, overrides: Mapping[str, float]) -> list[float]:
        """The candidate's full-window simulated R series."""
        ...


@dataclass(frozen=True, slots=True, kw_only=True)
class StageSettings:
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
class OptimizationReport:
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


class StagedSearch:
    """Runs the ten stages over an evaluation core, seeded end to end."""

    def __init__(
        self,
        *,
        space: tuple[OptimizableParameter, ...],
        core: EvaluationCore,
        settings: StageSettings,
        weights: ObjectiveWeights,
        optimizer_version: str,
        symbol: str,
        timeframe: str,
    ) -> None:
        self._space = space
        self._core = core
        self._settings = settings
        self._weights = weights
        self._version = optimizer_version
        self._symbol = symbol
        self._timeframe = timeframe

    def run(self, *, seed: int) -> Result[OptimizationReport]:
        """All ten stages; the full Book V report."""
        try:
            report = self._run(seed)
        except ApexError as error:
            return Result.failure(error)
        return Result.success(report)

    # --- Stages ------------------------------------------------------------------

    def _run(self, seed: int) -> OptimizationReport:
        settings = self._settings
        trials: list[Trial] = []
        rng = random.Random(seed)
        for _ in range(settings.random_trials):  # Stage 1
            trials.append(self._trial(sample_random(self._space, rng), "random"))
        for overrides in sample_latin_hypercube(  # Stage 2
            self._space, settings.latin_trials, rng
        ):
            trials.append(self._trial(overrides, "latin"))
        trials.extend(self._bayesian(seed))  # Stage 3
        for _ in range(settings.refinement_rounds):  # Stage 4
            incumbent = max(trials, key=lambda trial: trial.score)
            for overrides in neighbors(self._space, dict(incumbent.overrides)):
                trials.append(self._trial(overrides, "refine"))
        best = max(trials, key=lambda trial: trial.score)
        sensitivity = self._sensitivity(best)  # Stage 5
        stability = self._stability(trials)  # Stage 6
        walk = self._validate("walk_forward", walk_forward_splits, best)  # Stage 7
        roll = self._validate("rolling", rolling_splits, best)  # Stage 8
        expand = self._validate("expanding", expanding_splits, best)
        monte_share = monte_carlo_positive_share(  # Stage 9
            self._core.r_series(best.overrides),
            resamples=settings.monte_carlo_resamples,
            seed=seed,
        )
        return self._rank(  # Stage 10
            seed, trials, best, sensitivity, stability, walk, roll, expand, monte_share
        )

    def _trial(self, overrides: Mapping[str, float], stage: str) -> Trial:
        score, metrics = self._core.evaluate(overrides, 0, self._core.total)
        return Trial(
            overrides=dict(overrides), score=score, metrics=metrics, stage=stage
        )

    def _bayesian(self, seed: int) -> list[Trial]:
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

        study.optimize(suggest, n_trials=self._settings.bayesian_trials)
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
                score, _ = self._core.evaluate(candidate, 0, self._core.total)
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
            self._core.total, settings.validation_folds, settings.test_share
        )
        scores = tuple(
            self._core.evaluate(best.overrides, split.test_start, split.test_end)[0]
            for split in splits
        )
        mean = sum(scores) / len(scores)
        return ValidationReport(
            name=name,
            fold_scores=scores,
            mean_score=mean,
            passed=mean >= settings.validation_minimum_score,
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
    ) -> OptimizationReport:
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
        first, last = self._core.window_bounds
        return OptimizationReport(
            symbol=self._symbol,
            timeframe=self._timeframe,
            optimizer_version=self._version,
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
            bars_evaluated=self._core.total,
            window_start_ms=first,
            window_end_ms=last,
        )

"""Signal optimizer: sampling, simulation, metrics, stages, artifacts."""

import asyncio
import json
import random
from pathlib import Path

import pytest
from apex.contracts.engines import DecisionSnapshot, IOptimizer
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.decision.kernel import (
    TIMING_IMMEDIATE,
    DecisionOutcome,
    DecisionParams,
)
from apex.domain.market import Bar
from apex.optimization.metrics import compute_metrics
from apex.optimization.objective import ObjectiveWeights, objective_score
from apex.optimization.parameters import (
    OptimizableParameter,
    neighbors,
    sample_latin_hypercube,
    sample_random,
)
from apex.optimization.signal.engine import (
    OptimizerSettings,
    SignalOptimizer,
)
from apex.optimization.signal.store import SignalOptimizationStore, artifact_document
from apex.optimization.simulator import SimulatedTrade, simulate_signals
from apex.optimization.validation import (
    monte_carlo_positive_share,
    rolling_splits,
    walk_forward_splits,
)

from tests.conftest import T0
from tests.unit.decision.test_decision import (
    bullish_vector,
    make_bar,
    strong_channels,
)

H1_MS = Timeframe.H1.duration_ms

SPACE = (
    OptimizableParameter(name="probability_threshold", minimum=0.5, maximum=0.9, step=0.05),
    OptimizableParameter(name="cooldown_bars", minimum=0, maximum=8, step=2, integer=True),
)


class TestParameterSpace:
    def test_quantize_snaps_and_clamps(self) -> None:
        parameter = SPACE[0]
        assert parameter.quantize(0.63) == 0.65
        assert parameter.quantize(0.2) == 0.5
        assert parameter.quantize(1.7) == 0.9

    def test_sampling_is_deterministic(self) -> None:
        first = sample_random(SPACE, random.Random(9))
        second = sample_random(SPACE, random.Random(9))
        assert first == second

    def test_latin_hypercube_stratifies(self) -> None:
        points = sample_latin_hypercube(SPACE, 4, random.Random(3))
        assert len(points) == 4
        thresholds = {point["probability_threshold"] for point in points}
        assert len(thresholds) >= 3  # stratified, not collapsed

    def test_neighbors_step_one_dimension_at_a_time(self) -> None:
        center = {"probability_threshold": 0.7, "cooldown_bars": 4.0}
        moved = neighbors(SPACE, center)
        assert {tuple(sorted(point.items())) for point in moved} == {
            (("cooldown_bars", 4.0), ("probability_threshold", 0.65)),
            (("cooldown_bars", 4.0), ("probability_threshold", 0.75)),
            (("cooldown_bars", 2.0), ("probability_threshold", 0.7)),
            (("cooldown_bars", 6.0), ("probability_threshold", 0.7)),
        }


def signal_outcome(index: int, bars: list[Bar]) -> DecisionOutcome:
    """A synthetic fired long at bar ``index`` with entry/stop/targets."""
    from apex.decision.kernel import CentralDecisionKernel

    params = DecisionParams(
        execution_timing=TIMING_IMMEDIATE,
        atr_length=3,
        ema_length=3,
        rvol_gate_enabled=False,
        similarity_cooldown_enabled=False,
        cooldown_bars=1,
        # Simulator tests exercise trade management, not the kernel's
        # virtual ledger; the flatness gate is covered in the decision
        # suite.
        flatness_gate_enabled=False,
    )
    kernel = CentralDecisionKernel(params=params, clock=ManualClock(T0))
    snapshots = [
        DecisionSnapshot(
            bar=bar,
            vector=bullish_vector(),
            probability_long=0.85,
            probability_short=0.05,
            channels=strong_channels(),
            macro_high=float(bar.close.value) + 50.0,
            macro_low=float(bar.close.value) - 50.0,
        )
        for bar in bars[: index + 1]
    ]
    context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
    outcomes = kernel.decide_series(snapshots, context).unwrap()
    outcome = outcomes[index]
    assert outcome.action == "signal"
    return outcome


class TestSimulator:
    def rising(self, count: int) -> list[Bar]:
        bars = []
        for i in range(count):
            base = 100.0 + i
            bars.append(make_bar(i, base, base + 2.2, base - 0.4, base + 2.0))
        return bars

    def test_target_hit_pays_base_rr(self) -> None:
        bars = self.rising(40)
        outcome = signal_outcome(3, bars)
        trades = simulate_signals(
            (outcome,), bars, base_risk_reward=1.75, fee_r=0.02, horizon_bars=30
        )
        assert len(trades) == 1
        assert trades[0].exit_reason == "target"
        assert trades[0].r_multiple == pytest.approx(1.75 - 0.02)

    def test_stop_hit_costs_one_r(self) -> None:
        bars = self.rising(6)
        outcome = signal_outcome(3, bars)
        # Crash bar below any stop right after entry.
        crash_base = 40.0
        bars.append(make_bar(6, crash_base + 60, crash_base + 60, crash_base, crash_base))
        trades = simulate_signals(
            (outcome,), bars, base_risk_reward=1.75, fee_r=0.02, horizon_bars=30
        )
        assert trades[0].exit_reason == "stop"
        assert trades[0].r_multiple == pytest.approx(-1.02)


class TestMetricsAndObjective:
    def trade(self, r: float) -> SimulatedTrade:
        return SimulatedTrade(
            bar_open_ms=0, direction="long", setup="t", r_multiple=r,
            bars_held=1, exit_reason="target",
        )

    def test_known_series(self) -> None:
        metrics = compute_metrics([self.trade(r) for r in (1.0, -1.0, 2.0, 1.0)])
        assert metrics.trade_count == 4
        assert metrics.expectancy == pytest.approx(0.75)
        assert metrics.net_r == pytest.approx(3.0)
        assert metrics.win_rate == pytest.approx(0.75)
        assert metrics.profit_factor == pytest.approx(4.0)
        assert metrics.max_drawdown == pytest.approx(1.0)
        assert metrics.losing_streak == 1

    def test_objective_prefers_the_better_series(self) -> None:
        weights = ObjectiveWeights()
        good = compute_metrics([self.trade(r) for r in (1.0, 1.5, -1.0, 2.0, 1.0)])
        bad = compute_metrics([self.trade(r) for r in (-1.0, -1.0, 1.0, -1.0, -1.0)])
        assert objective_score(good, weights) > objective_score(bad, weights)

    def test_empty_series_is_penalized(self) -> None:
        weights = ObjectiveWeights()
        assert objective_score(compute_metrics([]), weights) < 0


class TestValidationSplits:
    def test_walk_forward_marches_and_stays_in_bounds(self) -> None:
        splits = walk_forward_splits(100, 4, 0.2)
        assert len(splits) == 4
        for split in splits:
            assert 0 <= split.train_start < split.train_end
            assert split.train_end == split.test_start
            assert split.test_start < split.test_end <= 100

    def test_rolling_windows_move_the_train(self) -> None:
        splits = rolling_splits(100, 3, 0.2)
        starts = [split.train_start for split in splits]
        assert starts == sorted(starts)
        assert starts[-1] > starts[0]

    def test_monte_carlo_is_seeded(self) -> None:
        series = [1.0, -1.0, 2.0, 0.5, -0.5]
        first = monte_carlo_positive_share(series, resamples=50, seed=11)
        second = monte_carlo_positive_share(series, resamples=50, seed=11)
        assert first == second
        assert 0.0 <= first <= 1.0


def optimizer_snapshots(count: int) -> list[DecisionSnapshot]:
    snapshots = []
    for i in range(count):
        base = 100.0 + i
        bar = make_bar(i, base, base + 2.2, base - 0.4, base + 2.0)
        snapshots.append(
            DecisionSnapshot(
                bar=bar,
                vector=bullish_vector(),
                probability_long=0.85,
                probability_short=0.05,
                channels=strong_channels(),
                macro_high=base + 50.0,
                macro_low=base - 50.0,
            )
        )
    return snapshots


TINY = OptimizerSettings(
    random_trials=4,
    latin_trials=4,
    bayesian_trials=4,
    refinement_rounds=1,
    validation_folds=2,
    test_share=0.25,
    monte_carlo_resamples=40,
    horizon_bars=20,
)


def build_optimizer(count: int = 48) -> SignalOptimizer:
    return SignalOptimizer(
        snapshots=optimizer_snapshots(count),
        base_params=DecisionParams(
            execution_timing=TIMING_IMMEDIATE,
            atr_length=3,
            ema_length=3,
            rvol_gate_enabled=False,
            similarity_cooldown_enabled=False,
        ),
        context=MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0),
        settings=TINY,
        weights=ObjectiveWeights(minimum_trades=2),
        clock=ManualClock(T0),
        space=SPACE,
    )


class TestSignalOptimizer:
    def test_full_pipeline_is_deterministic(self) -> None:
        first = build_optimizer().optimize_detailed(seed=13).unwrap()
        second = build_optimizer().optimize_detailed(seed=13).unwrap()
        assert first.best_overrides == second.best_overrides
        assert first.best_score == second.best_score
        assert first.monte_carlo_share == second.monte_carlo_share
        assert first.trials == second.trials

    def test_report_carries_the_book_v_record(self) -> None:
        report = build_optimizer().optimize_detailed(seed=13).unwrap()
        assert report.symbol == "BTCUSDT"
        assert report.trials >= 12
        assert len(report.sensitivity) == len(SPACE)
        assert len(report.walk_forward.fold_scores) == TINY.validation_folds
        assert 0.0 <= report.confidence <= 1.0
        assert report.bars_evaluated == 48

    def test_contract_surface(self) -> None:
        optimizer = build_optimizer()
        assert isinstance(optimizer, IOptimizer)
        winner = optimizer.optimize(seed=13).unwrap()
        report = build_optimizer().optimize_detailed(seed=13).unwrap()
        assert (winner == dict(report.best_overrides)) is report.accepted or winner == {}


class TestArtifactStore:
    def test_record_publish_and_hash(self, tmp_path: Path) -> None:
        asyncio.run(self._roundtrip(tmp_path))

    async def _roundtrip(self, tmp_path: Path) -> None:
        report = build_optimizer().optimize_detailed(seed=13).unwrap()
        store = SignalOptimizationStore(
            database_path=tmp_path / "optimization.sqlite",
            artifact_dir=tmp_path / "artifacts",
        )
        await store.open()
        try:
            await store.record_run(report, created_at=T0)
            latest = await store.latest("BTCUSDT", "1h")
            assert latest is not None and latest["seed"] == 13
            if report.accepted:
                path = await store.publish_artifact(
                    report, created_at=T0, apex_version="0.9.0"
                )
                document = json.loads(Path(path).read_text())
                assert document["sha256"]
                assert document["optimized_parameters"] == dict(report.best_overrides)
                assert path.name == "BTCUSDT_1h_signal.json"
        finally:
            await store.close()

    def test_artifact_hash_is_stable(self) -> None:
        report = build_optimizer().optimize_detailed(seed=13).unwrap()
        first = artifact_document(report, created_at=T0, apex_version="0.9.0")
        second = artifact_document(report, created_at=T0, apex_version="0.9.0")
        assert first["sha256"] == second["sha256"]

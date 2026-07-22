"""Risk optimizer: plan decoding, managed trades, sizing, engine."""

import pytest
from apex.contracts.engines import IOptimizer
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.decision.kernel import TIMING_IMMEDIATE, DecisionParams
from apex.domain.market import Bar
from apex.features.calculations import wilder_atr
from apex.optimization.objective import ObjectiveWeights
from apex.optimization.risk.engine import RiskOptimizer
from apex.optimization.risk.simulator import (
    SizingContext,
    decode_plan,
    manage_trades,
    position_size,
)
from apex.optimization.risk.space import (
    RISK_SEARCH_SPACE,
    SIZING_BUDGET,
    SIZING_CONFIDENCE,
    SIZING_DRAWDOWN,
    SIZING_FIXED,
    SIZING_KELLY,
    SIZING_PROBABILITY,
    STOP_MODEL_SIGNAL,
)
from apex.optimization.simulator import SimulatedTrade
from apex.optimization.staged import StageSettings
from apex.portfolio.account import TradeStatistics

from tests.conftest import T0
from tests.unit.decision.test_decision import make_bar
from tests.unit.optimization.test_optimization import (
    optimizer_snapshots,
    signal_outcome,
)

H1_MS = Timeframe.H1.duration_ms

BASE_OVERRIDES: dict[str, float] = {
    "stop_model": float(STOP_MODEL_SIGNAL),
    "stop_atr_multiple": 2.0,
    "tp1_r": 0.5,
    "tp2_step_r": 0.5,
    "tp3_step_r": 1.0,
    "tp1_allocation": 0.3,
    "tp2_allocation": 0.3,
    "breakeven_trigger_r": 0.5,
    "trailing_enabled": 0.0,
    "trailing_distance_r": 1.0,
    "sizing_model": float(SIZING_FIXED),
    "risk_fraction": 1.0,
}


def rising(count: int) -> list[Bar]:
    bars: list[Bar] = []
    for i in range(count):
        base = 100.0 + i
        bars.append(make_bar(i, base, base + 2.2, base - 0.4, base + 2.0))
    return bars


class TestPlanDecoding:
    def test_ladder_is_monotonic_by_construction(self) -> None:
        plan = decode_plan(BASE_OVERRIDES)
        assert plan.tp1_r < plan.tp2_r < plan.tp3_r
        assert plan.tp2_r == pytest.approx(1.0)
        assert plan.tp3_r == pytest.approx(2.0)

    def test_tp3_gets_the_remainder(self) -> None:
        plan = decode_plan(BASE_OVERRIDES)
        assert plan.tp3_allocation == pytest.approx(0.4)

    def test_sizing_models(self) -> None:
        bars = rising(8)
        outcome = signal_outcome(3, bars)
        fixed = decode_plan({**BASE_OVERRIDES, "sizing_model": float(SIZING_FIXED)})
        prob = decode_plan({**BASE_OVERRIDES, "sizing_model": float(SIZING_PROBABILITY)})
        conf = decode_plan({**BASE_OVERRIDES, "sizing_model": float(SIZING_CONFIDENCE)})
        assert position_size(fixed, outcome) == pytest.approx(1.0)
        # p = 0.85 -> clamp(1.7) = 1.5 exposure boost.
        assert position_size(prob, outcome) == pytest.approx(1.5)
        assert position_size(conf, outcome) <= position_size(prob, outcome)

    def context(
        self,
        *,
        trades: int = 20,
        wins: int = 12,
        average_win_r: float = 2.0,
        average_loss_r: float = -1.0,
        drawdown_r: float = 0.0,
        day_loss_r: float = 0.0,
    ) -> SizingContext:
        losses = trades - wins
        return SizingContext(
            statistics=TradeStatistics(
                trades=trades, wins=wins, losses=losses,
                r_sum=wins * average_win_r + losses * average_loss_r,
                average_win_r=average_win_r, average_loss_r=average_loss_r,
                consecutive_losses=0,
            ),
            drawdown_r=drawdown_r,
            day_loss_r=day_loss_r,
        )

    def test_history_models_fall_back_without_context(self) -> None:
        outcome = signal_outcome(3, rising(8))
        for model in (SIZING_KELLY, SIZING_DRAWDOWN, SIZING_BUDGET):
            plan = decode_plan({**BASE_OVERRIDES, "sizing_model": float(model)})
            assert position_size(plan, outcome) == pytest.approx(1.0)

    def test_kelly_scales_with_the_edge(self) -> None:
        outcome = signal_outcome(3, rising(8))
        plan = decode_plan({**BASE_OVERRIDES, "sizing_model": float(SIZING_KELLY)})
        # Strong edge: p=0.6, payoff 2 -> kelly 0.2 vs neutral 0.125 -> 1.6x
        # clamped to the 1.5 ceiling.
        strong = self.context()
        assert position_size(plan, outcome, strong) == pytest.approx(1.5)
        # No edge: p=0.3, payoff 1 -> kelly 0 -> floored exposure.
        weak = self.context(wins=6, average_win_r=1.0)
        assert position_size(plan, outcome, weak) == pytest.approx(0.5)
        # Below the minimum trade count: neutral (fresh chart).
        fresh = self.context(trades=5, wins=3)
        assert position_size(plan, outcome, fresh) == pytest.approx(1.0)

    def test_drawdown_shrinks_exposure(self) -> None:
        outcome = signal_outcome(3, rising(8))
        plan = decode_plan({**BASE_OVERRIDES, "sizing_model": float(SIZING_DRAWDOWN)})
        assert position_size(plan, outcome, self.context()) == pytest.approx(1.0)
        deep = self.context(drawdown_r=5.0)
        assert position_size(plan, outcome, deep) == pytest.approx(0.5)

    def test_budget_stands_aside_when_spent(self) -> None:
        outcome = signal_outcome(3, rising(8))
        plan = decode_plan({**BASE_OVERRIDES, "sizing_model": float(SIZING_BUDGET)})
        half = self.context(day_loss_r=1.0)
        assert position_size(plan, outcome, half) == pytest.approx(0.5)
        spent = self.context(day_loss_r=2.0)
        assert position_size(plan, outcome, spent) == 0.0


class TestManagedTrades:
    def managed(
        self, bars: list[Bar], overrides: dict[str, float]
    ) -> list[SimulatedTrade]:
        outcome = signal_outcome(3, bars)
        return manage_trades(
            (outcome,),
            bars,
            decode_plan(overrides),
            atr=wilder_atr(bars, 3),
            fee_r=0.0,
            horizon_bars=40,
        )

    def test_full_ladder_realizes_the_weighted_sum(self) -> None:
        trades = self.managed(rising(60), BASE_OVERRIDES)
        assert len(trades) == 1
        # 0.3*0.5 + 0.3*1.0 + 0.4*2.0 = 1.25 R, all targets reached.
        assert trades[0].exit_reason == "targets"
        assert trades[0].r_multiple == pytest.approx(1.25)

    def test_breakeven_protects_after_the_trigger(self) -> None:
        bars = rising(8)
        outcome = signal_outcome(3, bars)
        entry_close = float(bars[3].close.value)
        # Rise ~1R above entry (trigger breakeven + fill TP1), then crash.
        risk_proxy = 4.0  # roughly 2 x ATR on this series
        peak = entry_close + risk_proxy
        bars.append(make_bar(8, entry_close, peak, entry_close - 0.2, peak - 0.4))
        bars.append(make_bar(9, peak - 0.4, peak - 0.2, entry_close - 30, entry_close - 30))
        trades = manage_trades(
            (outcome,), bars, decode_plan(BASE_OVERRIDES),
            atr=wilder_atr(bars, 3), fee_r=0.0, horizon_bars=40,
        )
        assert len(trades) == 1
        trade = trades[0]
        # TP1 realized positive; the rest stopped at (or above) entry:
        # far better than the unmanaged -1R crash outcome.
        assert trade.exit_reason == "stop"
        assert trade.r_multiple > -0.5

    def test_trailing_locks_in_extended_moves(self) -> None:
        overrides = {**BASE_OVERRIDES, "trailing_enabled": 1.0, "trailing_distance_r": 0.5}
        bars = rising(30)
        outcome = signal_outcome(3, bars)
        # Strong rise through TP2 then a full crash: trailing keeps most.
        last = float(bars[-1].close.value)
        bars.append(make_bar(30, last, last + 30, last - 0.5, last + 30))
        bars.append(make_bar(31, last + 30, last + 30.5, 20.0, 20.0))
        with_trailing = manage_trades(
            (outcome,), bars, decode_plan(overrides),
            atr=wilder_atr(bars, 3), fee_r=0.0, horizon_bars=60,
        )
        without = manage_trades(
            (outcome,), bars, decode_plan(BASE_OVERRIDES),
            atr=wilder_atr(bars, 3), fee_r=0.0, horizon_bars=60,
        )
        assert with_trailing[0].r_multiple >= without[0].r_multiple

    def test_stop_first_on_same_bar_collision(self) -> None:
        bars = rising(6)
        outcome = signal_outcome(3, bars)
        base = float(bars[-1].close.value)
        # One giant bar spanning both the stop and every target.
        bars.append(make_bar(6, base, base + 100, 1.0, base))
        trades = manage_trades(
            (outcome,), bars, decode_plan(BASE_OVERRIDES),
            atr=wilder_atr(bars, 3), fee_r=0.0, horizon_bars=40,
        )
        assert trades[0].exit_reason == "stop"
        assert trades[0].r_multiple == pytest.approx(-1.0)


TINY = StageSettings(
    random_trials=4,
    latin_trials=4,
    bayesian_trials=4,
    refinement_rounds=1,
    validation_folds=2,
    test_share=0.25,
    monte_carlo_resamples=40,
    horizon_bars=20,
)


def build_risk_optimizer(count: int = 48) -> RiskOptimizer:
    from apex.core.context import MarketContext
    from apex.decision.kernel import CentralDecisionKernel

    snapshots = optimizer_snapshots(count)
    params = DecisionParams(
        execution_timing=TIMING_IMMEDIATE,
        atr_length=3,
        ema_length=3,
        rvol_gate_enabled=False,
        similarity_cooldown_enabled=False,
    )
    kernel = CentralDecisionKernel(params=params, clock=ManualClock(T0))
    context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
    outcomes = kernel.decide_series(snapshots, context).unwrap()
    return RiskOptimizer(
        outcomes=outcomes,
        bars=[snapshot.bar for snapshot in snapshots],
        symbol="BTCUSDT",
        timeframe="1h",
        fee_r=params.fee_slippage_r,
        settings=TINY,
        weights=ObjectiveWeights(minimum_trades=2),
    )


class TestRiskOptimizer:
    def test_deterministic_pipeline(self) -> None:
        first = build_risk_optimizer().optimize_detailed(seed=21).unwrap()
        second = build_risk_optimizer().optimize_detailed(seed=21).unwrap()
        assert first.best_overrides == second.best_overrides
        assert first.best_score == second.best_score

    def test_report_and_contract(self) -> None:
        optimizer = build_risk_optimizer()
        assert isinstance(optimizer, IOptimizer)
        report = optimizer.optimize_detailed(seed=21).unwrap()
        assert report.optimizer_version == "risk-1.0.0"
        assert len(report.sensitivity) == len(RISK_SEARCH_SPACE)
        assert report.trials >= 12
        assert 0.0 <= report.confidence <= 1.0

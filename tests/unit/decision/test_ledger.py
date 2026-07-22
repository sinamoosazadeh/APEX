"""Virtual trade ledger: arm/close mechanics, flatness, equity guard."""

from itertools import pairwise

import pytest
from apex.contracts.engines import DecisionSnapshot
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.decision.kernel import (
    TIMING_IMMEDIATE,
    CentralDecisionKernel,
    DecisionParams,
    _SideState,
)
from apex.decision.ledger import VirtualLedger

from tests.conftest import T0
from tests.unit.decision.test_decision import bullish_vector, make_bar, strong_channels


def armed_long(*, entry: float = 100.0, stop: float = 98.0, target: float = 105.0) -> VirtualLedger:
    ledger = VirtualLedger()
    ledger.arm(direction=1, entry=entry, stop=stop, target=target, index=5)
    return ledger


class TestVirtualLedger:
    def test_arm_records_geometry_and_r(self) -> None:
        ledger = armed_long()
        assert not ledger.is_flat
        assert ledger.entry_bar == 5
        assert ledger.open_r_win == pytest.approx(2.5)  # 5 points / 2 risk

    def test_entry_bar_never_closes(self) -> None:
        ledger = armed_long()
        bar = make_bar(5, 100.0, 106.0, 97.0, 101.0)  # touches both
        assert ledger.close_on_touch(bar, 5, conservative=True) is None
        assert not ledger.is_flat

    def test_target_touch_pays_open_r(self) -> None:
        ledger = armed_long()
        bar = make_bar(6, 104.0, 105.5, 103.0, 105.0)
        realized = ledger.close_on_touch(bar, 6, conservative=True)
        assert realized == pytest.approx(2.5)
        assert ledger.is_flat
        assert (ledger.wins, ledger.losses, ledger.trades) == (1, 0, 1)
        assert ledger.r_sum == pytest.approx(2.5)

    def test_stop_touch_costs_one_r(self) -> None:
        ledger = armed_long()
        bar = make_bar(6, 99.0, 99.5, 97.9, 98.5)
        realized = ledger.close_on_touch(bar, 6, conservative=True)
        assert realized == pytest.approx(-1.0)
        assert (ledger.wins, ledger.losses) == (0, 1)

    def test_collision_resolves_conservatively(self) -> None:
        ledger = armed_long()
        bar = make_bar(6, 100.0, 106.0, 97.0, 101.0)  # both touched
        assert ledger.close_on_touch(bar, 6, conservative=True) == pytest.approx(-1.0)

    def test_collision_pays_target_without_resolver(self) -> None:
        ledger = armed_long()
        bar = make_bar(6, 100.0, 106.0, 97.0, 101.0)
        assert ledger.close_on_touch(bar, 6, conservative=False) == pytest.approx(2.5)

    def test_short_side_mirrors(self) -> None:
        ledger = VirtualLedger()
        ledger.arm(direction=-1, entry=100.0, stop=102.0, target=95.0, index=0)
        bar = make_bar(1, 97.0, 98.0, 94.5, 95.5)  # target touched
        assert ledger.close_on_touch(bar, 1, conservative=True) == pytest.approx(2.5)

    def test_guard_needs_minimum_trades(self) -> None:
        ledger = VirtualLedger()
        ledger.trades = 11
        ledger.r_sum = -11.0
        ledger.equity_ema = 0.0
        assert not ledger.refresh_guard(ema_length=50, minimum_trades=12)
        ledger.trades = 12
        assert ledger.refresh_guard(ema_length=50, minimum_trades=12)

    def test_guard_ema_seeds_then_decays(self) -> None:
        ledger = VirtualLedger()
        assert not ledger.refresh_guard(ema_length=5, minimum_trades=1)
        assert ledger.equity_ema == pytest.approx(0.0)
        ledger.r_sum = 3.0  # a win landed; r_sum above its EMA
        assert not ledger.refresh_guard(ema_length=5, minimum_trades=0)
        ledger.trades = 1
        ledger.r_sum = -2.0  # collapse below the lagging EMA
        assert ledger.refresh_guard(ema_length=5, minimum_trades=1)


def series(count: int) -> list[DecisionSnapshot]:
    snapshots = []
    for index in range(count):
        base = 100.0 + index
        snapshots.append(
            DecisionSnapshot(
                bar=make_bar(index, base, base + 2.2, base - 0.4, base + 2.0),
                vector=bullish_vector(),
                probability_long=0.85,
                probability_short=0.05,
                channels=strong_channels(),
                macro_high=base + 52.0,
                macro_low=base - 48.0,
            )
        )
    return snapshots


def kernel(**overrides: object) -> CentralDecisionKernel:
    params = DecisionParams(
        execution_timing=TIMING_IMMEDIATE,
        atr_length=3,
        ema_length=3,
        rvol_gate_enabled=False,
        similarity_cooldown_enabled=False,
        cooldown_bars=1,
        **overrides,  # type: ignore[arg-type]
    )
    return CentralDecisionKernel(params=params, clock=ManualClock(T0))


class TestFlatnessGate:
    def test_flatness_suppresses_overlapping_signals(self) -> None:
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        outcomes = kernel().decide_series(series(40), context).unwrap()
        signal_bars = [
            index for index, outcome in enumerate(outcomes)
            if outcome.action == "signal"
        ]
        assert len(signal_bars) >= 2  # trade closes at target, then re-fires
        gaps = [b - a for a, b in pairwise(signal_bars)]
        assert min(gaps) > 5  # never back-to-back while a trade is open
        vetoed_flat = [
            outcome for outcome in outcomes
            if outcome.action == "veto" and "flatness" in outcome.failed_gates
        ]
        assert vetoed_flat  # blocked bars are audited with their gate

    def test_disabled_gate_restores_prior_behavior(self) -> None:
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        gated = kernel().decide_series(series(40), context).unwrap()
        free = (
            kernel(flatness_gate_enabled=False)
            .decide_series(series(40), context)
            .unwrap()
        )
        def count(outcomes: tuple[object, ...]) -> int:
            return sum(
                1 for outcome in outcomes
                if getattr(outcome, "action", "") == "signal"
            )

        assert count(free) > count(gated)


class TestEquityGuardWiring:
    def test_guard_term_raises_the_oracle(self) -> None:
        decision_kernel = kernel()
        snapshot = series(5)[4]
        side = _SideState(
            probability=0.85, contributors=13, catalyst=0.8,
            expected_r=1.0, confidence=0.6, ready=False,
        )
        calm = decision_kernel._oracle(snapshot, 0.3, side, guard_bad=False)
        guarded = decision_kernel._oracle(snapshot, 0.3, side, guard_bad=True)
        assert guarded - calm == pytest.approx(0.10)

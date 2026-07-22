"""Managed-trade simulator (Book V part 6).

Replays each fired signal under a candidate risk-management plan:

- **Stop model**: a fresh ATR stop at the chosen multiple, or the
  signal's own structure-hybrid stop (part 6's model selection over
  the models available today; liquidity/ICT/session stops arrive with
  their engines).
- **Three-level TP ladder** with volume allocations; each level
  realizes its share at its R multiple.
- **Breakeven**: once price reaches the trigger R, the stop moves to
  entry for the remaining volume.
- **Trailing**: once TP2 fills (and when enabled), the stop trails the
  best price at a fixed R distance.
- **Exposure shaping**: the whole trade is weighted by the sizing
  model - fixed, probability-adjusted or confidence-adjusted - times
  the risk fraction, so the R series is exposure-weighted.

Same-bar collisions resolve pessimistically (stop before target, the
AICE conservative resolver); unrealized volume marks to market at the
horizon. Kelly/portfolio/correlation sizing models require portfolio
state (Phase 9) and extend the model set then.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from apex.decision.kernel import DecisionOutcome
from apex.domain.market import Bar
from apex.features.calculations import clamp
from apex.optimization.risk.space import (
    SIZING_CONFIDENCE,
    SIZING_PROBABILITY,
    STOP_MODEL_ATR,
)
from apex.optimization.simulator import SimulatedTrade

# Sizing adjustment bounds (exposure shaping stays near 1x).
_SIZE_FLOOR, _SIZE_CEIL = 0.5, 1.5
_MINIMUM_REMAINDER = 0.10


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskPlan:
    """One candidate risk-management plan, decoded from overrides."""

    stop_model: int
    stop_atr_multiple: float
    tp1_r: float
    tp2_r: float
    tp3_r: float
    tp1_allocation: float
    tp2_allocation: float
    breakeven_trigger_r: float
    trailing_enabled: bool
    trailing_distance_r: float
    sizing_model: int
    risk_fraction: float

    @property
    def tp3_allocation(self) -> float:
        """The remainder after TP1/TP2 (floored by construction)."""
        return max(1.0 - self.tp1_allocation - self.tp2_allocation, _MINIMUM_REMAINDER)


def decode_plan(overrides: Mapping[str, float]) -> RiskPlan:
    """Build a plan from optimizer overrides (monotonic TP ladder)."""
    tp1 = overrides["tp1_r"]
    tp2 = tp1 + overrides["tp2_step_r"]
    tp3 = tp2 + overrides["tp3_step_r"]
    return RiskPlan(
        stop_model=int(overrides["stop_model"]),
        stop_atr_multiple=overrides["stop_atr_multiple"],
        tp1_r=tp1,
        tp2_r=tp2,
        tp3_r=tp3,
        tp1_allocation=overrides["tp1_allocation"],
        tp2_allocation=overrides["tp2_allocation"],
        breakeven_trigger_r=overrides["breakeven_trigger_r"],
        trailing_enabled=overrides["trailing_enabled"] >= 0.5,
        trailing_distance_r=overrides["trailing_distance_r"],
        sizing_model=int(overrides["sizing_model"]),
        risk_fraction=overrides["risk_fraction"],
    )


def position_size(plan: RiskPlan, outcome: DecisionOutcome) -> float:
    """Exposure weight for one trade under the sizing model."""
    base = plan.risk_fraction
    if plan.sizing_model == SIZING_PROBABILITY:
        return base * clamp(2.0 * outcome.probability, _SIZE_FLOOR, _SIZE_CEIL)
    if plan.sizing_model == SIZING_CONFIDENCE:
        conviction = outcome.probability * (1.0 - outcome.uncertainty)
        return base * clamp(2.0 * conviction, _SIZE_FLOOR, _SIZE_CEIL)
    return base


def manage_trades(
    outcomes: tuple[DecisionOutcome, ...],
    bars: list[Bar],
    plan: RiskPlan,
    *,
    atr: list[float | None],
    fee_r: float,
    horizon_bars: int,
) -> list[SimulatedTrade]:
    """Exposure-weighted R outcomes for every fired signal."""
    index_by_open = {bar.open_time.epoch_ms: i for i, bar in enumerate(bars)}
    trades: list[SimulatedTrade] = []
    for outcome in outcomes:
        if outcome.action != "signal" or outcome.signal is None:
            continue
        start = index_by_open.get(outcome.bar_open_ms)
        if start is None:
            continue
        trade = _manage(outcome, bars, start, plan, atr, fee_r, horizon_bars)
        if trade is not None:
            trades.append(trade)
    return trades


def _stop_price(
    outcome: DecisionOutcome,
    entry: float,
    plan: RiskPlan,
    bar_atr: float | None,
    long_side: bool,
) -> float:
    signal = outcome.signal
    assert signal is not None  # guarded by the caller
    if plan.stop_model == STOP_MODEL_ATR and bar_atr is not None and bar_atr > 0:
        sign = 1.0 if long_side else -1.0
        return entry - sign * bar_atr * plan.stop_atr_multiple
    return float(signal.stop_zone.lower.value)


def _manage(
    outcome: DecisionOutcome,
    bars: list[Bar],
    start: int,
    plan: RiskPlan,
    atr: list[float | None],
    fee_r: float,
    horizon_bars: int,
) -> SimulatedTrade | None:
    signal = outcome.signal
    assert signal is not None  # guarded by the caller
    entry = float(signal.entry_zone.lower.value)
    long_side = outcome.direction.value == "long"
    stop = _stop_price(outcome, entry, plan, atr[start], long_side)
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    state = _TradeState(entry=entry, stop=stop, risk=risk, long_side=long_side)
    last = min(start + horizon_bars, len(bars) - 1)
    for index in range(start + 1, last + 1):
        if state.step(bars[index], plan):
            break
    realized = state.finalize(bars[last], plan)
    size = position_size(plan, outcome)
    return SimulatedTrade(
        bar_open_ms=outcome.bar_open_ms,
        direction=outcome.direction.value,
        setup=outcome.setup,
        r_multiple=(realized - fee_r) * size,
        bars_held=max(min(state.bars_held, last - start), 0),
        exit_reason=state.exit_reason,
    )


class _TradeState:
    """Mutable managed-position state for one replayed trade."""

    def __init__(self, *, entry: float, stop: float, risk: float, long_side: bool) -> None:
        self.entry = entry
        self.stop = stop
        self.risk = risk
        self.long_side = long_side
        self.remaining = 1.0
        self.realized = 0.0
        self.peak = entry
        self.filled = [False, False, False]
        self.closed = False
        self.exit_reason = "horizon"
        self.bars_held = 0

    def _r(self, price: float) -> float:
        sign = 1.0 if self.long_side else -1.0
        return sign * (price - self.entry) / self.risk

    def _level(self, r_multiple: float) -> float:
        sign = 1.0 if self.long_side else -1.0
        return self.entry + sign * r_multiple * self.risk

    def step(self, bar: Bar, plan: RiskPlan) -> bool:
        """Advance one bar; True when the position fully closed."""
        self.bars_held += 1
        high = float(bar.high.value)
        low = float(bar.low.value)
        best = high if self.long_side else low
        self.peak = max(self.peak, best) if self.long_side else min(self.peak, best)
        stop_hit = low <= self.stop if self.long_side else high >= self.stop
        if stop_hit:  # pessimistic: stop resolves before targets
            self.realized += self.remaining * self._r(self.stop)
            self.remaining = 0.0
            self.closed = True
            self.exit_reason = "stop"
            return True
        self._fill_targets(high, low, plan)
        if self.remaining <= 0:
            self.closed = True
            self.exit_reason = "targets"
            return True
        self._manage_stop(plan)
        return False

    def _fill_targets(self, high: float, low: float, plan: RiskPlan) -> None:
        ladder = (
            (0, plan.tp1_r, plan.tp1_allocation),
            (1, plan.tp2_r, plan.tp2_allocation),
            (2, plan.tp3_r, plan.tp3_allocation),
        )
        for slot, r_multiple, allocation in ladder:
            if self.filled[slot]:
                continue
            level = self._level(r_multiple)
            touched = high >= level if self.long_side else low <= level
            if not touched:
                break
            share = min(allocation, self.remaining)
            self.realized += share * r_multiple
            self.remaining -= share
            self.filled[slot] = True

    def _manage_stop(self, plan: RiskPlan) -> None:
        peak_r = self._r(self.peak)
        if peak_r >= plan.breakeven_trigger_r:
            self.stop = (
                max(self.stop, self.entry) if self.long_side else min(self.stop, self.entry)
            )
        if plan.trailing_enabled and self.filled[1]:
            sign = 1.0 if self.long_side else -1.0
            trailed = self.peak - sign * plan.trailing_distance_r * self.risk
            self.stop = (
                max(self.stop, trailed) if self.long_side else min(self.stop, trailed)
            )

    def finalize(self, last_bar: Bar, plan: RiskPlan) -> float:
        """Realized R plus any remainder marked at the horizon close."""
        if not self.closed and self.remaining > 0:
            close = float(last_bar.close.value)
            self.realized += self.remaining * self._r(close)
            self.remaining = 0.0
        return self.realized

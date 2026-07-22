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
  model times the risk fraction, so the R series is exposure-weighted.
  Signal-shaped models (fixed, probability, confidence) read the
  outcome alone; the Phase 9 portfolio-state models read the fold's
  own trailing history, strictly causally (only trades CLOSED before
  a signal's entry bar inform its size):

  - **Constrained Kelly** (Book V 4.11, the shared Kelly source):
    trailing win rate and payoff, half-Kelly capped, shaped around
    the constrained midpoint; risk-fraction behavior below the
    minimum trade count (a fresh chart).
  - **Drawdown-adjusted**: exposure shrinks linearly with the
    weighted equity curve's current drawdown in R.
  - **Budget-adjusted**: exposure scales with the remaining daily
    loss budget in R (the portfolio.yaml 2%-day / 1%-trade ratio);
    a spent budget stands the trade aside entirely, mirroring the
    portfolio governance daily limit.

Same-bar collisions resolve pessimistically (stop before target, the
AICE conservative resolver); unrealized volume marks to market at the
horizon. Correlation-adjusted sizing is enforced at the portfolio
engine's admission (a single-series simulation cannot exercise
cross-symbol correlation); full cross-symbol backtesting arrives with
the Phase 11 research orchestration.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from apex.decision.kernel import DecisionOutcome
from apex.domain.market import Bar
from apex.features.calculations import clamp, volatility_regime_factor
from apex.optimization.risk.space import (
    ENTRY_LIMIT,
    SIZING_BUDGET,
    SIZING_CONFIDENCE,
    SIZING_DRAWDOWN,
    SIZING_KELLY,
    SIZING_PROBABILITY,
    STOP_MODEL_ATR,
    STOP_MODEL_ICT_OB,
    STOP_MODEL_LIQUIDITY,
    STOP_MODEL_SESSION,
    STOP_MODEL_SIGNAL,
    STOP_MODEL_VOLATILITY,
)
from apex.optimization.simulator import SimulatedTrade
from apex.portfolio.account import TradeStatistics, constrained_kelly, day_key

# Sizing adjustment bounds (exposure shaping stays near 1x).
_SIZE_FLOOR, _SIZE_CEIL = 0.5, 1.5
_MINIMUM_REMAINDER = 0.10
# Constrained-Kelly shape (Book V 4.11 defaults; the live sizing
# authority is the portfolio engine's configured Kelly settings).
_KELLY_MULTIPLIER = 0.5
_KELLY_CAP = 0.25
_KELLY_MINIMUM_TRADES = 12
_KELLY_NEUTRAL = _KELLY_CAP / 2.0
# Drawdown-adjusted shape: R of weighted drawdown that floors exposure.
_DRAWDOWN_SCALE_R = 10.0
# Daily budget in R: portfolio.yaml daily_loss_limit_fraction (0.02)
# over the per-trade risk_fraction (0.01).
_DAY_BUDGET_R = 2.0
# Level-stop buffer beyond the structure level (AICE 0.15 x ATR).
_LEVEL_BUFFER_ATR = 0.15
# Volatility stop: ATR width vs its own mean (the volume family's
# regime input) over this window.
_VOLATILITY_MEAN_WINDOW = 100


@dataclass(frozen=True, slots=True, kw_only=True)
class StopLevels:
    """Signal-bar structure levels for the level stop models.

    ``None`` is the AICE na-branch: the model falls back to ATR.
    """

    ob_long_bottom: float | None = None
    ob_short_top: float | None = None
    macro_high: float | None = None
    macro_low: float | None = None


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
    entry_model: int
    limit_offset_atr: float
    limit_patience_bars: int

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
        entry_model=int(overrides.get("entry_model", 0.0)),
        limit_offset_atr=overrides.get("limit_offset_atr", 0.0),
        limit_patience_bars=int(overrides.get("limit_patience_bars", 3.0)),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class SizingContext:
    """Trailing fold state a history-aware sizing model reads."""

    statistics: TradeStatistics
    drawdown_r: float
    day_loss_r: float


@dataclass(frozen=True, slots=True, kw_only=True)
class _ManagedClose:
    """One completed managed trade before exposure weighting."""

    close_ms: int
    weighted_r: float
    win: bool


class _SizingHistory:
    """Chronological closed-trade memory (strictly causal reads)."""

    def __init__(self) -> None:
        self._closes: list[_ManagedClose] = []

    def record(self, close: _ManagedClose) -> None:
        self._closes.append(close)
        self._closes.sort(key=lambda item: item.close_ms)

    def context(self, entry_ms: int) -> SizingContext:
        """The fold state visible at one entry instant."""
        visible = [item for item in self._closes if item.close_ms <= entry_ms]
        wins = [item.weighted_r for item in visible if item.win]
        losses = [item.weighted_r for item in visible if not item.win]
        equity = 0.0
        peak = 0.0
        for item in visible:
            equity += item.weighted_r
            peak = max(peak, equity)
        entry_day = day_key(entry_ms)
        day_losses = sum(
            -item.weighted_r
            for item in visible
            if item.weighted_r < 0 and day_key(item.close_ms) == entry_day
        )
        return SizingContext(
            statistics=TradeStatistics(
                trades=len(visible),
                wins=len(wins),
                losses=len(losses),
                r_sum=equity,
                average_win_r=sum(wins) / len(wins) if wins else 0.0,
                average_loss_r=sum(losses) / len(losses) if losses else 0.0,
                consecutive_losses=0,
            ),
            drawdown_r=max(peak - equity, 0.0),
            day_loss_r=day_losses,
        )


def position_size(
    plan: RiskPlan, outcome: DecisionOutcome, context: SizingContext | None = None
) -> float:
    """Exposure weight for one trade under the sizing model.

    History-aware models fall back to the plain risk fraction when no
    fold context exists yet (the fresh-chart behavior).
    """
    base = plan.risk_fraction
    if plan.sizing_model == SIZING_PROBABILITY:
        return base * clamp(2.0 * outcome.probability, _SIZE_FLOOR, _SIZE_CEIL)
    if plan.sizing_model == SIZING_CONFIDENCE:
        conviction = outcome.probability * (1.0 - outcome.uncertainty)
        return base * clamp(2.0 * conviction, _SIZE_FLOOR, _SIZE_CEIL)
    if context is None:
        return base
    if plan.sizing_model == SIZING_KELLY:
        kelly = constrained_kelly(
            context.statistics,
            multiplier=_KELLY_MULTIPLIER,
            cap=_KELLY_CAP,
            minimum_trades=_KELLY_MINIMUM_TRADES,
            fallback=_KELLY_NEUTRAL,
        )
        return base * clamp(kelly / _KELLY_NEUTRAL, _SIZE_FLOOR, _SIZE_CEIL)
    if plan.sizing_model == SIZING_DRAWDOWN:
        return base * clamp(
            1.0 - context.drawdown_r / _DRAWDOWN_SCALE_R, _SIZE_FLOOR, 1.0
        )
    if plan.sizing_model == SIZING_BUDGET:
        remaining = 1.0 - context.day_loss_r / _DAY_BUDGET_R
        return base * clamp(remaining, 0.0, 1.0)
    return base


def manage_trades(
    outcomes: tuple[DecisionOutcome, ...],
    bars: list[Bar],
    plan: RiskPlan,
    *,
    atr: list[float | None],
    fee_r: float,
    horizon_bars: int,
    levels: Mapping[int, StopLevels] | None = None,
    slippage_r: float = 0.0,
) -> list[SimulatedTrade]:
    """Exposure-weighted R outcomes for every fired signal.

    Trades are managed in entry order; history-aware sizing reads only
    trades already closed at each entry. A budget-exhausted size of
    zero - or a limit entry never filled within its patience - stands
    the trade aside. ``levels`` supplies signal-bar structure levels
    for the level stop models; ``slippage_r`` is the crossing cost a
    market entry pays on top of ``fee_r`` (limit fills avoid it).
    """
    index_by_open = {bar.open_time.epoch_ms: i for i, bar in enumerate(bars)}
    history = _SizingHistory()
    trades: list[SimulatedTrade] = []
    for outcome in outcomes:
        if outcome.action != "signal" or outcome.signal is None:
            continue
        start = index_by_open.get(outcome.bar_open_ms)
        if start is None:
            continue
        context = history.context(outcome.bar_open_ms)
        size = position_size(plan, outcome, context)
        if size <= 0.0:
            continue
        stop_levels = levels.get(outcome.bar_open_ms) if levels else None
        managed = _manage(
            outcome, bars, start, plan, atr, fee_r, horizon_bars, size,
            stop_levels=stop_levels, slippage_r=slippage_r,
        )
        if managed is None:
            continue
        trade, close_ms = managed
        trades.append(trade)
        history.record(
            _ManagedClose(
                close_ms=close_ms,
                weighted_r=trade.r_multiple,
                win=trade.r_multiple > 0,
            )
        )
    return trades


def _entry_fill(
    bars: list[Bar],
    start: int,
    plan: RiskPlan,
    bar_atr: float | None,
    base_entry: float,
    *,
    long_side: bool,
    slippage_r: float,
) -> tuple[int, float, float] | None:
    """(fill index, entry price, entry cost R) under the entry model.

    Market fills at the signal close and pays the slippage share; a
    limit rests at the offset and fills on the first touch within its
    patience window - never filled stands the trade aside.
    """
    if plan.entry_model != ENTRY_LIMIT or bar_atr is None or bar_atr <= 0:
        return start, base_entry, slippage_r
    sign = 1.0 if long_side else -1.0
    limit = base_entry - sign * plan.limit_offset_atr * bar_atr
    last = min(start + plan.limit_patience_bars, len(bars) - 1)
    for index in range(start + 1, last + 1):
        bar = bars[index]
        touched = (
            float(bar.low.value) <= limit
            if long_side
            else float(bar.high.value) >= limit
        )
        if touched:
            return index, limit, 0.0
    return None


def _session_extreme(bars: list[Bar], start: int, *, long_side: bool) -> float | None:
    """The signal bar's UTC-day extreme so far (strictly causal)."""
    day = day_key(bars[start].open_time.epoch_ms)
    lows: list[float] = []
    highs: list[float] = []
    for index in range(start, -1, -1):
        if day_key(bars[index].open_time.epoch_ms) != day:
            break
        lows.append(float(bars[index].low.value))
        highs.append(float(bars[index].high.value))
    if not lows:
        return None
    return min(lows) if long_side else max(highs)


def _volatility_width(atr: list[float | None], start: int) -> float:
    """ATR vs its own mean (the volume family's regime input)."""
    current = atr[start]
    if current is None or current <= 0:
        return 1.0
    window = [
        value
        for value in atr[max(start - _VOLATILITY_MEAN_WINDOW + 1, 0) : start + 1]
        if value is not None
    ]
    mean = sum(window) / len(window) if window else 0.0
    return current / mean if mean > 0 else 1.0


def _level_stop(
    level: float | None, entry: float, bar_atr: float, *, long_side: bool
) -> float | None:
    """Level minus the AICE buffer; None keeps the na-branch."""
    if level is None:
        return None
    sign = 1.0 if long_side else -1.0
    candidate = level - sign * bar_atr * _LEVEL_BUFFER_ATR
    # The stop must protect: below the entry for longs, above for shorts.
    if (candidate < entry) if long_side else (candidate > entry):
        return candidate
    return None


def _stop_price(
    outcome: DecisionOutcome,
    entry: float,
    plan: RiskPlan,
    bar_atr: float | None,
    long_side: bool,
    *,
    levels: StopLevels | None,
    session_extreme: float | None,
    volatility_width: float,
) -> float:
    """The candidate plan's stop (Book V stop catalog).

    Level models (ICT order-block boundary, external liquidity
    extreme, session extreme) apply the AICE buffer and fall back to
    the plain ATR stop when their level is absent or unprotective.
    """
    signal = outcome.signal
    assert signal is not None  # guarded by the caller
    if plan.stop_model == STOP_MODEL_SIGNAL:
        return float(signal.stop_zone.lower.value)
    if bar_atr is None or bar_atr <= 0:
        return float(signal.stop_zone.lower.value)
    sign = 1.0 if long_side else -1.0
    atr_stop = entry - sign * bar_atr * plan.stop_atr_multiple
    if plan.stop_model == STOP_MODEL_ATR:
        return atr_stop
    if plan.stop_model == STOP_MODEL_VOLATILITY:
        factor = volatility_regime_factor(volatility_width)
        return entry - sign * bar_atr * plan.stop_atr_multiple * factor
    level: float | None = None
    if plan.stop_model == STOP_MODEL_ICT_OB and levels is not None:
        level = levels.ob_long_bottom if long_side else levels.ob_short_top
    elif plan.stop_model == STOP_MODEL_LIQUIDITY and levels is not None:
        level = levels.macro_low if long_side else levels.macro_high
    elif plan.stop_model == STOP_MODEL_SESSION:
        level = session_extreme
    candidate = _level_stop(level, entry, bar_atr, long_side=long_side)
    return candidate if candidate is not None else atr_stop


def _manage(
    outcome: DecisionOutcome,
    bars: list[Bar],
    start: int,
    plan: RiskPlan,
    atr: list[float | None],
    fee_r: float,
    horizon_bars: int,
    size: float,
    *,
    stop_levels: StopLevels | None,
    slippage_r: float,
) -> tuple[SimulatedTrade, int] | None:
    signal = outcome.signal
    assert signal is not None  # guarded by the caller
    base_entry = float(signal.entry_zone.lower.value)
    long_side = outcome.direction.value == "long"
    filled = _entry_fill(
        bars, start, plan, atr[start], base_entry,
        long_side=long_side, slippage_r=slippage_r,
    )
    if filled is None:
        return None
    fill_index, entry, entry_cost_r = filled
    stop = _stop_price(
        outcome, entry, plan, atr[start], long_side,
        levels=stop_levels,
        session_extreme=_session_extreme(bars, start, long_side=long_side),
        volatility_width=_volatility_width(atr, start),
    )
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    state = _TradeState(entry=entry, stop=stop, risk=risk, long_side=long_side)
    last = min(fill_index + horizon_bars, len(bars) - 1)
    close_index = last
    for index in range(fill_index + 1, last + 1):
        if state.step(bars[index], plan):
            close_index = index
            break
    realized = state.finalize(bars[last], plan)
    trade = SimulatedTrade(
        bar_open_ms=outcome.bar_open_ms,
        direction=outcome.direction.value,
        setup=outcome.setup,
        r_multiple=(realized - fee_r - entry_cost_r) * size,
        bars_held=max(min(state.bars_held, last - fill_index), 0),
        exit_reason=state.exit_reason,
    )
    return trade, bars[close_index].open_time.epoch_ms


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

"""Signal outcome simulator (Book V part 5: signal quality only).

Replays each fired signal against the bars that follow it: the trade
exits at the stop (-1R) or at the base risk-reward target (+base_rr R)
- whichever a later bar touches first - or marks to market at the
horizon. Same-bar collisions resolve pessimistically to the stop.
Position sizing, partial exits and trade management belong to the
risk/execution optimizers (Book V parts 6+), not here.
"""

from dataclasses import dataclass

from apex.decision.kernel import DecisionOutcome
from apex.domain.market import Bar


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulatedTrade:
    """One simulated signal outcome in R units."""

    bar_open_ms: int
    direction: str
    setup: str
    r_multiple: float
    bars_held: int
    exit_reason: str


def simulate_signals(
    outcomes: tuple[DecisionOutcome, ...],
    bars: list[Bar],
    *,
    base_risk_reward: float,
    fee_r: float,
    horizon_bars: int,
) -> list[SimulatedTrade]:
    """R outcomes for every fired signal, in firing order."""
    index_by_open = {bar.open_time.epoch_ms: i for i, bar in enumerate(bars)}
    trades: list[SimulatedTrade] = []
    for outcome in outcomes:
        if outcome.action != "signal" or outcome.signal is None:
            continue
        start = index_by_open.get(outcome.bar_open_ms)
        if start is None:
            continue
        trades.append(
            _replay(outcome, bars, start, base_risk_reward, fee_r, horizon_bars)
        )
    return trades


def _replay(
    outcome: DecisionOutcome,
    bars: list[Bar],
    start: int,
    base_risk_reward: float,
    fee_r: float,
    horizon_bars: int,
) -> SimulatedTrade:
    signal = outcome.signal
    assert signal is not None  # guarded by the caller
    entry = float(signal.entry_zone.lower.value)
    stop = float(signal.stop_zone.lower.value)
    target = float(signal.target_zones[1].lower.value)  # tp2 = 1x base_rr
    long_side = outcome.direction.value == "long"
    risk = max(abs(entry - stop), 1e-9)
    last = min(start + horizon_bars, len(bars) - 1)
    for held, index in enumerate(range(start + 1, last + 1), start=1):
        bar = bars[index]
        high = float(bar.high.value)
        low = float(bar.low.value)
        stop_hit = low <= stop if long_side else high >= stop
        target_hit = high >= target if long_side else low <= target
        if stop_hit:  # pessimistic on same-bar collision
            return _trade(outcome, -1.0 - fee_r, held, "stop")
        if target_hit:
            return _trade(outcome, base_risk_reward - fee_r, held, "target")
    close = float(bars[last].close.value)
    sign = 1.0 if long_side else -1.0
    marked = sign * (close - entry) / risk - fee_r
    return _trade(outcome, marked, max(last - start, 0), "horizon")


def _trade(
    outcome: DecisionOutcome, r_multiple: float, held: int, reason: str
) -> SimulatedTrade:
    return SimulatedTrade(
        bar_open_ms=outcome.bar_open_ms,
        direction=outcome.direction.value,
        setup=outcome.setup,
        r_multiple=r_multiple,
        bars_held=held,
        exit_reason=reason,
    )

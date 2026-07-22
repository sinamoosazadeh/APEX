"""Simulation metrics (Book V part 5: the multi-objective inputs).

Pure, deterministic reductions of a simulated R series: the objective
maximands (expectancy, net R, profit factor, Sharpe/Sortino/Calmar,
recovery, win rate, average trade, consistency) and the penalty
inputs (max drawdown, losing streak, variance, trade count).
"""

from dataclasses import dataclass

from apex.optimization.simulator import SimulatedTrade


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationMetrics:
    """Deterministic figures for one simulated parameter trial."""

    trade_count: int
    expectancy: float
    net_r: float
    profit_factor: float
    win_rate: float
    average_trade: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    recovery_factor: float
    losing_streak: int
    consistency: float
    variance: float


def compute_metrics(trades: list[SimulatedTrade], *, window: int = 10) -> SimulationMetrics:
    """Reduce an R series into the objective figures (zeros when empty)."""
    if not trades:
        return SimulationMetrics(
            trade_count=0, expectancy=0.0, net_r=0.0, profit_factor=0.0,
            win_rate=0.0, average_trade=0.0, sharpe=0.0, sortino=0.0,
            max_drawdown=0.0, calmar=0.0, recovery_factor=0.0,
            losing_streak=0, consistency=0.0, variance=0.0,
        )
    rs = [trade.r_multiple for trade in trades]
    count = len(rs)
    net = sum(rs)
    mean = net / count
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float(count if wins else 0)
    variance = sum((r - mean) ** 2 for r in rs) / count
    deviation = variance**0.5
    downside = [min(r, 0.0) for r in rs]
    downside_dev = (sum(d * d for d in downside) / count) ** 0.5
    drawdown = _max_drawdown(rs)
    streak = _longest_losing_streak(rs)
    return SimulationMetrics(
        trade_count=count,
        expectancy=mean,
        net_r=net,
        profit_factor=profit_factor,
        win_rate=len(wins) / count,
        average_trade=mean,
        sharpe=mean / deviation if deviation > 0 else 0.0,
        sortino=mean / downside_dev if downside_dev > 0 else (mean if mean > 0 else 0.0),
        max_drawdown=drawdown,
        calmar=net / drawdown if drawdown > 0 else (net if net > 0 else 0.0),
        recovery_factor=net / drawdown if drawdown > 0 else (net if net > 0 else 0.0),
        losing_streak=streak,
        consistency=_consistency(rs, window),
        variance=variance,
    )


def _max_drawdown(rs: list[float]) -> float:
    peak = equity = 0.0
    worst = 0.0
    for r in rs:
        equity += r
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def _longest_losing_streak(rs: list[float]) -> int:
    longest = current = 0
    for r in rs:
        current = current + 1 if r <= 0 else 0
        longest = max(longest, current)
    return longest


def _consistency(rs: list[float], window: int) -> float:
    """Share of consecutive windows with non-negative sums."""
    if len(rs) < window:
        return 1.0 if sum(rs) >= 0 else 0.0
    sums = [
        sum(rs[start : start + window]) for start in range(0, len(rs) - window + 1)
    ]
    positive = sum(1 for value in sums if value >= 0)
    return positive / len(sums)

"""Multi-objective composite score (Book V part 5).

Blends the maximands into a single deterministic score and subtracts
the penalty stack. Objectives are squashed onto comparable scales
before weighting so no single figure dominates; weights are data
(Constitution 3.7) with Book V defaults.
"""

from dataclasses import dataclass

from apex.core.validation import ensure_in_range, ensure_positive
from apex.features.calculations import clamp
from apex.optimization.metrics import SimulationMetrics


@dataclass(frozen=True, slots=True, kw_only=True)
class ObjectiveWeights:
    """Weights of the maximands and penalties."""

    expectancy: float = 0.25
    net_r: float = 0.10
    profit_factor: float = 0.10
    sharpe: float = 0.15
    sortino: float = 0.05
    calmar: float = 0.05
    win_rate: float = 0.10
    consistency: float = 0.20
    drawdown_penalty: float = 0.15
    streak_penalty: float = 0.05
    variance_penalty: float = 0.05
    minimum_trades: int = 5
    low_trade_penalty: float = 0.50

    def __post_init__(self) -> None:
        ensure_positive(self.minimum_trades, "minimum_trades")
        for name in (
            "expectancy", "net_r", "profit_factor", "sharpe", "sortino",
            "calmar", "win_rate", "consistency", "drawdown_penalty",
            "streak_penalty", "variance_penalty", "low_trade_penalty",
        ):
            ensure_in_range(getattr(self, name), 0.0, 1.0, name)


# Squash scales: the value mapping each figure to ~1.0.
_EXPECTANCY_SCALE = 1.0
_NET_SCALE = 10.0
_PROFIT_FACTOR_SCALE = 3.0
_SHARPE_SCALE = 1.0
_SORTINO_SCALE = 1.5
_CALMAR_SCALE = 3.0
_DRAWDOWN_SCALE = 5.0
_STREAK_SCALE = 6.0
_VARIANCE_SCALE = 4.0


def objective_score(metrics: SimulationMetrics, weights: ObjectiveWeights) -> float:
    """The composite score for one trial (higher is better)."""
    if metrics.trade_count == 0:
        return -weights.low_trade_penalty
    gain = (
        weights.expectancy * clamp(metrics.expectancy / _EXPECTANCY_SCALE, -1.0, 1.0)
        + weights.net_r * clamp(metrics.net_r / _NET_SCALE, -1.0, 1.0)
        + weights.profit_factor
        * clamp(metrics.profit_factor / _PROFIT_FACTOR_SCALE, 0.0, 1.0)
        + weights.sharpe * clamp(metrics.sharpe / _SHARPE_SCALE, -1.0, 1.0)
        + weights.sortino * clamp(metrics.sortino / _SORTINO_SCALE, -1.0, 1.0)
        + weights.calmar * clamp(metrics.calmar / _CALMAR_SCALE, -1.0, 1.0)
        + weights.win_rate * metrics.win_rate
        + weights.consistency * metrics.consistency
    )
    penalty = (
        weights.drawdown_penalty * clamp(metrics.max_drawdown / _DRAWDOWN_SCALE, 0.0, 1.0)
        + weights.streak_penalty * clamp(metrics.losing_streak / _STREAK_SCALE, 0.0, 1.0)
        + weights.variance_penalty * clamp(metrics.variance / _VARIANCE_SCALE, 0.0, 1.0)
    )
    if metrics.trade_count < weights.minimum_trades:
        penalty += weights.low_trade_penalty * (
            1.0 - metrics.trade_count / weights.minimum_trades
        )
    return gain - penalty

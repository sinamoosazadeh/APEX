"""Account state fold (Book I 8.4/8.15; Book II 21.4).

Tracks capital, realized PnL, peak equity and drawdown, the daily and
weekly realized-loss windows that back the risk budgets, the
consecutive-loss streak, and the closed-trade statistics that feed
the constrained-Kelly estimate. All calendar arithmetic is integer
epoch math (UTC days; Monday-aligned weeks), so the fold is exactly
reproducible from bar timestamps alone.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from apex.portfolio.ledger import ClosedTrade

_DAY_MS = 86_400_000
# Epoch day 0 (1970-01-01) was a Thursday; +3 aligns weeks to Monday.
_MONDAY_SHIFT = 3
_DAYS_PER_WEEK = 7


@dataclass(frozen=True, slots=True, kw_only=True)
class TradeStatistics:
    """Closed-trade statistics for sizing models (Book V 4.11)."""

    trades: int = 0
    wins: int = 0
    losses: int = 0
    r_sum: float = 0.0
    average_win_r: float = 0.0
    average_loss_r: float = 0.0
    consecutive_losses: int = 0

    @property
    def win_rate(self) -> float:
        """Share of winning trades; 0 before any trade."""
        return self.wins / self.trades if self.trades else 0.0


def day_key(epoch_ms: int) -> int:
    """UTC day bucket of an instant."""
    return epoch_ms // _DAY_MS


def week_key(epoch_ms: int) -> int:
    """Monday-aligned week bucket of an instant."""
    return (day_key(epoch_ms) + _MONDAY_SHIFT) // _DAYS_PER_WEEK


def constrained_kelly(
    statistics: TradeStatistics,
    *,
    multiplier: float,
    cap: float,
    minimum_trades: int,
    fallback: float,
) -> float:
    """Constrained Kelly fraction (Book V 4.11: never full Kelly).

    ``kelly = p - (1 - p) / payoff`` scaled by ``multiplier`` and
    clamped to ``[0, cap]``. Below the minimum trade count - or when
    the payoff is undefined - the ``fallback`` fraction applies, the
    fresh-chart behavior. The single Kelly source for the portfolio
    engine and the risk optimizer (Constitution 2.12).
    """
    if statistics.trades < minimum_trades:
        return fallback
    if statistics.wins == 0 or statistics.losses == 0:
        return fallback
    payoff = statistics.average_win_r / abs(statistics.average_loss_r)
    if payoff <= 0:
        return fallback
    win_rate = statistics.win_rate
    raw = win_rate - (1.0 - win_rate) / payoff
    return min(max(raw * multiplier, 0.0), cap)


@dataclass(slots=True)
class AccountFold:
    """Mutable account state over one deterministic fold."""

    base_currency: str
    initial_capital: Decimal
    realized: Decimal = Decimal(0)
    peak_equity: Decimal = field(default=Decimal(0))
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    day: int = -1
    day_start_equity: Decimal = Decimal(0)
    day_realized: Decimal = Decimal(0)
    week: int = -1
    week_start_equity: Decimal = Decimal(0)
    week_realized: Decimal = Decimal(0)
    consecutive_losses: int = 0
    wins: int = 0
    losses: int = 0
    r_sum: float = 0.0
    win_r_sum: float = 0.0
    loss_r_sum: float = 0.0

    def __post_init__(self) -> None:
        if self.peak_equity == 0:
            self.peak_equity = self.initial_capital

    @property
    def closed_equity(self) -> Decimal:
        """Capital plus realized PnL (cash equity)."""
        return self.initial_capital + self.realized

    def equity(self, unrealized: Decimal) -> Decimal:
        """Marked-to-market equity."""
        return self.closed_equity + unrealized

    def roll_windows(self, epoch_ms: int, marked_equity: Decimal) -> None:
        """Open new day/week risk windows at their boundaries."""
        day = day_key(epoch_ms)
        if day != self.day:
            self.day = day
            self.day_start_equity = marked_equity
            self.day_realized = Decimal(0)
        week = week_key(epoch_ms)
        if week != self.week:
            self.week = week
            self.week_start_equity = marked_equity
            self.week_realized = Decimal(0)

    def apply_close(self, trade: ClosedTrade) -> None:
        """Fold one realized trade into the account."""
        amount = trade.realized_pnl.amount
        self.realized += amount
        self.day_realized += amount
        self.week_realized += amount
        if trade.win:
            self.wins += 1
            self.win_r_sum += trade.realized_r
            self.consecutive_losses = 0
        else:
            self.losses += 1
            self.loss_r_sum += trade.realized_r
            self.consecutive_losses += 1
        self.r_sum += trade.realized_r

    def mark(self, marked_equity: Decimal) -> None:
        """Update the peak and drawdown at a marked equity point."""
        if marked_equity > self.peak_equity:
            self.peak_equity = marked_equity
        if self.peak_equity > 0:
            drawdown = float(
                (self.peak_equity - marked_equity) / self.peak_equity
            )
            self.current_drawdown = max(drawdown, 0.0)
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)

    def window_loss_fraction(self, *, weekly: bool) -> float:
        """Realized loss of the open window as a fraction of its start."""
        realized = self.week_realized if weekly else self.day_realized
        start = self.week_start_equity if weekly else self.day_start_equity
        if realized >= 0 or start <= 0:
            return 0.0
        return float(-realized / start)

    def statistics(self) -> TradeStatistics:
        """The closed-trade statistics snapshot."""
        trades = self.wins + self.losses
        return TradeStatistics(
            trades=trades,
            wins=self.wins,
            losses=self.losses,
            r_sum=self.r_sum,
            average_win_r=self.win_r_sum / self.wins if self.wins else 0.0,
            average_loss_r=self.loss_r_sum / self.losses if self.losses else 0.0,
            consecutive_losses=self.consecutive_losses,
        )

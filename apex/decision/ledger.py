"""AICE virtual trade ledger (Book VI lines 2906-2942, 3217-3280).

The kernel's own bar-synchronous position memory - the Pine ``var``
block that backs two decision gates:

- **Flatness** (line 2958/2971): ``flat_ok = pos_dir == 0`` joins the
  base gate, so no signal fires while the virtual trade is open.
- **Virtual equity guard** (lines 2941-2945): closed trades accumulate
  ``r_sum``; when the trade count reaches its minimum and ``r_sum``
  sits below its own EMA, the failure-risk oracle gains +0.10.

The ledger arms when a signal fires (entry at close, the signal's stop
and its final target, AICE ``tp_price := tp3_price``) and closes on
the first stop/target touch strictly after the entry bar, resolving
same-bar collisions with the conservative resolver (input line 186).
Pine execution order is preserved: the guard EMA refreshes before this
bar's closes, entries precede closes, and a close only frees the gate
for the following bar.

This is decision-layer state - deterministic, one virtual position per
series. Durable institutional positions, account state and exposure
live in the portfolio platform (Book II ch. 13/21), which consumes the
fired-signal stream downstream.
"""

from dataclasses import dataclass

from apex.domain.market import Bar

# Same-bar collision loss (lines 3222-3223).
_LOSS_R = -1.0
_MINIMUM_RISK = 1e-9


@dataclass(slots=True)
class VirtualLedger:
    """One series' virtual trade state and closed-trade statistics."""

    direction: int = 0
    entry_price: float = 0.0
    stop_price: float = 0.0
    target_price: float = 0.0
    open_r_win: float = 0.0
    entry_bar: int = -1
    wins: int = 0
    losses: int = 0
    trades: int = 0
    r_sum: float = 0.0
    equity_ema: float | None = None

    @property
    def is_flat(self) -> bool:
        """AICE ``flat_ok`` (line 2958)."""
        return self.direction == 0

    def refresh_guard(self, *, ema_length: int, minimum_trades: int) -> bool:
        """Per-bar EMA refresh and the raw guard condition (2941-2942).

        Runs before this bar's closes, so both the EMA input and the
        comparison see ``r_sum`` as of the previous bar's end - exactly
        the Pine line order. Returns the raw ``r_sum < ema`` condition
        once the trade count reaches its minimum; the kernel applies
        the enable flag (Pine computes ``equity_ma`` unconditionally).
        """
        alpha = 2.0 / (float(ema_length) + 1.0)
        if self.equity_ema is None:
            self.equity_ema = self.r_sum
        else:
            self.equity_ema += alpha * (self.r_sum - self.equity_ema)
        return self.trades >= minimum_trades and self.r_sum < self.equity_ema

    def arm(
        self,
        *,
        direction: int,
        entry: float,
        stop: float,
        target: float,
        index: int,
    ) -> None:
        """Open the virtual trade at signal construction (3092-3130).

        ``target`` is the signal's final objective (AICE ``tp_price :=
        tp3_price``); ``open_r_win`` is its R multiple against the
        armed risk (``(tp_price - entry_price) / risk_pts``).
        """
        risk = max(abs(entry - stop), _MINIMUM_RISK)
        self.direction = direction
        self.entry_price = entry
        self.stop_price = stop
        self.target_price = target
        self.open_r_win = abs(target - entry) / risk
        self.entry_bar = index

    def close_on_touch(self, bar: Bar, index: int, *, conservative: bool) -> float | None:
        """Close the open trade on a stop/target touch (3217-3272).

        The entry bar itself never closes (``bar_index > entry_bar``);
        a same-bar stop+target collision resolves to the stop when the
        conservative resolver is on, to the target otherwise. Returns
        the realized R on a close, ``None`` otherwise.
        """
        if self.direction == 0 or index <= self.entry_bar:
            return None
        high = float(bar.high.value)
        low = float(bar.low.value)
        if self.direction == 1:
            stop_hit = low <= self.stop_price
            target_hit = high >= self.target_price
        else:
            stop_hit = high >= self.stop_price
            target_hit = low <= self.target_price
        if not stop_hit and not target_hit:
            return None
        win = target_hit and not (stop_hit and conservative)
        realized = self.open_r_win if win else _LOSS_R
        if win:
            self.wins += 1
        else:
            self.losses += 1
        self.trades += 1
        self.r_sum += realized
        self.direction = 0
        self.entry_price = 0.0
        self.stop_price = 0.0
        self.target_price = 0.0
        self.open_r_win = 0.0
        self.entry_bar = -1
        return realized

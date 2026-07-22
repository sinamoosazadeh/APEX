"""Exposure engine (Book II 13.10/21.6; Book I 8.6).

Computes the marked exposure book over the open lots - per-symbol
signed notional, gross/net aggregates and direction counts - and the
rolling return correlation between symbols (Book II 21.8) reusing the
shared :func:`correlation` fold (Constitution 2.12: one source per
computation). Effective (beta/leverage-weighted) exposure and the
sector dimensions arrive with their data sources in later phases.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from math import log

from apex.core.enums import Direction
from apex.features.calculations import correlation
from apex.portfolio.ledger import OpenLot


@dataclass(frozen=True, slots=True, kw_only=True)
class ExposureView:
    """The marked exposure book at one instant."""

    gross_notional: Decimal
    net_notional: Decimal
    by_symbol: Mapping[str, Decimal]
    open_positions: int
    long_positions: int
    short_positions: int

    def symbol_notional(self, symbol: str) -> Decimal:
        """Absolute marked notional held in one symbol."""
        return abs(self.by_symbol.get(symbol, Decimal(0)))


def exposure_view(
    lots: Sequence[OpenLot], last_close: Mapping[str, Decimal]
) -> ExposureView:
    """Mark the open lots to their symbols' last confirmed closes."""
    by_symbol: dict[str, Decimal] = {}
    longs = 0
    shorts = 0
    for lot in lots:
        symbol = lot.position.symbol
        mark = last_close.get(symbol, lot.entry)
        notional = lot.position.quantity.value * mark
        if lot.position.direction is Direction.LONG:
            longs += 1
            signed = notional
        else:
            shorts += 1
            signed = -notional
        by_symbol[symbol] = by_symbol.get(symbol, Decimal(0)) + signed
    gross = sum((abs(value) for value in by_symbol.values()), Decimal(0))
    net = sum(by_symbol.values(), Decimal(0))
    return ExposureView(
        gross_notional=gross,
        net_notional=net,
        by_symbol=by_symbol,
        open_positions=len(lots),
        long_positions=longs,
        short_positions=shorts,
    )


def unrealized_pnl(
    lots: Sequence[OpenLot], last_close: Mapping[str, Decimal]
) -> Decimal:
    """Marked-to-market PnL of the open lots."""
    total = Decimal(0)
    for lot in lots:
        mark = last_close.get(lot.position.symbol, lot.entry)
        sign = Decimal(1) if lot.position.direction is Direction.LONG else Decimal(-1)
        total += (mark - lot.entry) * lot.position.quantity.value * sign
    return total


def rolling_return_correlation(
    closes_a: Sequence[float], closes_b: Sequence[float], window: int
) -> float | None:
    """Rolling log-return correlation over the aligned tails.

    Returns ``None`` until both series carry a full window of returns
    - an unknown correlation is never reported as zero.
    """
    length = min(len(closes_a), len(closes_b))
    if length < window + 1:
        return None
    tail_a = closes_a[-(window + 1) :]
    tail_b = closes_b[-(window + 1) :]
    if min(tail_a) <= 0 or min(tail_b) <= 0:
        return None
    returns_a = [log(tail_a[i] / tail_a[i - 1]) for i in range(1, len(tail_a))]
    returns_b = [log(tail_b[i] / tail_b[i - 1]) for i in range(1, len(tail_b))]
    series = correlation(returns_a, returns_b, window)
    return series[-1] if series else None

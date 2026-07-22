"""Position lifecycle fold (Book II 21.5; Book I 8.4).

Turns fired-signal records into durable :class:`Position` lineages and
closed-trade records. The close model is the AICE virtual-trade model
the decision kernel guarantees per series: one open position at a
time, closed on the first stop/final-target touch strictly after the
entry bar, same-bar collisions resolved conservatively. Fills happen
at the exact stop/target prices with the configured taker fee charged
on entry and exit notionals (Phase 10); slippage modeling lives in
the execution engines, which own real fills.

All money arithmetic is exact :class:`Decimal` via :class:`Money`;
R multiples are dimensionless floats.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from apex.core.enums import Direction, PositionStatus, Timeframe
from apex.core.time.timestamp import Timestamp
from apex.core.types import Price, Quantity
from apex.domain.market import Bar
from apex.domain.money import Money
from apex.domain.position import Position

_EIGHT_PLACES = Decimal("0.00000001")

CLOSE_REASON_STOP = "stop"
CLOSE_REASON_TARGET = "target"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClosedTrade:
    """One realized virtual trade (the portfolio's audit record)."""

    position_id: uuid.UUID
    lineage_id: uuid.UUID
    exchange: str
    symbol: str
    timeframe: Timeframe
    direction: Direction
    opened_at: Timestamp
    closed_at: Timestamp
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    quantity: Decimal
    risk_amount: Money
    realized_pnl: Money
    realized_r: float
    win: bool
    reason: str
    entry_bar_ms: int


@dataclass(slots=True)
class OpenLot:
    """One open position with its armed risk geometry."""

    position: Position
    timeframe: Timeframe
    entry: Decimal
    stop: Decimal
    target: Decimal
    risk_per_unit: Decimal
    risk_amount: Money
    entry_bar_ms: int
    entry_index: int


def bar_close_time(bar: Bar) -> Timestamp:
    """The confirmed close instant of a bar."""
    return Timestamp(epoch_ms=bar.open_time.epoch_ms + bar.timeframe.duration_ms)


def size_position(
    equity: Decimal, risk_fraction: float, risk_per_unit: Decimal
) -> Decimal:
    """Risk-fraction sizing: ``equity x fraction / stop distance``."""
    if risk_per_unit <= 0 or equity <= 0:
        return Decimal(0)
    risk_amount = equity * Decimal(str(risk_fraction))
    return (risk_amount / risk_per_unit).quantize(_EIGHT_PLACES)


def open_lot(
    *,
    bar: Bar,
    timeframe: Timeframe,
    direction: Direction,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
    quantity: Decimal,
    risk_amount: Money,
    entry_index: int,
    signal_id: uuid.UUID | None = None,
) -> OpenLot:
    """Arm a new open lot from a fired signal at its decision bar."""
    opened_at = bar_close_time(bar)
    position = Position(
        created_at=opened_at,
        exchange=bar.exchange,
        symbol=bar.symbol,
        direction=direction,
        quantity=Quantity(quantity),
        average_entry=Price(entry),
        opened_at=opened_at,
        status=PositionStatus.OPEN,
        signal_id=signal_id,
    )
    return OpenLot(
        position=position,
        timeframe=timeframe,
        entry=entry,
        stop=stop,
        target=target,
        risk_per_unit=max(abs(entry - stop), _EIGHT_PLACES),
        risk_amount=risk_amount,
        entry_bar_ms=bar.open_time.epoch_ms,
        entry_index=entry_index,
    )


def close_lot(
    lot: OpenLot,
    bar: Bar,
    *,
    conservative: bool,
    currency: str,
    fee_rate: Decimal = Decimal(0),
) -> tuple[Position, ClosedTrade] | None:
    """Close on the first stop/target touch after the entry bar.

    Mirrors the kernel's virtual ledger exactly (AICE lines
    3217-3272): the entry bar never closes; a same-bar stop+target
    collision resolves to the stop when the conservative resolver is
    on, to the target otherwise. ``fee_rate`` charges the taker fee on
    both the entry and exit notionals into the realized PnL (Phase 10;
    zero keeps ideal fills). ``realized_r`` stays the price-geometry R
    - exactly the kernel ledger's series. Returns the closed position
    version and its trade record, or ``None`` when the lot stays open.
    """
    if bar.open_time.epoch_ms <= lot.entry_bar_ms:
        return None
    high = bar.high.value
    low = bar.low.value
    long_side = lot.position.direction is Direction.LONG
    if long_side:
        stop_hit = low <= lot.stop
        target_hit = high >= lot.target
    else:
        stop_hit = high >= lot.stop
        target_hit = low <= lot.target
    if not stop_hit and not target_hit:
        return None
    win = target_hit and not (stop_hit and conservative)
    exit_price = lot.target if win else lot.stop
    sign = Decimal(1) if long_side else Decimal(-1)
    quantity = lot.position.quantity.value
    fees = (lot.entry + exit_price) * quantity * fee_rate
    pnl_amount = (exit_price - lot.entry) * quantity * sign - fees
    realized_pnl = Money(currency=currency, amount=pnl_amount)
    signed_move = (exit_price - lot.entry) if long_side else (lot.entry - exit_price)
    realized_r = float(signed_move / lot.risk_per_unit)
    closed_at = bar_close_time(bar)
    closed = lot.position.evolve(
        created_at=closed_at,
        status=PositionStatus.CLOSED,
        closed_at=closed_at,
        realized_pnl=realized_pnl,
    )
    trade = ClosedTrade(
        position_id=closed.object_id,
        lineage_id=closed.lineage_id or closed.object_id,
        exchange=closed.exchange,
        symbol=closed.symbol,
        timeframe=lot.timeframe,
        direction=closed.direction,
        opened_at=lot.position.opened_at,
        closed_at=closed_at,
        entry=lot.entry,
        stop=lot.stop,
        target=lot.target,
        exit_price=exit_price,
        quantity=quantity,
        risk_amount=lot.risk_amount,
        realized_pnl=realized_pnl,
        realized_r=realized_r,
        win=win,
        reason=CLOSE_REASON_TARGET if win else CLOSE_REASON_STOP,
        entry_bar_ms=lot.entry_bar_ms,
    )
    return closed, trade

"""Position contract.

A position version records the state of one market exposure at a point
in time. Changes (fills, partial closes) produce new versions via
``evolve``; the position lineage is the full audit trail.
"""

import uuid
from dataclasses import dataclass, field

from apex.core.base import BaseObject
from apex.core.enums import Direction, PositionStatus
from apex.core.exceptions import ValidationError
from apex.core.time.timestamp import Timestamp
from apex.core.types import Leverage, Price, Quantity
from apex.core.validation import ensure_not_empty, ensure_symbol
from apex.domain.money import Money

_NO_LEVERAGE = Leverage(1.0)


@dataclass(frozen=True, slots=True, kw_only=True)
class Position(BaseObject):
    """One market exposure and its lifecycle state."""

    exchange: str
    symbol: str
    direction: Direction
    quantity: Quantity
    average_entry: Price
    opened_at: Timestamp
    status: PositionStatus = PositionStatus.OPEN
    leverage: Leverage = _NO_LEVERAGE
    signal_id: uuid.UUID | None = None
    order_ids: tuple[uuid.UUID, ...] = field(default=())
    realized_pnl: Money | None = None
    closed_at: Timestamp | None = None

    def _validate(self) -> None:
        ensure_not_empty(self.exchange, "exchange")
        ensure_symbol(self.symbol)
        if self.direction is Direction.NEUTRAL:
            raise ValidationError("position direction cannot be neutral", code="RSK-010")
        closed = self.status is not PositionStatus.OPEN
        if closed and self.closed_at is None:
            raise ValidationError(
                "closed position requires closed_at",
                code="RSK-011",
                details={"status": self.status.value},
            )
        if not closed and self.closed_at is not None:
            raise ValidationError(
                "open position must not carry closed_at",
                code="RSK-012",
            )
        if self.closed_at is not None and self.closed_at < self.opened_at:
            raise ValidationError(
                "position cannot close before it opened",
                code="RSK-013",
                details={"opened_at": str(self.opened_at), "closed_at": str(self.closed_at)},
            )

    @property
    def is_open(self) -> bool:
        """Whether the position still carries exposure."""
        return self.status is PositionStatus.OPEN

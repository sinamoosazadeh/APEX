"""Portfolio snapshot contract (Book II 5.11).

The portfolio publishes an immutable snapshot of its state at every
change; consumers never reach into portfolio internals.
"""

from dataclasses import dataclass, field

from apex.core.base import BaseObject
from apex.core.exceptions import ValidationError
from apex.core.time.timestamp import Timestamp
from apex.core.types import Drawdown
from apex.domain.money import Money
from apex.domain.position import Position


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSnapshot(BaseObject):
    """State of the whole portfolio at one instant."""

    as_of: Timestamp
    base_currency: str
    equity: Money
    cash: Money
    total_exposure: Money
    unrealized_pnl: Money
    realized_pnl: Money
    current_drawdown: Drawdown
    open_positions: tuple[Position, ...] = field(default=())

    def _validate(self) -> None:
        amounts = (
            self.equity,
            self.cash,
            self.total_exposure,
            self.unrealized_pnl,
            self.realized_pnl,
        )
        for money in amounts:
            if money.currency != self.base_currency:
                raise ValidationError(
                    "portfolio amounts must be in the base currency",
                    code="RSK-020",
                    details={
                        "base_currency": self.base_currency,
                        "found": money.currency,
                    },
                )
        if self.total_exposure.is_negative:
            raise ValidationError(
                "total exposure cannot be negative",
                code="RSK-021",
                details={"total_exposure": str(self.total_exposure)},
            )
        for position in self.open_positions:
            if not position.is_open:
                raise ValidationError(
                    "snapshot open_positions must contain only open positions",
                    code="RSK-022",
                    details={"position": str(position.object_id)},
                )

    @property
    def position_count(self) -> int:
        """Number of open positions."""
        return len(self.open_positions)

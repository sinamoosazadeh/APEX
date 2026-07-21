"""Order contract.

An order is an immutable instruction to the execution platform. Status
progression produces new versions via ``evolve`` - never mutation
(Book II 4.8/4.10).
"""

import uuid
from dataclasses import dataclass

from apex.core.base import BaseObject
from apex.core.enums import OrderSide, OrderStatus, OrderType, TimeInForce
from apex.core.exceptions import ValidationError
from apex.core.types import Price, Quantity
from apex.core.validation import ensure_not_empty, ensure_symbol


@dataclass(frozen=True, slots=True, kw_only=True)
class Order(BaseObject):
    """An exchange order instruction and its lifecycle state."""

    exchange: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Quantity
    time_in_force: TimeInForce = TimeInForce.GTC
    limit_price: Price | None = None
    stop_price: Price | None = None
    status: OrderStatus = OrderStatus.NEW
    signal_id: uuid.UUID | None = None
    client_order_id: str | None = None
    exchange_order_id: str | None = None

    def _validate(self) -> None:
        ensure_not_empty(self.exchange, "exchange")
        ensure_symbol(self.symbol)
        needs_limit = self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT)
        if needs_limit and self.limit_price is None:
            raise ValidationError(
                "limit-type orders require a limit price",
                code="EXE-001",
                details={"order_type": self.order_type.value},
            )
        if not needs_limit and self.limit_price is not None:
            raise ValidationError(
                "non-limit orders must not carry a limit price",
                code="EXE-002",
                details={"order_type": self.order_type.value},
            )
        needs_stop = self.order_type in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT)
        if needs_stop and self.stop_price is None:
            raise ValidationError(
                "stop-type orders require a stop price",
                code="EXE-003",
                details={"order_type": self.order_type.value},
            )
        if not needs_stop and self.stop_price is not None:
            raise ValidationError(
                "non-stop orders must not carry a stop price",
                code="EXE-004",
                details={"order_type": self.order_type.value},
            )

    @property
    def is_terminal(self) -> bool:
        """Whether the order can no longer change state."""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        )

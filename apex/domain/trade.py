"""Trade (fill) contract.

A trade records an execution fact: some quantity of an order filled at
a price, with fees. Facts never change - trades are terminal objects.
"""

import uuid
from dataclasses import dataclass

from apex.core.base import BaseObject
from apex.core.enums import LiquidityRole, OrderSide
from apex.core.time.timestamp import Timestamp
from apex.core.types import Price, Quantity
from apex.core.validation import ensure_not_empty, ensure_symbol
from apex.domain.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class Trade(BaseObject):
    """One fill of an order."""

    order_id: uuid.UUID
    exchange: str
    symbol: str
    side: OrderSide
    price: Price
    quantity: Quantity
    fee: Money
    liquidity_role: LiquidityRole
    executed_at: Timestamp
    exchange_trade_id: str | None = None

    def _validate(self) -> None:
        ensure_not_empty(self.exchange, "exchange")
        ensure_symbol(self.symbol)

    def notional(self, currency: str) -> Money:
        """Traded notional value ``price * quantity`` in ``currency``."""
        return Money(currency=currency, amount=self.price.value * self.quantity.value)

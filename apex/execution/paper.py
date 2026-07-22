"""Paper execution engine (Book II ch. 12; run modes backtest/paper).

The same :class:`IExecutionEngine` contract as live execution, filled
deterministically from confirmed bars instead of a venue:

- **Market** orders fill at the first confirmed bar opening at or
  after the request, at the open price adjusted by the configured
  slippage (basis points against the trade), paying the taker fee.
- **Limit** orders rest at their price and fill on the first touch
  within the patience window (maker fee, no slippage); untouched
  orders expire with no fills.

Fees and slippage are config; fills are exact Decimal; every fill is
a domain :class:`Trade`. Exits stay with the portfolio's close model
- paper execution owns entries, exactly the boundary the golden rule
draws (12.30: execution never re-decides).
"""

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Final

from apex.core.context import ExecutionContext
from apex.core.enums import LiquidityRole, OrderSide, OrderType
from apex.core.exceptions import ApexError, ExecutionError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.core.types import Price, Quantity
from apex.domain.market import Bar
from apex.domain.money import Money
from apex.domain.order import Order
from apex.domain.trade import Trade
from apex.execution.config import ExecutionSettings
from apex.storage.bars import SqliteBarRepository

_BPS: Final[Decimal] = Decimal(10_000)


class PaperExecutionEngine:
    """Deterministic bar-driven fills behind the execution contract."""

    def __init__(
        self,
        *,
        settings: ExecutionSettings,
        bar_repository: SqliteBarRepository,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._settings = settings
        self._bars = bar_repository
        self._clock = clock
        self._logger = logger

    async def execute(
        self,
        order: Order,
        context: ExecutionContext,
    ) -> Result[Sequence[Trade]]:
        """Fill the order from confirmed bars; empty means unfilled."""
        try:
            fills = await self._fill(order, context)
        except ApexError as error:
            return Result.failure(error)
        return Result.success(fills)

    async def _fill(
        self, order: Order, context: ExecutionContext
    ) -> tuple[Trade, ...]:
        if context.timeframe is None:
            raise ExecutionError(
                "paper execution needs the series timeframe in the context",
                code="EXE-026",
            )
        if order.order_type not in (OrderType.MARKET, OrderType.LIMIT):
            raise ExecutionError(
                "paper execution fills market and limit entries only",
                code="EXE-027",
                details={"order_type": order.order_type.value},
            )
        duration = context.timeframe.duration_ms
        start = context.requested_at
        end = Timestamp(
            epoch_ms=start.epoch_ms
            + (self._settings.paper_patience_bars + 1) * duration
        )
        bars = await self._bars.get_range(
            order.exchange, order.symbol, context.timeframe,
            start=start, end=end, closed_only=True,
        )
        if not bars:
            self._logger.info(
                "paper_no_bars_yet",
                symbol=order.symbol,
                timeframe=context.timeframe.value,
                requested_at=str(start),
            )
            return ()
        if order.order_type is OrderType.MARKET:
            return (self._market_fill(order, bars[0]),)
        return self._limit_fill(order, bars)

    def _market_fill(self, order: Order, bar: Bar) -> Trade:
        """Next confirmed open, slipped against the trade, taker fee."""
        slip = Decimal(str(self._settings.paper_slippage_bps)) / _BPS
        sign = Decimal(1) if order.side is OrderSide.BUY else Decimal(-1)
        price = bar.open.value * (Decimal(1) + sign * slip)
        return self._trade(
            order,
            price=price,
            executed_at=bar.open_time,
            role=LiquidityRole.TAKER,
            fee_rate=Decimal(str(self._settings.taker_fee_rate)),
        )

    def _limit_fill(self, order: Order, bars: list[Bar]) -> tuple[Trade, ...]:
        """First touch within patience fills at the limit; else expire."""
        assert order.limit_price is not None  # enforced by Order._validate
        limit = order.limit_price.value
        buying = order.side is OrderSide.BUY
        for bar in bars[: self._settings.paper_patience_bars]:
            touched = bar.low.value <= limit if buying else bar.high.value >= limit
            if touched:
                return (
                    self._trade(
                        order,
                        price=limit,
                        executed_at=bar_close(bar),
                        role=LiquidityRole.MAKER,
                        fee_rate=Decimal(str(self._settings.maker_fee_rate)),
                    ),
                )
        self._logger.info(
            "paper_limit_expired",
            symbol=order.symbol,
            limit=str(limit),
            patience_bars=self._settings.paper_patience_bars,
        )
        return ()

    def _trade(
        self,
        order: Order,
        *,
        price: Decimal,
        executed_at: Timestamp,
        role: LiquidityRole,
        fee_rate: Decimal,
    ) -> Trade:
        quantity = order.quantity.value
        fee = (price * quantity * fee_rate).quantize(Decimal("0.00000001"))
        seed = order.client_order_id or str(order.object_id)
        trade_id = uuid.uuid5(uuid.NAMESPACE_OID, seed).hex[:16]
        return Trade(
            created_at=executed_at,
            order_id=order.object_id,
            exchange=order.exchange,
            symbol=order.symbol,
            side=order.side,
            price=Price(price.quantize(Decimal("0.00000001"))),
            quantity=Quantity(quantity),
            fee=Money(currency="USDT", amount=fee),
            liquidity_role=role,
            executed_at=executed_at,
            exchange_trade_id=f"paper-{trade_id}",
        )


def bar_close(bar: Bar) -> Timestamp:
    """The confirmed close instant of a bar."""
    return Timestamp(epoch_ms=bar.open_time.epoch_ms + bar.timeframe.duration_ms)

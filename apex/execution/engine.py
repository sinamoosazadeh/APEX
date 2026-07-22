"""Live execution engine (Book II ch. 12/20; Book VII API v2).

Turns an approved order into venue reality and nothing else - the
golden rule (12.30): no signal, probability, size or decision is ever
altered here. The lifecycle: idempotent submission (deterministic
client order id), fill polling against the venue until terminal or
timeout, timeout cancellation (the configured policy), and fill
retrieval translated into domain :class:`Trade` records.

Bracket protection (the signal's stop and final target) rides the
venue's attached stopLoss/takeProfit triggers, so protection exists
at the exchange even if this process dies - the recovery principle
of 12.26. Smart order routing, order-book intelligence and the
TWAP/VWAP/POV/iceberg engines need book-depth streams and multiple
venues (documented Phase 10 deferrals).
"""

import asyncio
from collections.abc import Sequence
from decimal import Decimal
from typing import Final

from apex.core.context import ExecutionContext
from apex.core.enums import OrderStatus
from apex.core.exceptions import ApexError, ExecutionError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.domain.order import Order
from apex.domain.trade import Trade
from apex.execution.config import ExecutionSettings
from apex.execution.trading.client import ORDER_PATH, USER_TRADES_PATH, ToobitTradingClient
from apex.execution.trading.translator import (
    contract_symbol,
    order_params,
    parse_status,
    parse_trades,
    unwrap,
)

_TERMINAL: Final[tuple[OrderStatus, ...]] = (
    OrderStatus.FILLED,
    OrderStatus.CANCELED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
)


class LiveExecutionEngine:
    """Order lifecycle against the Toobit futures venue."""

    def __init__(
        self,
        *,
        client: ToobitTradingClient,
        settings: ExecutionSettings,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._client = client
        self._settings = settings
        self._clock = clock
        self._logger = logger

    @property
    def can_trade(self) -> bool:
        """Whether venue credentials are configured."""
        return self._client.can_trade

    async def execute(
        self,
        order: Order,
        context: ExecutionContext,
    ) -> Result[Sequence[Trade]]:
        """Contract surface: work the bare order (no bracket legs)."""
        return await self.execute_bracket(order, context)

    async def execute_bracket(
        self,
        order: Order,
        context: ExecutionContext,
        *,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> Result[Sequence[Trade]]:
        """Submit, poll to terminal, cancel on timeout, return fills."""
        try:
            fills = await self._work(order, stop_loss, take_profit)
        except ApexError as error:
            self._logger.failure("live_execution_failed", error)
            return Result.failure(error)
        return Result.success(fills)

    async def _work(
        self,
        order: Order,
        stop_loss: Decimal | None,
        take_profit: Decimal | None,
    ) -> tuple[Trade, ...]:
        contract = contract_symbol(order.symbol, self._settings.contract_infix)
        params = order_params(
            order, contract=contract, stop_loss=stop_loss, take_profit=take_profit
        )
        placed = unwrap(await self._client.place_order(params), path=ORDER_PATH)
        venue_id, status, _, _ = parse_status(placed, path=ORDER_PATH)
        self._logger.info(
            "live_order_placed",
            symbol=order.symbol,
            contract=contract,
            venue_order_id=venue_id,
            status=status.value,
        )
        status = await self._await_terminal(order, venue_id, status)
        if status in (OrderStatus.REJECTED, OrderStatus.EXPIRED):
            raise ExecutionError(
                "venue rejected the order",
                code="EXE-028",
                details={"venue_order_id": venue_id, "status": status.value},
            )
        return await self._fills(order, contract, venue_id)

    async def _await_terminal(
        self, order: Order, venue_id: str, status: OrderStatus
    ) -> OrderStatus:
        """Poll until terminal; cancel at the timeout policy."""
        deadline = self._clock.now().epoch_ms + self._settings.order_timeout_ms
        while status not in _TERMINAL:
            if self._clock.now().epoch_ms >= deadline:
                self._logger.info(
                    "live_order_timeout_cancel",
                    venue_order_id=venue_id,
                    status=status.value,
                )
                canceled = unwrap(
                    await self._client.cancel_order(order_id=venue_id),
                    path=ORDER_PATH,
                )
                _, status, _, _ = parse_status(canceled, path=ORDER_PATH)
                break
            await asyncio.sleep(self._settings.poll_interval_ms / 1000)
            queried = unwrap(
                await self._client.query_order(order_id=venue_id), path=ORDER_PATH
            )
            _, status, _, _ = parse_status(queried, path=ORDER_PATH)
        return status

    async def _fills(
        self, order: Order, contract: str, venue_id: str
    ) -> tuple[Trade, ...]:
        payload = unwrap(
            await self._client.user_trades(contract), path=USER_TRADES_PATH
        )
        fills = parse_trades(
            payload, order=order, venue_order_id=venue_id, path=USER_TRADES_PATH
        )
        self._logger.info(
            "live_order_fills",
            venue_order_id=venue_id,
            fills=len(fills),
        )
        return tuple(fills)

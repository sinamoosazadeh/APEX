"""Anti-corruption translator for the Toobit trading API (Book VII).

The venue dialect (contract symbols, v2 payload envelopes, side +
positionSide semantics, string decimals) never leaks past this module
- the same boundary discipline as the Phase 3 market-data translator
(Book II 5.37). One-way position mode is assumed: a LONG position
opens with BUY/LONG and a SHORT with SELL/SHORT.
"""

import uuid
from decimal import Decimal, InvalidOperation
from typing import Final

from apex.core.enums import LiquidityRole, OrderSide, OrderStatus, OrderType, TimeInForce
from apex.core.exceptions import ExecutionError
from apex.core.serialization import JsonValue
from apex.core.time.timestamp import Timestamp
from apex.core.types import Price, Quantity
from apex.domain.money import Money
from apex.domain.order import Order
from apex.domain.trade import Trade

_QUOTE: Final[str] = "USDT"

_STATUS: Final[dict[str, OrderStatus]] = {
    "NEW": OrderStatus.NEW,
    "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
    "FILLED": OrderStatus.FILLED,
    "CANCELED": OrderStatus.CANCELED,
    "REJECTED": OrderStatus.REJECTED,
}

_TIME_IN_FORCE: Final[dict[TimeInForce, str]] = {
    TimeInForce.GTC: "GTC",
    TimeInForce.IOC: "IOC",
    TimeInForce.FOK: "FOK",
    TimeInForce.POST_ONLY: "POST_ONLY",
}


def contract_symbol(symbol: str, infix: str) -> str:
    """Map a market symbol to its futures contract id.

    ``BTCUSDT`` with the ``-SWAP-`` infix becomes ``BTC-SWAP-USDT``
    (Book VII contract naming). Symbols not ending in the quote asset
    are rejected rather than guessed.
    """
    if not symbol.endswith(_QUOTE):
        raise ExecutionError(
            "cannot derive the contract id for this symbol",
            code="EXE-018",
            details={"symbol": symbol},
        )
    base = symbol[: -len(_QUOTE)]
    return f"{base}{infix}{_QUOTE}"


def order_params(
    order: Order,
    *,
    contract: str,
    stop_loss: Decimal | None = None,
    take_profit: Decimal | None = None,
) -> dict[str, str]:
    """Build the signed POST /api/v2/futures/order business params.

    The bracket legs ride the venue's attached ``stopLoss`` /
    ``takeProfit`` triggers (mark-price triggered, market on trigger)
    so protection exists at the venue even if the client dies.
    """
    if order.client_order_id is None:
        raise ExecutionError(
            "orders must carry a client order id (idempotency)",
            code="EXE-019",
            details={"order": str(order.object_id)},
        )
    long_side = order.side is OrderSide.BUY
    params: dict[str, str] = {
        "symbol": contract,
        "side": "BUY" if long_side else "SELL",
        "positionSide": "LONG" if long_side else "SHORT",
        "type": "LIMIT" if order.order_type is OrderType.LIMIT else "MARKET",
        "newClientOrderId": order.client_order_id,
        "quantity": str(order.quantity.value),
    }
    if order.order_type is OrderType.LIMIT:
        assert order.limit_price is not None  # enforced by Order._validate
        params["price"] = str(order.limit_price.value)
        params["timeInForce"] = _TIME_IN_FORCE[order.time_in_force]
    if stop_loss is not None:
        params["stopLoss"] = str(stop_loss)
        params["slTriggerBy"] = "MARK_PRICE"
        params["slOrderType"] = "MARKET"
    if take_profit is not None:
        params["takeProfit"] = str(take_profit)
        params["tpTriggerBy"] = "MARK_PRICE"
        params["tpOrderType"] = "MARKET"
    return params


def unwrap(payload: JsonValue, *, path: str) -> JsonValue:
    """Unwrap the v2 ``{code, msg, data}`` envelope; error on failure."""
    if not isinstance(payload, dict):
        raise ExecutionError(
            "unexpected trading API payload shape",
            code="EXE-020",
            details={"path": path, "type": type(payload).__name__},
        )
    code = payload.get("code")
    if code != 200:
        raise ExecutionError(
            "trading API returned a business error",
            code="EXE-021",
            details={"path": path, "code": str(code), "msg": str(payload.get("msg"))},
        )
    return payload.get("data")


def parse_status(payload: JsonValue, *, path: str) -> tuple[str, OrderStatus, Decimal, Decimal]:
    """(venue order id, status, executed quantity, average price)."""
    if not isinstance(payload, dict):
        raise ExecutionError(
            "order payload must be a mapping",
            code="EXE-022",
            details={"path": path, "type": type(payload).__name__},
        )
    raw_status = str(payload.get("status", ""))
    status = _STATUS.get(raw_status)
    if status is None:
        raise ExecutionError(
            "unknown venue order status",
            code="EXE-023",
            details={"path": path, "status": raw_status},
        )
    return (
        str(payload.get("orderId", "")),
        status,
        _decimal(payload.get("executedQty", "0"), "executedQty", path),
        _decimal(payload.get("avgPrice", "0"), "avgPrice", path),
    )


def parse_trades(
    payload: JsonValue,
    *,
    order: Order,
    venue_order_id: str,
    path: str,
) -> list[Trade]:
    """Fills of one order from the user-trades payload."""
    if not isinstance(payload, list):
        raise ExecutionError(
            "user-trades payload must be a list",
            code="EXE-024",
            details={"path": path, "type": type(payload).__name__},
        )
    fills: list[Trade] = []
    for item in payload:
        if not isinstance(item, dict) or str(item.get("orderId")) != venue_order_id:
            continue
        executed_at = Timestamp(epoch_ms=int(str(item.get("time", "0"))))
        fills.append(
            Trade(
                created_at=executed_at,
                order_id=order.object_id,
                exchange=order.exchange,
                symbol=order.symbol,
                side=order.side,
                price=Price(_decimal(item.get("price"), "price", path)),
                quantity=Quantity(_decimal(item.get("qty"), "qty", path)),
                fee=Money(
                    currency=str(item.get("commissionAsset", _QUOTE)),
                    amount=_decimal(item.get("commission", "0"), "commission", path),
                ),
                liquidity_role=(
                    LiquidityRole.MAKER
                    if bool(item.get("isMaker"))
                    else LiquidityRole.TAKER
                ),
                executed_at=executed_at,
                exchange_trade_id=str(item.get("id", "")),
            )
        )
    return fills


def client_order_id(execution_id: uuid.UUID) -> str:
    """Deterministic idempotent client order id for one execution."""
    return f"apex-{execution_id.hex[:20]}"


def _decimal(raw: object, field: str, path: str) -> Decimal:
    try:
        return Decimal(str(raw))
    except InvalidOperation as error:
        raise ExecutionError(
            "trading API returned a non-decimal value",
            code="EXE-025",
            details={"path": path, "field": field, "value": repr(raw)},
        ) from error

"""Emergency position flattening (Book II 25.29; Book I 8.27).

The FLATTENED kill-switch response: every open position is closed
best-effort - a reduce-only market order at the venue when trading
credentials exist, and an immediate ledger close at the latest
confirmed bar's close (the emergency mark) either way, so exposure
accounting never lags the emergency. Execution owns this module
because no order may reach the venue outside the execution layer
(20.31).
"""

from dataclasses import replace
from decimal import Decimal

from apex.core.exceptions import ApexError
from apex.core.identity import IdProvider
from apex.core.logging import StructuredLogger
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.execution.trading.client import ToobitTradingClient
from apex.execution.trading.translator import (
    client_order_id,
    close_params,
    contract_symbol,
)
from apex.portfolio.store import PositionRecord, SqlitePortfolioRepository
from apex.storage.bars import SqliteBarRepository

CLOSE_REASON_FLATTENED = "flattened"


async def flatten_positions(
    *,
    portfolio: SqlitePortfolioRepository,
    portfolio_id: str,
    bars: SqliteBarRepository,
    exchange_id: str,
    client: ToobitTradingClient,
    contract_infix: str,
    fee_rate: Decimal,
    ids: IdProvider,
    clock: Clock,
    logger: StructuredLogger,
) -> int:
    """Close every open position; returns how many were closed."""
    open_records = [
        record
        for record in await portfolio.get_positions(portfolio_id)
        if record.status == "open"
    ]
    closed = 0
    for record in open_records:
        mark = await _emergency_mark(bars, exchange_id, record)
        if mark is None:
            logger.warning(
                "flatten_no_mark",
                symbol=record.symbol,
                timeframe=record.timeframe.value,
            )
            continue
        if client.can_trade:
            await _venue_close(client, record, contract_infix, ids, logger)
        await portfolio.upsert_positions(
            [_closed(record, mark, fee_rate, clock)]
        )
        closed += 1
        logger.warning(
            "position_flattened",
            symbol=record.symbol,
            position_id=record.position_id,
            mark=str(mark),
        )
    return closed


async def _emergency_mark(
    bars: SqliteBarRepository, exchange_id: str, record: PositionRecord
) -> Decimal | None:
    """The latest confirmed close for the position's series."""
    duration = record.timeframe.duration_ms
    latest = await bars.latest_open_time(
        exchange_id, record.symbol, record.timeframe
    )
    if latest is None:
        return None
    window = await bars.get_range(
        exchange_id,
        record.symbol,
        record.timeframe,
        start=Timestamp(epoch_ms=latest.epoch_ms - 3 * duration),
        end=Timestamp(epoch_ms=latest.epoch_ms + duration),
        closed_only=True,
    )
    if not window:
        return None
    return window[-1].close.value


async def _venue_close(
    client: ToobitTradingClient,
    record: PositionRecord,
    contract_infix: str,
    ids: IdProvider,
    logger: StructuredLogger,
) -> None:
    """Best-effort reduce-only market close at the venue."""
    params = close_params(
        contract=contract_symbol(record.symbol, contract_infix),
        direction=record.direction,
        quantity=record.quantity,
        client_order_id=client_order_id(ids.new_id()),
    )
    try:
        await client.place_order(params)
    except ApexError as error:
        logger.failure("flatten_venue_close_failed", error)


def _closed(
    record: PositionRecord, mark: Decimal, fee_rate: Decimal, clock: Clock
) -> PositionRecord:
    """The emergency ledger close at the mark (taker fees charged)."""
    long_position = record.direction == "long"
    favorable = (mark - record.entry) if long_position else (record.entry - mark)
    gross = favorable * record.quantity
    fees = fee_rate * (record.entry + mark) * record.quantity
    risk_per_unit = abs(record.entry - record.stop)
    realized_r = float(favorable / risk_per_unit) if risk_per_unit > 0 else 0.0
    return replace(
        record,
        status="closed",
        closed_at=clock.now(),
        exit_price=mark,
        realized_pnl=gross - fees,
        realized_r=realized_r,
        close_reason=CLOSE_REASON_FLATTENED,
    )

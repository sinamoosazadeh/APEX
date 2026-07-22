"""Execution store (Book II 12.29 Execution Audit).

No order or trade executes without a complete durable record: every
execution attempt persists with its decision anchor, order geometry,
fill outcome, costs and reason set; every fill persists exactly. The
audit allows full reconstruction of any execution (12.29) and feeds
the adaptive execution learning of Phase 11.
"""

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Final

from apex.core.enums import Timeframe
from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp

_EXECUTIONS: Final[str] = """
CREATE TABLE IF NOT EXISTS executions (
    execution_id    TEXT    NOT NULL,
    portfolio_id    TEXT    NOT NULL,
    exchange        TEXT    NOT NULL,
    symbol          TEXT    NOT NULL,
    timeframe       TEXT    NOT NULL,
    mode            TEXT    NOT NULL,
    signal_bar_ms   INTEGER NOT NULL,
    direction       TEXT    NOT NULL,
    order_type      TEXT    NOT NULL,
    client_order_id TEXT    NOT NULL,
    requested_at_ms INTEGER NOT NULL,
    completed_at_ms INTEGER,
    status          TEXT    NOT NULL,
    quantity        TEXT    NOT NULL,
    decision_price  TEXT    NOT NULL,
    fill_price      TEXT,
    fees            TEXT    NOT NULL,
    slippage        TEXT,
    stop            TEXT    NOT NULL,
    target          TEXT    NOT NULL,
    reasons         TEXT    NOT NULL,
    PRIMARY KEY (execution_id)
)
"""

_FILLS: Final[str] = """
CREATE TABLE IF NOT EXISTS execution_fills (
    execution_id      TEXT    NOT NULL,
    exchange_trade_id TEXT    NOT NULL,
    price             TEXT    NOT NULL,
    quantity          TEXT    NOT NULL,
    fee               TEXT    NOT NULL,
    liquidity_role    TEXT    NOT NULL,
    executed_at_ms    INTEGER NOT NULL,
    PRIMARY KEY (execution_id, exchange_trade_id)
)
"""

_INSERT_EXECUTION: Final[str] = """
INSERT INTO executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(execution_id) DO UPDATE SET
    completed_at_ms = excluded.completed_at_ms, status = excluded.status,
    fill_price = excluded.fill_price, fees = excluded.fees,
    slippage = excluded.slippage, reasons = excluded.reasons
"""

_INSERT_FILL: Final[str] = """
INSERT INTO execution_fills VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(execution_id, exchange_trade_id) DO UPDATE SET
    price = excluded.price, quantity = excluded.quantity, fee = excluded.fee
"""

STATUS_FILLED = "filled"
STATUS_UNFILLED = "unfilled"
STATUS_REJECTED = "rejected"
STATUS_FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionRecord:
    """One stored execution attempt."""

    execution_id: str
    portfolio_id: str
    exchange: str
    symbol: str
    timeframe: Timeframe
    mode: str
    signal_bar_time: Timestamp
    direction: str
    order_type: str
    client_order_id: str
    requested_at: Timestamp
    completed_at: Timestamp | None
    status: str
    quantity: Decimal
    decision_price: Decimal
    fill_price: Decimal | None
    fees: Decimal
    slippage: Decimal | None
    stop: Decimal
    target: Decimal
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FillRecord:
    """One stored fill."""

    execution_id: str
    exchange_trade_id: str
    price: Decimal
    quantity: Decimal
    fee: Decimal
    liquidity_role: str
    executed_at: Timestamp


class SqliteExecutionRepository:
    """Durable, idempotent execution audit."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("execution repository is already open", code="STO-080")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(_EXECUTIONS)
        connection.execute(_FILLS)
        connection.commit()
        return connection

    async def close(self) -> None:
        """Close the database; idempotent."""
        async with self._lock:
            if self._connection is not None:
                await asyncio.to_thread(self._connection.close)
                self._connection = None

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise StorageError("execution repository is not open", code="STO-081")
        return self._connection

    async def upsert_execution(self, record: ExecutionRecord) -> None:
        """Persist one execution attempt idempotently."""
        connection = self._require_connection()
        row = (
            record.execution_id, record.portfolio_id, record.exchange,
            record.symbol, record.timeframe.value, record.mode,
            record.signal_bar_time.epoch_ms, record.direction, record.order_type,
            record.client_order_id, record.requested_at.epoch_ms,
            record.completed_at.epoch_ms if record.completed_at else None,
            record.status, str(record.quantity), str(record.decision_price),
            str(record.fill_price) if record.fill_price is not None else None,
            str(record.fees),
            str(record.slippage) if record.slippage is not None else None,
            str(record.stop), str(record.target),
            json.dumps(list(record.reasons)),
        )

        def write() -> None:
            with connection:
                connection.execute(_INSERT_EXECUTION, row)

        async with self._lock:
            await asyncio.to_thread(write)

    async def upsert_fills(self, records: list[FillRecord]) -> int:
        """Persist fills idempotently; returns the number written."""
        if not records:
            return 0
        connection = self._require_connection()
        rows = [
            (
                record.execution_id, record.exchange_trade_id, str(record.price),
                str(record.quantity), str(record.fee), record.liquidity_role,
                record.executed_at.epoch_ms,
            )
            for record in records
        ]

        def write() -> int:
            with connection:
                connection.executemany(_INSERT_FILL, rows)
            return len(rows)

        async with self._lock:
            return await asyncio.to_thread(write)

    async def get_executions(
        self, portfolio_id: str, *, status: str | None = None
    ) -> list[ExecutionRecord]:
        """Stored executions, oldest request first."""
        connection = self._require_connection()
        query = "SELECT * FROM executions WHERE portfolio_id = ?"
        parameters: tuple[object, ...] = (portfolio_id,)
        if status is not None:
            query += " AND status = ?"
            parameters = (*parameters, status)
        query += " ORDER BY requested_at_ms"
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query, parameters).fetchall()
            )
        return [self._to_execution(row) for row in rows]

    async def get_fills(self, execution_id: str) -> list[FillRecord]:
        """Stored fills of one execution, oldest first."""
        connection = self._require_connection()
        query = (
            "SELECT * FROM execution_fills WHERE execution_id = ? "
            "ORDER BY executed_at_ms"
        )
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query, (execution_id,)).fetchall()
            )
        return [self._to_fill(row) for row in rows]

    def _to_execution(self, row: tuple[object, ...]) -> ExecutionRecord:
        (
            execution_id, portfolio_id, exchange, symbol, timeframe, mode,
            signal_bar_ms, direction, order_type, client_order_id,
            requested_at_ms, completed_at_ms, status, quantity, decision_price,
            fill_price, fees, slippage, stop, target, reasons,
        ) = row
        return ExecutionRecord(
            execution_id=str(execution_id),
            portfolio_id=str(portfolio_id),
            exchange=str(exchange),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            mode=str(mode),
            signal_bar_time=Timestamp(epoch_ms=int(str(signal_bar_ms))),
            direction=str(direction),
            order_type=str(order_type),
            client_order_id=str(client_order_id),
            requested_at=Timestamp(epoch_ms=int(str(requested_at_ms))),
            completed_at=(
                Timestamp(epoch_ms=int(str(completed_at_ms)))
                if completed_at_ms is not None
                else None
            ),
            status=str(status),
            quantity=Decimal(str(quantity)),
            decision_price=Decimal(str(decision_price)),
            fill_price=Decimal(str(fill_price)) if fill_price is not None else None,
            fees=Decimal(str(fees)),
            slippage=Decimal(str(slippage)) if slippage is not None else None,
            stop=Decimal(str(stop)),
            target=Decimal(str(target)),
            reasons=tuple(json.loads(str(reasons))),
        )

    def _to_fill(self, row: tuple[object, ...]) -> FillRecord:
        (
            execution_id, exchange_trade_id, price, quantity, fee,
            liquidity_role, executed_at_ms,
        ) = row
        return FillRecord(
            execution_id=str(execution_id),
            exchange_trade_id=str(exchange_trade_id),
            price=Decimal(str(price)),
            quantity=Decimal(str(quantity)),
            fee=Decimal(str(fee)),
            liquidity_role=str(liquidity_role),
            executed_at=Timestamp(epoch_ms=int(str(executed_at_ms))),
        )

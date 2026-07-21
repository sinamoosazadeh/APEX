"""Tick repository.

Durable trade-print storage (Book II ch. 6/16). Idempotent on the
exchange trade id (Toobit's stream provides a globally unique,
incrementing ``v``); ticks from sources without ids deduplicate on a
synthesized time/price/quantity/side key.
"""

import asyncio
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

from apex.core.enums import OrderSide
from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp
from apex.core.types import Price, Quantity
from apex.domain.market import Tick

_TICK_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS ticks (
    exchange       TEXT    NOT NULL,
    symbol         TEXT    NOT NULL,
    dedup_key      TEXT    NOT NULL,
    trade_id       TEXT,
    occurred_at_ms INTEGER NOT NULL,
    price          TEXT    NOT NULL,
    quantity       TEXT    NOT NULL,
    aggressor      TEXT    NOT NULL,
    PRIMARY KEY (exchange, symbol, dedup_key)
)
"""

_TICK_TIME_INDEX: Final[str] = """
CREATE INDEX IF NOT EXISTS idx_ticks_time
ON ticks (exchange, symbol, occurred_at_ms)
"""

_INSERT: Final[str] = """
INSERT INTO ticks (
    exchange, symbol, dedup_key, trade_id, occurred_at_ms,
    price, quantity, aggressor
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(exchange, symbol, dedup_key) DO NOTHING
"""


class SqliteTickRepository:
    """Durable, idempotent tick store with range queries."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("tick repository is already open", code="STO-020")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(_TICK_SCHEMA)
        connection.execute(_TICK_TIME_INDEX)
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
            raise StorageError("tick repository is not open", code="STO-021")
        return self._connection

    async def upsert(self, ticks: list[Tick]) -> int:
        """Persist ticks idempotently; returns rows actually inserted."""
        if not ticks:
            return 0
        connection = self._require_connection()
        rows: list[tuple[object, ...]] = [
            (
                tick.exchange,
                tick.symbol,
                tick.dedup_key(),
                tick.trade_id,
                tick.occurred_at.epoch_ms,
                str(tick.price.value),
                str(tick.quantity.value),
                tick.aggressor.value,
            )
            for tick in ticks
        ]
        async with self._lock:
            inserted = await asyncio.to_thread(self._upsert_blocking, connection, rows)
        return inserted

    @staticmethod
    def _upsert_blocking(
        connection: sqlite3.Connection,
        rows: list[tuple[object, ...]],
    ) -> int:
        before = connection.total_changes
        connection.executemany(_INSERT, rows)
        connection.commit()
        return connection.total_changes - before

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> Tick:
        exchange, symbol, trade_id, occurred_at_ms, price, quantity, aggressor = row
        return Tick(
            exchange=str(exchange),
            symbol=str(symbol),
            occurred_at=Timestamp(epoch_ms=int(occurred_at_ms)),
            price=Price(Decimal(str(price))),
            quantity=Quantity(Decimal(str(quantity))),
            aggressor=OrderSide(str(aggressor)),
            trade_id=str(trade_id) if trade_id is not None else None,
        )

    async def get_range(
        self,
        exchange: str,
        symbol: str,
        *,
        start: Timestamp,
        end: Timestamp,
        limit: int,
    ) -> list[Tick]:
        """Ticks with time in [start, end), oldest first, capped at limit."""
        if limit < 1:
            raise StorageError(
                "tick query limit must be >= 1",
                code="STO-022",
                details={"limit": limit},
            )
        connection = self._require_connection()
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(
                    "SELECT exchange, symbol, trade_id, occurred_at_ms, price, "
                    "quantity, aggressor FROM ticks "
                    "WHERE exchange = ? AND symbol = ? "
                    "AND occurred_at_ms >= ? AND occurred_at_ms < ? "
                    "ORDER BY occurred_at_ms ASC LIMIT ?",
                    (exchange, symbol, start.epoch_ms, end.epoch_ms, limit),
                ).fetchall()
            )
        return [self._from_row(row) for row in rows]

    async def count(self, exchange: str, symbol: str) -> int:
        """Number of stored ticks for a symbol."""
        connection = self._require_connection()
        async with self._lock:
            row = await asyncio.to_thread(
                lambda: connection.execute(
                    "SELECT COUNT(*) FROM ticks WHERE exchange = ? AND symbol = ?",
                    (exchange, symbol),
                ).fetchone()
            )
        return int(row[0])

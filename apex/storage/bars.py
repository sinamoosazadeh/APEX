"""Bar repository.

The market data platform's system of record (Book II ch. 6/16). Bars
are keyed by their natural identity (exchange, symbol, timeframe,
open time); ingestion is idempotent - re-ingesting the same bar
overwrites with the newest observation (a forming bar becoming closed).
"""

import asyncio
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

from apex.core.enums import Timeframe
from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp
from apex.core.types import FundingRate, Price, QualityScore, Spread, Volume
from apex.domain.market import Bar

_BAR_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS bars (
    exchange      TEXT    NOT NULL,
    symbol        TEXT    NOT NULL,
    timeframe     TEXT    NOT NULL,
    open_time_ms  INTEGER NOT NULL,
    open          TEXT    NOT NULL,
    high          TEXT    NOT NULL,
    low           TEXT    NOT NULL,
    close         TEXT    NOT NULL,
    volume        TEXT    NOT NULL,
    is_closed     INTEGER NOT NULL,
    trade_count   INTEGER,
    vwap          TEXT,
    spread        REAL,
    funding_rate  REAL,
    open_interest TEXT,
    quality       REAL    NOT NULL,
    content_hash  TEXT    NOT NULL,
    PRIMARY KEY (exchange, symbol, timeframe, open_time_ms)
)
"""

_INSERT: Final[str] = """
INSERT INTO bars (
    exchange, symbol, timeframe, open_time_ms, open, high, low, close,
    volume, is_closed, trade_count, vwap, spread, funding_rate,
    open_interest, quality, content_hash
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(exchange, symbol, timeframe, open_time_ms) DO UPDATE SET
    open = excluded.open, high = excluded.high, low = excluded.low,
    close = excluded.close, volume = excluded.volume,
    is_closed = excluded.is_closed, trade_count = excluded.trade_count,
    vwap = excluded.vwap, spread = excluded.spread,
    funding_rate = excluded.funding_rate,
    open_interest = excluded.open_interest, quality = excluded.quality,
    content_hash = excluded.content_hash
"""

_SELECT_COLUMNS: Final[str] = (
    "exchange, symbol, timeframe, open_time_ms, open, high, low, close, "
    "volume, is_closed, trade_count, vwap, spread, funding_rate, "
    "open_interest, quality"
)


class SqliteBarRepository:
    """Durable, idempotent bar store with range queries."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("bar repository is already open", code="STO-010")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(_BAR_SCHEMA)
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
            raise StorageError("bar repository is not open", code="STO-011")
        return self._connection

    async def upsert(self, bars: list[Bar]) -> int:
        """Persist bars idempotently; returns the number written."""
        if not bars:
            return 0
        connection = self._require_connection()
        rows = [self._to_row(bar) for bar in bars]
        async with self._lock:
            await asyncio.to_thread(self._upsert_blocking, connection, rows)
        return len(rows)

    @staticmethod
    def _upsert_blocking(
        connection: sqlite3.Connection,
        rows: list[tuple[object, ...]],
    ) -> None:
        connection.executemany(_INSERT, rows)
        connection.commit()

    @staticmethod
    def _to_row(bar: Bar) -> tuple[object, ...]:
        return (
            bar.exchange,
            bar.symbol,
            bar.timeframe.value,
            bar.open_time.epoch_ms,
            str(bar.open.value),
            str(bar.high.value),
            str(bar.low.value),
            str(bar.close.value),
            str(bar.volume.value),
            1 if bar.is_closed else 0,
            bar.trade_count,
            str(bar.vwap.value) if bar.vwap else None,
            bar.spread.value if bar.spread else None,
            bar.funding_rate.value if bar.funding_rate else None,
            str(bar.open_interest.value) if bar.open_interest else None,
            bar.quality.value,
            bar.content_hash(),
        )

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> Bar:
        (
            exchange, symbol, timeframe, open_time_ms, open_, high, low,
            close, volume, is_closed, trade_count, vwap, spread,
            funding_rate, open_interest, quality,
        ) = row
        return Bar(
            exchange=str(exchange),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            open_time=Timestamp(epoch_ms=int(open_time_ms)),
            open=Price(Decimal(str(open_))),
            high=Price(Decimal(str(high))),
            low=Price(Decimal(str(low))),
            close=Price(Decimal(str(close))),
            volume=Volume(Decimal(str(volume))),
            is_closed=bool(is_closed),
            trade_count=int(trade_count) if trade_count is not None else None,
            vwap=Price(Decimal(str(vwap))) if vwap is not None else None,
            spread=Spread(float(spread)) if spread is not None else None,
            funding_rate=(
                FundingRate(float(funding_rate)) if funding_rate is not None else None
            ),
            open_interest=(
                Volume(Decimal(str(open_interest))) if open_interest is not None else None
            ),
            quality=QualityScore(float(quality)),
        )

    async def get_range(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
        closed_only: bool = False,
    ) -> list[Bar]:
        """Bars with open time in [start, end), oldest first."""
        connection = self._require_connection()
        query = (
            f"SELECT {_SELECT_COLUMNS} FROM bars "
            "WHERE exchange = ? AND symbol = ? AND timeframe = ? "
            "AND open_time_ms >= ? AND open_time_ms < ? "
        )
        if closed_only:
            query += "AND is_closed = 1 "
        query += "ORDER BY open_time_ms ASC"
        parameters = (exchange, symbol, timeframe.value, start.epoch_ms, end.epoch_ms)
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query, parameters).fetchall()
            )
        return [self._from_row(row) for row in rows]

    async def latest_open_time(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
    ) -> Timestamp | None:
        """Open time of the most recent stored bar, if any."""
        connection = self._require_connection()
        async with self._lock:
            row = await asyncio.to_thread(
                lambda: connection.execute(
                    "SELECT MAX(open_time_ms) FROM bars "
                    "WHERE exchange = ? AND symbol = ? AND timeframe = ?",
                    (exchange, symbol, timeframe.value),
                ).fetchone()
            )
        if row is None or row[0] is None:
            return None
        return Timestamp(epoch_ms=int(row[0]))

    async def count(self, exchange: str, symbol: str, timeframe: Timeframe) -> int:
        """Number of stored bars for a series."""
        connection = self._require_connection()
        async with self._lock:
            row = await asyncio.to_thread(
                lambda: connection.execute(
                    "SELECT COUNT(*) FROM bars "
                    "WHERE exchange = ? AND symbol = ? AND timeframe = ?",
                    (exchange, symbol, timeframe.value),
                ).fetchone()
            )
        return int(row[0])

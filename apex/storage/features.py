"""Feature store (Book II 29.10).

The durable record of every computed feature value, keyed by its
series anchor (exchange, symbol, timeframe, bar open time) and name.
Recomputation is idempotent - same anchor, same name, newest value
wins - and vector queries assemble everything known about one bar.
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Any, Final

from apex.core.enums import Timeframe
from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp
from apex.core.types import Confidence, Reliability, Weight
from apex.domain.feature import Feature

_FEATURE_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS features (
    exchange       TEXT    NOT NULL,
    symbol         TEXT    NOT NULL,
    timeframe      TEXT    NOT NULL,
    bar_open_ms    INTEGER NOT NULL,
    name           TEXT    NOT NULL,
    family         TEXT    NOT NULL,
    value          REAL    NOT NULL,
    normalized     REAL    NOT NULL,
    weight         REAL    NOT NULL,
    confidence     REAL    NOT NULL,
    reliability    REAL    NOT NULL,
    source         TEXT    NOT NULL,
    computed_at_ms INTEGER NOT NULL,
    PRIMARY KEY (exchange, symbol, timeframe, bar_open_ms, name)
)
"""

_INSERT: Final[str] = """
INSERT INTO features (
    exchange, symbol, timeframe, bar_open_ms, name, family, value,
    normalized, weight, confidence, reliability, source, computed_at_ms
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(exchange, symbol, timeframe, bar_open_ms, name) DO UPDATE SET
    family = excluded.family, value = excluded.value,
    normalized = excluded.normalized, weight = excluded.weight,
    confidence = excluded.confidence, reliability = excluded.reliability,
    source = excluded.source, computed_at_ms = excluded.computed_at_ms
"""

_SELECT: Final[str] = (
    "SELECT exchange, symbol, timeframe, bar_open_ms, name, family, value, "
    "normalized, weight, confidence, reliability, source, computed_at_ms "
    "FROM features"
)


class SqliteFeatureRepository:
    """Durable, idempotent feature store with anchor and series queries."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("feature repository is already open", code="STO-030")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(_FEATURE_SCHEMA)
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
            raise StorageError("feature repository is not open", code="STO-031")
        return self._connection

    async def upsert(self, features: list[Feature]) -> int:
        """Persist features idempotently; returns the number written."""
        if not features:
            return 0
        connection = self._require_connection()
        rows: list[tuple[object, ...]] = [
            (
                f.exchange,
                f.symbol,
                f.timeframe.value,
                f.bar_open_time.epoch_ms,
                f.name,
                f.family,
                f.value,
                f.normalized_value,
                f.weight.value,
                f.confidence.value,
                f.reliability.value,
                f.source,
                f.computed_at.epoch_ms,
            )
            for f in features
        ]
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
    def _from_row(row: tuple[Any, ...]) -> Feature:
        (
            exchange, symbol, timeframe, bar_open_ms, name, family, value,
            normalized, weight, confidence, reliability, source, computed_at_ms,
        ) = row
        return Feature(
            created_at=Timestamp(epoch_ms=int(computed_at_ms)),
            exchange=str(exchange),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            bar_open_time=Timestamp(epoch_ms=int(bar_open_ms)),
            name=str(name),
            family=str(family),
            value=float(value),
            normalized_value=float(normalized),
            weight=Weight(float(weight)),
            confidence=Confidence(float(confidence)),
            reliability=Reliability(float(reliability)),
            source=str(source),
            computed_at=Timestamp(epoch_ms=int(computed_at_ms)),
        )

    async def get_vector(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        bar_open_time: Timestamp,
    ) -> list[Feature]:
        """Every stored feature for one bar anchor, ordered by name."""
        connection = self._require_connection()
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(
                    f"{_SELECT} WHERE exchange = ? AND symbol = ? AND timeframe = ? "
                    "AND bar_open_ms = ? ORDER BY name ASC",
                    (exchange, symbol, timeframe.value, bar_open_time.epoch_ms),
                ).fetchall()
            )
        return [self._from_row(row) for row in rows]

    async def get_series(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        name: str,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> list[Feature]:
        """One feature across bars in [start, end), oldest first."""
        connection = self._require_connection()
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(
                    f"{_SELECT} WHERE exchange = ? AND symbol = ? AND timeframe = ? "
                    "AND name = ? AND bar_open_ms >= ? AND bar_open_ms < ? "
                    "ORDER BY bar_open_ms ASC",
                    (
                        exchange,
                        symbol,
                        timeframe.value,
                        name,
                        start.epoch_ms,
                        end.epoch_ms,
                    ),
                ).fetchall()
            )
        return [self._from_row(row) for row in rows]

    async def count(self, exchange: str, symbol: str, timeframe: Timeframe) -> int:
        """Number of stored feature values for a series."""
        connection = self._require_connection()
        async with self._lock:
            row = await asyncio.to_thread(
                lambda: connection.execute(
                    "SELECT COUNT(*) FROM features "
                    "WHERE exchange = ? AND symbol = ? AND timeframe = ?",
                    (exchange, symbol, timeframe.value),
                ).fetchone()
            )
        return int(row[0])

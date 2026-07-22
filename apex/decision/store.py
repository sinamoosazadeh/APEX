"""Decision store (Book I ch. 9: every decision is auditable).

The durable record of every kernel outcome that matters: fired signals
(with their full entry context) and vetoed readiness (with the failed
gates). Keyed by the series anchor and side; recomputation is
idempotent.
"""

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from apex.core.enums import Timeframe
from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp

_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS decisions (
    exchange       TEXT    NOT NULL,
    symbol         TEXT    NOT NULL,
    timeframe      TEXT    NOT NULL,
    bar_open_ms    INTEGER NOT NULL,
    action         TEXT    NOT NULL,
    direction      TEXT    NOT NULL,
    setup          TEXT    NOT NULL,
    probability    REAL    NOT NULL,
    uncertainty    REAL    NOT NULL,
    expected_r     REAL    NOT NULL,
    contributors   INTEGER NOT NULL,
    failed_gates   TEXT    NOT NULL,
    entry          REAL,
    stop           REAL,
    targets        TEXT,
    computed_at_ms INTEGER NOT NULL,
    PRIMARY KEY (exchange, symbol, timeframe, bar_open_ms)
)
"""

_INSERT: Final[str] = """
INSERT INTO decisions (
    exchange, symbol, timeframe, bar_open_ms, action, direction, setup,
    probability, uncertainty, expected_r, contributors, failed_gates,
    entry, stop, targets, computed_at_ms
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(exchange, symbol, timeframe, bar_open_ms) DO UPDATE SET
    action = excluded.action, direction = excluded.direction,
    setup = excluded.setup, probability = excluded.probability,
    uncertainty = excluded.uncertainty, expected_r = excluded.expected_r,
    contributors = excluded.contributors, failed_gates = excluded.failed_gates,
    entry = excluded.entry, stop = excluded.stop, targets = excluded.targets,
    computed_at_ms = excluded.computed_at_ms
"""

_SELECT: Final[str] = (
    "SELECT exchange, symbol, timeframe, bar_open_ms, action, direction, "
    "setup, probability, uncertainty, expected_r, contributors, failed_gates, "
    "entry, stop, targets, computed_at_ms FROM decisions"
)


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionRecord:
    """One stored kernel outcome."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    bar_open_time: Timestamp
    action: str
    direction: str
    setup: str
    probability: float
    uncertainty: float
    expected_r: float
    contributors: int
    failed_gates: tuple[str, ...]
    entry: float | None
    stop: float | None
    targets: tuple[float, ...]
    computed_at: Timestamp


class SqliteDecisionRepository:
    """Durable, idempotent decision store with range queries."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("decision repository is already open", code="STO-050")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(_SCHEMA)
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
            raise StorageError("decision repository is not open", code="STO-051")
        return self._connection

    async def upsert(self, records: list[DecisionRecord]) -> int:
        """Persist decisions idempotently; returns the number written."""
        if not records:
            return 0
        connection = self._require_connection()
        rows = [
            (
                record.exchange, record.symbol, record.timeframe.value,
                record.bar_open_time.epoch_ms, record.action, record.direction,
                record.setup, record.probability, record.uncertainty,
                record.expected_r, record.contributors,
                json.dumps(list(record.failed_gates)), record.entry, record.stop,
                json.dumps(list(record.targets)), record.computed_at.epoch_ms,
            )
            for record in records
        ]

        def write() -> int:
            with connection:
                connection.executemany(_INSERT, rows)
            return len(rows)

        async with self._lock:
            return await asyncio.to_thread(write)

    async def get_range(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> list[DecisionRecord]:
        """Decisions with bar open time in [start, end), oldest first."""
        connection = self._require_connection()
        query = (
            f"{_SELECT} WHERE exchange = ? AND symbol = ? AND timeframe = ? "
            "AND bar_open_ms >= ? AND bar_open_ms < ? ORDER BY bar_open_ms"
        )
        parameters = (exchange, symbol, timeframe.value, start.epoch_ms, end.epoch_ms)
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query, parameters).fetchall()
            )
        return [self._to_record(row) for row in rows]

    async def count(
        self, exchange: str, symbol: str, timeframe: Timeframe, *, action: str | None = None
    ) -> int:
        """Stored decisions for one series, optionally by action."""
        connection = self._require_connection()
        query = (
            "SELECT COUNT(*) FROM decisions WHERE exchange = ? AND symbol = ? "
            "AND timeframe = ?"
        )
        parameters: tuple[object, ...] = (exchange, symbol, timeframe.value)
        if action is not None:
            query += " AND action = ?"
            parameters = (*parameters, action)
        async with self._lock:
            row = await asyncio.to_thread(
                lambda: connection.execute(query, parameters).fetchone()
            )
        return int(row[0])

    def _to_record(self, row: tuple[object, ...]) -> DecisionRecord:
        (
            exchange, symbol, timeframe, bar_open_ms, action, direction, setup,
            probability, uncertainty, expected_r, contributors, failed_gates,
            entry, stop, targets, computed_at_ms,
        ) = row
        return DecisionRecord(
            exchange=str(exchange),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            bar_open_time=Timestamp(epoch_ms=int(str(bar_open_ms))),
            action=str(action),
            direction=str(direction),
            setup=str(setup),
            probability=float(str(probability)),
            uncertainty=float(str(uncertainty)),
            expected_r=float(str(expected_r)),
            contributors=int(str(contributors)),
            failed_gates=tuple(json.loads(str(failed_gates))),
            entry=float(str(entry)) if entry is not None else None,
            stop=float(str(stop)) if stop is not None else None,
            targets=tuple(json.loads(str(targets))) if targets is not None else (),
            computed_at=Timestamp(epoch_ms=int(str(computed_at_ms))),
        )

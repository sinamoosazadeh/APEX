"""Probability assessment store (Book II ch. 8).

The durable record of every per-side confluence assessment, keyed by
its series anchor (exchange, symbol, timeframe, bar open time) and
side. Recomputation is idempotent: same anchor, same side, newest
assessment wins.
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
CREATE TABLE IF NOT EXISTS assessments (
    exchange       TEXT    NOT NULL,
    symbol         TEXT    NOT NULL,
    timeframe      TEXT    NOT NULL,
    bar_open_ms    INTEGER NOT NULL,
    side           TEXT    NOT NULL,
    probability    REAL    NOT NULL,
    lower_bound    REAL    NOT NULL,
    upper_bound    REAL    NOT NULL,
    entropy        REAL    NOT NULL,
    raw_score      REAL    NOT NULL,
    sample_size    INTEGER NOT NULL,
    channels       TEXT    NOT NULL,
    computed_at_ms INTEGER NOT NULL,
    PRIMARY KEY (exchange, symbol, timeframe, bar_open_ms, side)
)
"""

_INSERT: Final[str] = """
INSERT INTO assessments (
    exchange, symbol, timeframe, bar_open_ms, side, probability,
    lower_bound, upper_bound, entropy, raw_score, sample_size,
    channels, computed_at_ms
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(exchange, symbol, timeframe, bar_open_ms, side) DO UPDATE SET
    probability = excluded.probability, lower_bound = excluded.lower_bound,
    upper_bound = excluded.upper_bound, entropy = excluded.entropy,
    raw_score = excluded.raw_score, sample_size = excluded.sample_size,
    channels = excluded.channels, computed_at_ms = excluded.computed_at_ms
"""

_SELECT: Final[str] = (
    "SELECT exchange, symbol, timeframe, bar_open_ms, side, probability, "
    "lower_bound, upper_bound, entropy, raw_score, sample_size, channels, "
    "computed_at_ms FROM assessments"
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AssessmentRecord:
    """One stored per-side assessment row."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    bar_open_time: Timestamp
    side: str
    probability: float
    lower_bound: float
    upper_bound: float
    entropy: float
    raw_score: float
    sample_size: int
    channels: dict[str, float]
    computed_at: Timestamp


class SqliteProbabilityRepository:
    """Durable, idempotent assessment store with range queries."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("probability repository is already open", code="STO-040")
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
            raise StorageError("probability repository is not open", code="STO-041")
        return self._connection

    async def upsert(self, records: list[AssessmentRecord]) -> int:
        """Persist assessments idempotently; returns the number written."""
        if not records:
            return 0
        connection = self._require_connection()
        rows = [
            (
                record.exchange,
                record.symbol,
                record.timeframe.value,
                record.bar_open_time.epoch_ms,
                record.side,
                record.probability,
                record.lower_bound,
                record.upper_bound,
                record.entropy,
                record.raw_score,
                record.sample_size,
                json.dumps(record.channels, sort_keys=True),
                record.computed_at.epoch_ms,
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
    ) -> list[AssessmentRecord]:
        """Assessments with bar open time in [start, end), oldest first."""
        connection = self._require_connection()
        query = (
            f"{_SELECT} WHERE exchange = ? AND symbol = ? AND timeframe = ? "
            "AND bar_open_ms >= ? AND bar_open_ms < ? ORDER BY bar_open_ms, side"
        )
        parameters = (
            exchange, symbol, timeframe.value, start.epoch_ms, end.epoch_ms,
        )
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query, parameters).fetchall()
            )
        return [self._to_record(row) for row in rows]

    async def count(self, exchange: str, symbol: str, timeframe: Timeframe) -> int:
        """Stored assessment rows for one series."""
        connection = self._require_connection()
        query = (
            "SELECT COUNT(*) FROM assessments WHERE exchange = ? AND symbol = ? "
            "AND timeframe = ?"
        )
        async with self._lock:
            row = await asyncio.to_thread(
                lambda: connection.execute(
                    query, (exchange, symbol, timeframe.value)
                ).fetchone()
            )
        return int(row[0])

    def _to_record(self, row: tuple[object, ...]) -> AssessmentRecord:
        (
            exchange, symbol, timeframe, bar_open_ms, side, probability,
            lower_bound, upper_bound, entropy, raw_score, sample_size,
            channels, computed_at_ms,
        ) = row
        return AssessmentRecord(
            exchange=str(exchange),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            bar_open_time=Timestamp(epoch_ms=int(str(bar_open_ms))),
            side=str(side),
            probability=float(str(probability)),
            lower_bound=float(str(lower_bound)),
            upper_bound=float(str(upper_bound)),
            entropy=float(str(entropy)),
            raw_score=float(str(raw_score)),
            sample_size=int(str(sample_size)),
            channels=dict(json.loads(str(channels))),
            computed_at=Timestamp(epoch_ms=int(str(computed_at_ms))),
        )

"""Portfolio store (Book II 13.26 Portfolio Memory).

Durable, idempotent SQLite persistence of the fold's outputs:
positions (final lifecycle state, keyed by their entry bar), portfolio
snapshots at every state change, and governed rejections with their
reason sets. Rebuilds clear the portfolio scope first - the store
always mirrors one deterministic reconstruction of the decision
stream (Book II 21.5/21.27).

Money-like magnitudes persist as exact strings (Decimal round-trip);
R multiples and fractions are REAL.
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
from apex.portfolio.account import TradeStatistics

_POSITIONS: Final[str] = """
CREATE TABLE IF NOT EXISTS portfolio_positions (
    portfolio_id   TEXT    NOT NULL,
    exchange       TEXT    NOT NULL,
    symbol         TEXT    NOT NULL,
    timeframe      TEXT    NOT NULL,
    entry_bar_ms   INTEGER NOT NULL,
    position_id    TEXT    NOT NULL,
    lineage_id     TEXT    NOT NULL,
    direction      TEXT    NOT NULL,
    quantity       TEXT    NOT NULL,
    entry          TEXT    NOT NULL,
    stop           TEXT    NOT NULL,
    target         TEXT    NOT NULL,
    risk_amount    TEXT    NOT NULL,
    opened_at_ms   INTEGER NOT NULL,
    status         TEXT    NOT NULL,
    closed_at_ms   INTEGER,
    exit_price     TEXT,
    realized_pnl   TEXT,
    realized_r     REAL,
    close_reason   TEXT,
    PRIMARY KEY (portfolio_id, exchange, symbol, timeframe, entry_bar_ms)
)
"""

_SNAPSHOTS: Final[str] = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    portfolio_id   TEXT    NOT NULL,
    as_of_ms       INTEGER NOT NULL,
    equity         TEXT    NOT NULL,
    cash           TEXT    NOT NULL,
    gross_exposure TEXT    NOT NULL,
    unrealized_pnl TEXT    NOT NULL,
    realized_pnl   TEXT    NOT NULL,
    drawdown       REAL    NOT NULL,
    open_positions INTEGER NOT NULL,
    PRIMARY KEY (portfolio_id, as_of_ms)
)
"""

_REJECTIONS: Final[str] = """
CREATE TABLE IF NOT EXISTS portfolio_rejections (
    portfolio_id   TEXT    NOT NULL,
    exchange       TEXT    NOT NULL,
    symbol         TEXT    NOT NULL,
    timeframe      TEXT    NOT NULL,
    bar_open_ms    INTEGER NOT NULL,
    reasons        TEXT    NOT NULL,
    PRIMARY KEY (portfolio_id, exchange, symbol, timeframe, bar_open_ms)
)
"""

_INSERT_POSITION: Final[str] = """
INSERT INTO portfolio_positions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(portfolio_id, exchange, symbol, timeframe, entry_bar_ms) DO UPDATE SET
    position_id = excluded.position_id, lineage_id = excluded.lineage_id,
    direction = excluded.direction, quantity = excluded.quantity,
    entry = excluded.entry, stop = excluded.stop, target = excluded.target,
    risk_amount = excluded.risk_amount, opened_at_ms = excluded.opened_at_ms,
    status = excluded.status, closed_at_ms = excluded.closed_at_ms,
    exit_price = excluded.exit_price, realized_pnl = excluded.realized_pnl,
    realized_r = excluded.realized_r, close_reason = excluded.close_reason
"""

_INSERT_SNAPSHOT: Final[str] = """
INSERT INTO portfolio_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(portfolio_id, as_of_ms) DO UPDATE SET
    equity = excluded.equity, cash = excluded.cash,
    gross_exposure = excluded.gross_exposure,
    unrealized_pnl = excluded.unrealized_pnl,
    realized_pnl = excluded.realized_pnl, drawdown = excluded.drawdown,
    open_positions = excluded.open_positions
"""

_INSERT_REJECTION: Final[str] = """
INSERT INTO portfolio_rejections VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(portfolio_id, exchange, symbol, timeframe, bar_open_ms) DO UPDATE SET
    reasons = excluded.reasons
"""


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionRecord:
    """One stored position in its final lifecycle state."""

    portfolio_id: str
    exchange: str
    symbol: str
    timeframe: Timeframe
    entry_bar_time: Timestamp
    position_id: str
    lineage_id: str
    direction: str
    quantity: Decimal
    entry: Decimal
    stop: Decimal
    target: Decimal
    risk_amount: Decimal
    opened_at: Timestamp
    status: str
    closed_at: Timestamp | None
    exit_price: Decimal | None
    realized_pnl: Decimal | None
    realized_r: float | None
    close_reason: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotRecord:
    """One stored portfolio snapshot."""

    portfolio_id: str
    as_of: Timestamp
    equity: Decimal
    cash: Decimal
    gross_exposure: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    drawdown: float
    open_positions: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RejectionRecord:
    """One stored governed rejection."""

    portfolio_id: str
    exchange: str
    symbol: str
    timeframe: Timeframe
    bar_open_time: Timestamp
    reasons: tuple[str, ...]


class SqlitePortfolioRepository:
    """Durable portfolio memory with idempotent rebuild semantics."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("portfolio repository is already open", code="STO-070")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(_POSITIONS)
        connection.execute(_SNAPSHOTS)
        connection.execute(_REJECTIONS)
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
            raise StorageError("portfolio repository is not open", code="STO-071")
        return self._connection

    async def clear(self, portfolio_id: str) -> None:
        """Drop one portfolio's stored state (rebuild semantics)."""
        connection = self._require_connection()

        def wipe() -> None:
            with connection:
                for table in (
                    "portfolio_positions",
                    "portfolio_snapshots",
                    "portfolio_rejections",
                ):
                    connection.execute(
                        f"DELETE FROM {table} WHERE portfolio_id = ?",
                        (portfolio_id,),
                    )

        async with self._lock:
            await asyncio.to_thread(wipe)

    async def upsert_positions(self, records: list[PositionRecord]) -> int:
        """Persist positions idempotently; returns the number written."""
        if not records:
            return 0
        connection = self._require_connection()
        rows = [
            (
                record.portfolio_id, record.exchange, record.symbol,
                record.timeframe.value, record.entry_bar_time.epoch_ms,
                record.position_id, record.lineage_id, record.direction,
                str(record.quantity), str(record.entry), str(record.stop),
                str(record.target), str(record.risk_amount),
                record.opened_at.epoch_ms, record.status,
                record.closed_at.epoch_ms if record.closed_at else None,
                str(record.exit_price) if record.exit_price is not None else None,
                str(record.realized_pnl) if record.realized_pnl is not None else None,
                record.realized_r, record.close_reason,
            )
            for record in records
        ]

        def write() -> int:
            with connection:
                connection.executemany(_INSERT_POSITION, rows)
            return len(rows)

        async with self._lock:
            return await asyncio.to_thread(write)

    async def upsert_snapshots(self, records: list[SnapshotRecord]) -> int:
        """Persist snapshots idempotently; returns the number written."""
        if not records:
            return 0
        connection = self._require_connection()
        rows = [
            (
                record.portfolio_id, record.as_of.epoch_ms, str(record.equity),
                str(record.cash), str(record.gross_exposure),
                str(record.unrealized_pnl), str(record.realized_pnl),
                record.drawdown, record.open_positions,
            )
            for record in records
        ]

        def write() -> int:
            with connection:
                connection.executemany(_INSERT_SNAPSHOT, rows)
            return len(rows)

        async with self._lock:
            return await asyncio.to_thread(write)

    async def upsert_rejections(self, records: list[RejectionRecord]) -> int:
        """Persist rejections idempotently; returns the number written."""
        if not records:
            return 0
        connection = self._require_connection()
        rows = [
            (
                record.portfolio_id, record.exchange, record.symbol,
                record.timeframe.value, record.bar_open_time.epoch_ms,
                json.dumps(list(record.reasons)),
            )
            for record in records
        ]

        def write() -> int:
            with connection:
                connection.executemany(_INSERT_REJECTION, rows)
            return len(rows)

        async with self._lock:
            return await asyncio.to_thread(write)

    async def get_positions(
        self, portfolio_id: str, *, status: str | None = None
    ) -> list[PositionRecord]:
        """Stored positions, oldest entry first, optionally by status."""
        connection = self._require_connection()
        query = "SELECT * FROM portfolio_positions WHERE portfolio_id = ?"
        parameters: tuple[object, ...] = (portfolio_id,)
        if status is not None:
            query += " AND status = ?"
            parameters = (*parameters, status)
        query += " ORDER BY entry_bar_ms, symbol"
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query, parameters).fetchall()
            )
        return [self._to_position(row) for row in rows]

    async def get_snapshots(self, portfolio_id: str) -> list[SnapshotRecord]:
        """Stored snapshots, oldest first."""
        connection = self._require_connection()
        query = (
            "SELECT * FROM portfolio_snapshots WHERE portfolio_id = ? "
            "ORDER BY as_of_ms"
        )
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query, (portfolio_id,)).fetchall()
            )
        return [self._to_snapshot(row) for row in rows]

    async def get_rejections(self, portfolio_id: str) -> list[RejectionRecord]:
        """Stored rejections, oldest first."""
        connection = self._require_connection()
        query = (
            "SELECT * FROM portfolio_rejections WHERE portfolio_id = ? "
            "ORDER BY bar_open_ms, symbol"
        )
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query, (portfolio_id,)).fetchall()
            )
        return [self._to_rejection(row) for row in rows]

    async def statistics(self, portfolio_id: str) -> TradeStatistics:
        """Closed-trade statistics in close order (Kelly inputs)."""
        closed = [
            record
            for record in await self.get_positions(portfolio_id, status="closed")
            if record.realized_r is not None and record.closed_at is not None
        ]
        closed.sort(key=lambda record: record.closed_at.epoch_ms if record.closed_at else 0)
        wins = sum(1 for record in closed if record.close_reason == "target")
        losses = len(closed) - wins
        win_r = sum(
            record.realized_r or 0.0
            for record in closed
            if record.close_reason == "target"
        )
        loss_r = sum(
            record.realized_r or 0.0
            for record in closed
            if record.close_reason != "target"
        )
        streak = 0
        for record in reversed(closed):
            if record.close_reason == "target":
                break
            streak += 1
        return TradeStatistics(
            trades=len(closed),
            wins=wins,
            losses=losses,
            r_sum=sum(record.realized_r or 0.0 for record in closed),
            average_win_r=win_r / wins if wins else 0.0,
            average_loss_r=loss_r / losses if losses else 0.0,
            consecutive_losses=streak,
        )

    def _to_position(self, row: tuple[object, ...]) -> PositionRecord:
        (
            portfolio_id, exchange, symbol, timeframe, entry_bar_ms, position_id,
            lineage_id, direction, quantity, entry, stop, target, risk_amount,
            opened_at_ms, status, closed_at_ms, exit_price, realized_pnl,
            realized_r, close_reason,
        ) = row
        return PositionRecord(
            portfolio_id=str(portfolio_id),
            exchange=str(exchange),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            entry_bar_time=Timestamp(epoch_ms=int(str(entry_bar_ms))),
            position_id=str(position_id),
            lineage_id=str(lineage_id),
            direction=str(direction),
            quantity=Decimal(str(quantity)),
            entry=Decimal(str(entry)),
            stop=Decimal(str(stop)),
            target=Decimal(str(target)),
            risk_amount=Decimal(str(risk_amount)),
            opened_at=Timestamp(epoch_ms=int(str(opened_at_ms))),
            status=str(status),
            closed_at=(
                Timestamp(epoch_ms=int(str(closed_at_ms)))
                if closed_at_ms is not None
                else None
            ),
            exit_price=Decimal(str(exit_price)) if exit_price is not None else None,
            realized_pnl=(
                Decimal(str(realized_pnl)) if realized_pnl is not None else None
            ),
            realized_r=float(str(realized_r)) if realized_r is not None else None,
            close_reason=str(close_reason) if close_reason is not None else None,
        )

    def _to_snapshot(self, row: tuple[object, ...]) -> SnapshotRecord:
        (
            portfolio_id, as_of_ms, equity, cash, gross_exposure,
            unrealized, realized, drawdown, open_positions,
        ) = row
        return SnapshotRecord(
            portfolio_id=str(portfolio_id),
            as_of=Timestamp(epoch_ms=int(str(as_of_ms))),
            equity=Decimal(str(equity)),
            cash=Decimal(str(cash)),
            gross_exposure=Decimal(str(gross_exposure)),
            unrealized_pnl=Decimal(str(unrealized)),
            realized_pnl=Decimal(str(realized)),
            drawdown=float(str(drawdown)),
            open_positions=int(str(open_positions)),
        )

    def _to_rejection(self, row: tuple[object, ...]) -> RejectionRecord:
        portfolio_id, exchange, symbol, timeframe, bar_open_ms, reasons = row
        return RejectionRecord(
            portfolio_id=str(portfolio_id),
            exchange=str(exchange),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            bar_open_time=Timestamp(epoch_ms=int(str(bar_open_ms))),
            reasons=tuple(json.loads(str(reasons))),
        )

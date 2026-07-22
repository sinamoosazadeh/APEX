"""Research store (Book II 14.21/23.19; Book V part 7 persistence).

One durable home for the research platform's records:

- **jobs**: the orchestrator's optimization queue with the part 7
  status lifecycle and retry accounting.
- **active_versions**: the runtime-injection pointers - which
  accepted artifact each (symbol, timeframe, kind) currently runs;
  history rows make rollback a repoint, never a delete.
- **experiments**: the registry (23.19 reproducibility stamps -
  seed, dataset window, versions - plus statistical results).
- **learning_artifacts**: versioned learning states per series.
"""

import asyncio
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from apex.core.enums import Timeframe
from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp

_SCHEMA: Final[tuple[str, ...]] = (
    """
    CREATE TABLE IF NOT EXISTS research_jobs (
        job_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol         TEXT    NOT NULL,
        timeframe      TEXT    NOT NULL,
        kind           TEXT    NOT NULL,
        priority       INTEGER NOT NULL,
        status         TEXT    NOT NULL,
        attempts       INTEGER NOT NULL DEFAULT 0,
        seed           INTEGER NOT NULL,
        window_bars    INTEGER NOT NULL,
        created_at_ms  INTEGER NOT NULL,
        completed_at_ms INTEGER,
        result         TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS active_versions (
        symbol         TEXT    NOT NULL,
        timeframe      TEXT    NOT NULL,
        kind           TEXT    NOT NULL,
        sequence       INTEGER NOT NULL,
        artifact_path  TEXT    NOT NULL,
        activated_at_ms INTEGER NOT NULL,
        active         INTEGER NOT NULL,
        PRIMARY KEY (symbol, timeframe, kind, sequence)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS experiments (
        experiment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis     TEXT    NOT NULL,
        symbol         TEXT    NOT NULL,
        timeframe      TEXT    NOT NULL,
        window_start_ms INTEGER NOT NULL,
        window_end_ms  INTEGER NOT NULL,
        seed           INTEGER NOT NULL,
        project_version TEXT   NOT NULL,
        baseline       TEXT    NOT NULL,
        candidate      TEXT    NOT NULL,
        p_value        REAL,
        effect_size    REAL,
        status         TEXT    NOT NULL,
        created_at_ms  INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learning_artifacts (
        symbol         TEXT    NOT NULL,
        timeframe      TEXT    NOT NULL,
        version        INTEGER NOT NULL,
        payload        TEXT    NOT NULL,
        outcomes       INTEGER NOT NULL,
        created_at_ms  INTEGER NOT NULL,
        PRIMARY KEY (symbol, timeframe, version)
    )
    """,
)

JOB_PENDING: Final[str] = "pending"
JOB_RUNNING: Final[str] = "running"
JOB_COMPLETED: Final[str] = "completed"
JOB_FAILED: Final[str] = "failed"

EXPERIMENT_VALIDATED: Final[str] = "validated"
EXPERIMENT_REJECTED: Final[str] = "rejected"


@dataclass(frozen=True, slots=True, kw_only=True)
class ResearchJob:
    """One queued optimization job (Book V part 7)."""

    job_id: int
    symbol: str
    timeframe: Timeframe
    kind: str
    priority: int
    status: str
    attempts: int
    seed: int
    window_bars: int
    created_at: Timestamp
    completed_at: Timestamp | None
    result: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentRecord:
    """One registered experiment with its reproducibility stamps."""

    experiment_id: int
    hypothesis: str
    symbol: str
    timeframe: Timeframe
    window_start: Timestamp
    window_end: Timestamp
    seed: int
    project_version: str
    baseline: str
    candidate: str
    p_value: float | None
    effect_size: float | None
    status: str
    created_at: Timestamp


class SqliteResearchRepository:
    """Durable research memory: jobs, versions, experiments, artifacts."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("research repository is already open", code="STO-090")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        for statement in _SCHEMA:
            connection.execute(statement)
        connection.commit()
        return connection

    async def close(self) -> None:
        """Close the database; idempotent."""
        async with self._lock:
            if self._connection is not None:
                await asyncio.to_thread(self._connection.close)
                self._connection = None

    def _require(self) -> sqlite3.Connection:
        if self._connection is None:
            raise StorageError("research repository is not open", code="STO-091")
        return self._connection

    async def _execute(self, query: str, parameters: tuple[object, ...]) -> int:
        connection = self._require()

        def write() -> int:
            with connection:
                cursor = connection.execute(query, parameters)
            return int(cursor.lastrowid or 0)

        async with self._lock:
            return await asyncio.to_thread(write)

    async def _fetch(
        self, query: str, parameters: tuple[object, ...]
    ) -> list[tuple[object, ...]]:
        connection = self._require()
        async with self._lock:
            return await asyncio.to_thread(
                lambda: connection.execute(query, parameters).fetchall()
            )

    # --- Jobs -------------------------------------------------------------------

    async def enqueue_job(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        kind: str,
        priority: int,
        seed: int,
        window_bars: int,
        created_at: Timestamp,
    ) -> int:
        """Queue one job; returns its id."""
        return await self._execute(
            "INSERT INTO research_jobs (symbol, timeframe, kind, priority, status,"
            " attempts, seed, window_bars, created_at_ms) VALUES (?,?,?,?,?,0,?,?,?)",
            (
                symbol, timeframe.value, kind, priority, JOB_PENDING,
                seed, window_bars, created_at.epoch_ms,
            ),
        )

    async def next_pending_job(self) -> ResearchJob | None:
        """Highest-priority oldest pending job (part 7 priority policy)."""
        rows = await self._fetch(
            "SELECT * FROM research_jobs WHERE status = ? "
            "ORDER BY priority, created_at_ms, job_id LIMIT 1",
            (JOB_PENDING,),
        )
        return self._to_job(rows[0]) if rows else None

    async def mark_job(
        self,
        job_id: int,
        *,
        status: str,
        completed_at: Timestamp | None = None,
        result: str | None = None,
        bump_attempts: bool = False,
    ) -> None:
        """Advance one job's lifecycle status."""
        await self._execute(
            "UPDATE research_jobs SET status = ?, completed_at_ms = ?, result = ?,"
            " attempts = attempts + ? WHERE job_id = ?",
            (
                status,
                completed_at.epoch_ms if completed_at else None,
                result,
                1 if bump_attempts else 0,
                job_id,
            ),
        )

    async def jobs(self, *, status: str | None = None) -> list[ResearchJob]:
        """Queued jobs, oldest first, optionally by status."""
        query = "SELECT * FROM research_jobs"
        parameters: tuple[object, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            parameters = (status,)
        query += " ORDER BY created_at_ms, job_id"
        return [self._to_job(row) for row in await self._fetch(query, parameters)]

    # --- Active versions (runtime injection + rollback) -----------------------------

    async def activate_version(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        kind: str,
        artifact_path: str,
        activated_at: Timestamp,
    ) -> int:
        """Point the series at a new accepted artifact (history kept)."""
        rows = await self._fetch(
            "SELECT COALESCE(MAX(sequence), 0) FROM active_versions "
            "WHERE symbol = ? AND timeframe = ? AND kind = ?",
            (symbol, timeframe.value, kind),
        )
        sequence = int(str(rows[0][0])) + 1
        await self._execute(
            "UPDATE active_versions SET active = 0 "
            "WHERE symbol = ? AND timeframe = ? AND kind = ?",
            (symbol, timeframe.value, kind),
        )
        await self._execute(
            "INSERT INTO active_versions VALUES (?,?,?,?,?,?,1)",
            (
                symbol, timeframe.value, kind, sequence,
                artifact_path, activated_at.epoch_ms,
            ),
        )
        return sequence

    async def active_artifact(
        self, symbol: str, timeframe: Timeframe, kind: str
    ) -> str | None:
        """The currently active artifact path, if any."""
        rows = await self._fetch(
            "SELECT artifact_path FROM active_versions "
            "WHERE symbol = ? AND timeframe = ? AND kind = ? AND active = 1 "
            "ORDER BY sequence DESC LIMIT 1",
            (symbol, timeframe.value, kind),
        )
        return str(rows[0][0]) if rows else None

    async def rollback_version(
        self, symbol: str, timeframe: Timeframe, kind: str
    ) -> str | None:
        """Repoint to the previous version; returns its path or None."""
        rows = await self._fetch(
            "SELECT sequence, artifact_path FROM active_versions "
            "WHERE symbol = ? AND timeframe = ? AND kind = ? "
            "ORDER BY sequence DESC LIMIT 2",
            (symbol, timeframe.value, kind),
        )
        if len(rows) < 2:
            return None
        previous_sequence = int(str(rows[1][0]))
        await self._execute(
            "UPDATE active_versions SET active = CASE WHEN sequence = ? THEN 1 "
            "ELSE 0 END WHERE symbol = ? AND timeframe = ? AND kind = ?",
            (previous_sequence, symbol, timeframe.value, kind),
        )
        return str(rows[1][1])

    # --- Experiments ---------------------------------------------------------------

    async def register_experiment(
        self,
        *,
        hypothesis: str,
        symbol: str,
        timeframe: Timeframe,
        window_start: Timestamp,
        window_end: Timestamp,
        seed: int,
        project_version: str,
        baseline: str,
        candidate: str,
        p_value: float | None,
        effect_size: float | None,
        status: str,
        created_at: Timestamp,
    ) -> int:
        """Register one completed experiment; returns its id."""
        return await self._execute(
            "INSERT INTO experiments (hypothesis, symbol, timeframe,"
            " window_start_ms, window_end_ms, seed, project_version, baseline,"
            " candidate, p_value, effect_size, status, created_at_ms)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                hypothesis, symbol, timeframe.value, window_start.epoch_ms,
                window_end.epoch_ms, seed, project_version, baseline, candidate,
                p_value, effect_size, status, created_at.epoch_ms,
            ),
        )

    async def experiments(self) -> list[ExperimentRecord]:
        """Registered experiments, oldest first."""
        rows = await self._fetch(
            "SELECT * FROM experiments ORDER BY created_at_ms, experiment_id", ()
        )
        return [self._to_experiment(row) for row in rows]

    # --- Learning artifacts -----------------------------------------------------------

    async def save_learning_artifact(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        payload: str,
        outcomes: int,
        created_at: Timestamp,
    ) -> int:
        """Persist the next learning-state version; returns the version."""
        rows = await self._fetch(
            "SELECT COALESCE(MAX(version), 0) FROM learning_artifacts "
            "WHERE symbol = ? AND timeframe = ?",
            (symbol, timeframe.value),
        )
        version = int(str(rows[0][0])) + 1
        await self._execute(
            "INSERT INTO learning_artifacts VALUES (?,?,?,?,?,?)",
            (
                symbol, timeframe.value, version, payload, outcomes,
                created_at.epoch_ms,
            ),
        )
        return version

    async def latest_learning_artifact(
        self, symbol: str, timeframe: Timeframe
    ) -> str | None:
        """The newest learning-state payload for one series."""
        rows = await self._fetch(
            "SELECT payload FROM learning_artifacts WHERE symbol = ? AND "
            "timeframe = ? ORDER BY version DESC LIMIT 1",
            (symbol, timeframe.value),
        )
        return str(rows[0][0]) if rows else None

    # --- Row mapping --------------------------------------------------------------------

    def _to_job(self, row: tuple[object, ...]) -> ResearchJob:
        (
            job_id, symbol, timeframe, kind, priority, status, attempts,
            seed, window_bars, created_at_ms, completed_at_ms, result,
        ) = row
        return ResearchJob(
            job_id=int(str(job_id)),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            kind=str(kind),
            priority=int(str(priority)),
            status=str(status),
            attempts=int(str(attempts)),
            seed=int(str(seed)),
            window_bars=int(str(window_bars)),
            created_at=Timestamp(epoch_ms=int(str(created_at_ms))),
            completed_at=(
                Timestamp(epoch_ms=int(str(completed_at_ms)))
                if completed_at_ms is not None
                else None
            ),
            result=str(result) if result is not None else None,
        )

    def _to_experiment(self, row: tuple[object, ...]) -> ExperimentRecord:
        (
            experiment_id, hypothesis, symbol, timeframe, window_start_ms,
            window_end_ms, seed, project_version, baseline, candidate,
            p_value, effect_size, status, created_at_ms,
        ) = row
        return ExperimentRecord(
            experiment_id=int(str(experiment_id)),
            hypothesis=str(hypothesis),
            symbol=str(symbol),
            timeframe=Timeframe(str(timeframe)),
            window_start=Timestamp(epoch_ms=int(str(window_start_ms))),
            window_end=Timestamp(epoch_ms=int(str(window_end_ms))),
            seed=int(str(seed)),
            project_version=str(project_version),
            baseline=str(baseline),
            candidate=str(candidate),
            p_value=float(str(p_value)) if p_value is not None else None,
            effect_size=float(str(effect_size)) if effect_size is not None else None,
            status=str(status),
            created_at=Timestamp(epoch_ms=int(str(created_at_ms))),
        )

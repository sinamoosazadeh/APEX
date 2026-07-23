"""Signal optimization run store and parameter artifacts (Book V).

Every run is recorded in SQLite; accepted winners additionally publish
the Book V per-symbol-per-timeframe artifact
(``{SYMBOL}_{TF}_signal.json``) carrying the optimized parameters,
dataset information, validation scores, a SHA256 integrity hash and -
when the security platform holds a signing key - an HMAC signature
(25.18). Symbol/timeframe isolation is structural: one artifact per
series, nothing shared.
"""

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Final

from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp
from apex.optimization.staged import OptimizationReport as SignalOptimizationReport

_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS optimization_runs (
    symbol         TEXT    NOT NULL,
    timeframe      TEXT    NOT NULL,
    seed           INTEGER NOT NULL,
    optimizer      TEXT    NOT NULL,
    trials         INTEGER NOT NULL,
    best_score     REAL    NOT NULL,
    confidence     REAL    NOT NULL,
    accepted       INTEGER NOT NULL,
    report         TEXT    NOT NULL,
    created_at_ms  INTEGER NOT NULL,
    PRIMARY KEY (symbol, timeframe, seed, optimizer)
)
"""

_INSERT: Final[str] = """
INSERT INTO optimization_runs (
    symbol, timeframe, seed, optimizer, trials, best_score, confidence,
    accepted, report, created_at_ms
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(symbol, timeframe, seed, optimizer) DO UPDATE SET
    trials = excluded.trials, best_score = excluded.best_score,
    confidence = excluded.confidence, accepted = excluded.accepted,
    report = excluded.report, created_at_ms = excluded.created_at_ms
"""


def report_payload(report: SignalOptimizationReport) -> dict[str, object]:
    """The canonical JSON-ready payload for a report."""
    payload = asdict(report)
    payload["best_overrides"] = dict(report.best_overrides)
    payload["sensitivity"] = [list(item) for item in report.sensitivity]
    return payload


def artifact_document(
    report: SignalOptimizationReport,
    *,
    created_at: Timestamp,
    apex_version: str,
    signer: Callable[[str], str | None] | None = None,
) -> dict[str, object]:
    """The Book V artifact document: SHA256 hash + optional signature."""
    body: dict[str, object] = {
        "symbol": report.symbol,
        "timeframe": report.timeframe,
        "optimizer_version": report.optimizer_version,
        "apex_version": apex_version,
        "optimization_timestamp_ms": created_at.epoch_ms,
        "seed": report.seed,
        "trials": report.trials,
        "dataset": {
            "bars_evaluated": report.bars_evaluated,
            "window_start_ms": report.window_start_ms,
            "window_end_ms": report.window_end_ms,
        },
        "optimized_parameters": dict(report.best_overrides),
        "objective_score": report.best_score,
        "validation": {
            "walk_forward": list(report.walk_forward.fold_scores),
            "rolling": list(report.rolling.fold_scores),
            "expanding": list(report.expanding.fold_scores),
            "monte_carlo_share": report.monte_carlo_share,
            "degradation": report.degradation,
        },
        "stability_score": report.stability_score,
        "confidence_score": report.confidence,
        "parameter_importance": [list(item) for item in report.sensitivity],
        "accepted": report.accepted,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    if signer is not None:
        signature = signer(canonical)
        if signature is not None:
            body["signature"] = signature
    return body


class SignalOptimizationStore:
    """SQLite run history plus the per-series JSON artifacts."""

    def __init__(
        self,
        *,
        database_path: Path,
        artifact_dir: Path,
        signer: Callable[[str], str | None] | None = None,
    ) -> None:
        self._path = database_path
        self._artifacts = artifact_dir
        self._signer = signer
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("optimization store is already open", code="STO-060")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._artifacts.mkdir(parents=True, exist_ok=True)
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
            raise StorageError("optimization store is not open", code="STO-061")
        return self._connection

    async def record_run(
        self, report: SignalOptimizationReport, *, created_at: Timestamp
    ) -> None:
        """Persist the run record (accepted or rejected)."""
        connection = self._require_connection()
        row = (
            report.symbol, report.timeframe, report.seed,
            report.optimizer_version, report.trials, report.best_score,
            report.confidence, 1 if report.accepted else 0,
            json.dumps(report_payload(report), sort_keys=True),
            created_at.epoch_ms,
        )

        def write() -> None:
            with connection:
                connection.execute(_INSERT, row)

        async with self._lock:
            await asyncio.to_thread(write)

    async def publish_artifact(
        self,
        report: SignalOptimizationReport,
        *,
        created_at: Timestamp,
        apex_version: str,
    ) -> Path:
        """Write the accepted winner's Book V artifact; returns its path."""
        if not report.accepted:
            raise StorageError(
                "rejected runs may not publish artifacts",
                code="STO-062",
                details={"symbol": report.symbol, "timeframe": report.timeframe},
            )
        document = artifact_document(
            report,
            created_at=created_at,
            apex_version=apex_version,
            signer=self._signer,
        )
        kind = report.optimizer_version.split("-", 1)[0]
        path = self._artifacts / f"{report.symbol}_{report.timeframe}_{kind}.json"

        def write() -> None:
            path.write_text(json.dumps(document, indent=2, sort_keys=True))

        async with self._lock:
            await asyncio.to_thread(write)
        return path

    async def latest(
        self, symbol: str, timeframe: str
    ) -> dict[str, object] | None:
        """The most recent run payload for one series, if any."""
        connection = self._require_connection()
        query = (
            "SELECT report FROM optimization_runs WHERE symbol = ? AND "
            "timeframe = ? ORDER BY created_at_ms DESC LIMIT 1"
        )
        async with self._lock:
            row = await asyncio.to_thread(
                lambda: connection.execute(query, (symbol, timeframe)).fetchone()
            )
        if row is None:
            return None
        return dict(json.loads(str(row[0])))

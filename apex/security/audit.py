"""Immutable hash-chained audit ledger (Book II 25.16/25.17; Book I 13.25).

Every security-relevant event lands as one append-only row carrying
timestamp, actor, action, target, result, details, the previous
entry's hash and its own hash over the canonical serialization of all
of that - a chain (25.16): deleting, editing or reordering any row
breaks every hash after it, and ``verify_chain`` detects it (25.17).
The ledger exposes no update or delete surface at all.
"""

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from apex.core.exceptions import SecurityError
from apex.core.serialization import JsonValue
from apex.core.time.timestamp import Timestamp

GENESIS_HASH: Final[str] = "0" * 64

_SCHEMA: Final[str] = """
    CREATE TABLE IF NOT EXISTS audit_ledger (
        sequence       INTEGER PRIMARY KEY AUTOINCREMENT,
        occurred_at_ms INTEGER NOT NULL,
        actor          TEXT    NOT NULL,
        action         TEXT    NOT NULL,
        target         TEXT    NOT NULL,
        result         TEXT    NOT NULL,
        details        TEXT    NOT NULL,
        previous_hash  TEXT    NOT NULL,
        entry_hash     TEXT    NOT NULL
    )
"""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditRecord:
    """One immutable audit entry (25.16 required fields)."""

    sequence: int
    occurred_at: Timestamp
    actor: str
    action: str
    target: str
    result: str
    details: str
    previous_hash: str
    entry_hash: str


def _entry_hash(
    *,
    occurred_at_ms: int,
    actor: str,
    action: str,
    target: str,
    result: str,
    details: str,
    previous_hash: str,
) -> str:
    canonical = json.dumps(
        {
            "occurred_at_ms": occurred_at_ms,
            "actor": actor,
            "action": action,
            "target": target,
            "result": result,
            "details": details,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SqliteAuditLedger:
    """Durable append-only audit chain; no mutation surface exists."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the ledger and ensure the schema exists."""
        if self._connection is not None:
            raise SecurityError("audit ledger is already open", code="SEC-020")
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
        """Close the ledger; idempotent."""
        async with self._lock:
            if self._connection is not None:
                await asyncio.to_thread(self._connection.close)
                self._connection = None

    def _require(self) -> sqlite3.Connection:
        if self._connection is None:
            raise SecurityError("audit ledger is not open", code="SEC-021")
        return self._connection

    async def append(
        self,
        *,
        actor: str,
        action: str,
        target: str,
        result: str,
        details: Mapping[str, JsonValue],
        occurred_at: Timestamp,
    ) -> AuditRecord:
        """Chain one new entry onto the ledger."""
        connection = self._require()
        details_json = json.dumps(dict(details), sort_keys=True, separators=(",", ":"))

        def write() -> AuditRecord:
            with connection:
                row = connection.execute(
                    "SELECT entry_hash FROM audit_ledger"
                    " ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                previous = str(row[0]) if row else GENESIS_HASH
                entry = _entry_hash(
                    occurred_at_ms=occurred_at.epoch_ms,
                    actor=actor,
                    action=action,
                    target=target,
                    result=result,
                    details=details_json,
                    previous_hash=previous,
                )
                cursor = connection.execute(
                    "INSERT INTO audit_ledger (occurred_at_ms, actor, action,"
                    " target, result, details, previous_hash, entry_hash)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (
                        occurred_at.epoch_ms, actor, action, target,
                        result, details_json, previous, entry,
                    ),
                )
            return AuditRecord(
                sequence=int(cursor.lastrowid or 0),
                occurred_at=occurred_at,
                actor=actor,
                action=action,
                target=target,
                result=result,
                details=details_json,
                previous_hash=previous,
                entry_hash=entry,
            )

        async with self._lock:
            return await asyncio.to_thread(write)

    async def records(self, *, limit: int | None = None) -> list[AuditRecord]:
        """Entries in chain order (oldest first), optionally the newest N."""
        connection = self._require()
        query = "SELECT * FROM audit_ledger ORDER BY sequence"
        if limit is not None:
            query = (
                "SELECT * FROM (SELECT * FROM audit_ledger ORDER BY sequence"
                f" DESC LIMIT {int(limit)}) ORDER BY sequence"
            )
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(query).fetchall()
            )
        return [self._to_record(row) for row in rows]

    async def count(self) -> int:
        """Total chained entries."""
        connection = self._require()
        async with self._lock:
            rows = await asyncio.to_thread(
                lambda: connection.execute(
                    "SELECT COUNT(*) FROM audit_ledger"
                ).fetchall()
            )
        return int(str(rows[0][0]))

    async def verify_chain(self) -> tuple[bool, int, str | None]:
        """Recompute the full chain; (ok, entries checked, break reason)."""
        expected = GENESIS_HASH
        checked = 0
        for record in await self.records():
            if record.previous_hash != expected:
                return False, checked, (
                    f"entry {record.sequence}: broken linkage"
                )
            recomputed = _entry_hash(
                occurred_at_ms=record.occurred_at.epoch_ms,
                actor=record.actor,
                action=record.action,
                target=record.target,
                result=record.result,
                details=record.details,
                previous_hash=record.previous_hash,
            )
            if recomputed != record.entry_hash:
                return False, checked, (
                    f"entry {record.sequence}: content hash mismatch"
                )
            expected = record.entry_hash
            checked += 1
        return True, checked, None

    def _to_record(self, row: tuple[object, ...]) -> AuditRecord:
        (
            sequence, occurred_at_ms, actor, action, target,
            result, details, previous_hash, entry_hash,
        ) = row
        return AuditRecord(
            sequence=int(str(sequence)),
            occurred_at=Timestamp(epoch_ms=int(str(occurred_at_ms))),
            actor=str(actor),
            action=str(action),
            target=str(target),
            result=str(result),
            details=str(details),
            previous_hash=str(previous_hash),
            entry_hash=str(entry_hash),
        )

"""SQLite storage backends.

First durable persistence of the Storage Platform (Book II ch. 24).
All SQLite access is offloaded to worker threads so the async policy
(Constitution 3.14) holds: no event-loop-blocking I/O.

One connection per storage instance, WAL journal mode, serialized by
an asyncio lock - deterministic, safe, and replaceable later by
DuckDB/Parquet backends behind the same contracts.
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Final

from apex.core.exceptions import StorageError
from apex.core.validation import ensure_not_empty

_KV_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS kv_store (
    namespace TEXT NOT NULL,
    key       TEXT NOT NULL,
    payload   BLOB NOT NULL,
    PRIMARY KEY (namespace, key)
)
"""


class SqliteKeyValueStorage:
    """Namespaced key/value storage implementing the IStorage contract."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("storage is already open", code="STO-001")
        self._connection = await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(_KV_SCHEMA)
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
            raise StorageError("storage is not open", code="STO-002")
        return self._connection

    async def write(self, namespace: str, key: str, payload: bytes) -> None:
        """Persist a payload under ``namespace/key`` (upsert)."""
        ensure_not_empty(namespace, "namespace")
        ensure_not_empty(key, "key")
        connection = self._require_connection()
        async with self._lock:
            await asyncio.to_thread(self._write_blocking, connection, namespace, key, payload)

    @staticmethod
    def _write_blocking(
        connection: sqlite3.Connection,
        namespace: str,
        key: str,
        payload: bytes,
    ) -> None:
        connection.execute(
            "INSERT INTO kv_store (namespace, key, payload) VALUES (?, ?, ?) "
            "ON CONFLICT(namespace, key) DO UPDATE SET payload = excluded.payload",
            (namespace, key, payload),
        )
        connection.commit()

    async def read(self, namespace: str, key: str) -> bytes | None:
        """Fetch a payload, or None when absent."""
        connection = self._require_connection()
        async with self._lock:
            row = await asyncio.to_thread(
                lambda: connection.execute(
                    "SELECT payload FROM kv_store WHERE namespace = ? AND key = ?",
                    (namespace, key),
                ).fetchone()
            )
        return bytes(row[0]) if row is not None else None

    async def exists(self, namespace: str, key: str) -> bool:
        """Whether ``namespace/key`` holds a payload."""
        return await self.read(namespace, key) is not None

    async def delete(self, namespace: str, key: str) -> bool:
        """Remove a payload; returns whether it existed."""
        connection = self._require_connection()
        async with self._lock:
            cursor = await asyncio.to_thread(
                lambda: connection.execute(
                    "DELETE FROM kv_store WHERE namespace = ? AND key = ?",
                    (namespace, key),
                )
            )
            await asyncio.to_thread(connection.commit)
        return cursor.rowcount > 0

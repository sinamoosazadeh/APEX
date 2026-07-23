"""Monitoring store (Book II 26.3 time-series persistence; Book I 10.16/10.17).

One durable home for the observability layer's records: metric
samples, heartbeats, deduplicated alerts, incidents, state snapshots
and the kill-switch history. Retention is config-driven pruning (the
spec mandates a time-series store but is silent on retention - the
platform makes it explicit). Kill-switch state is durable and
auditable: transitions append, never overwrite.
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Final

from apex.core.exceptions import StorageError
from apex.core.time.timestamp import Timestamp
from apex.monitoring.records import (
    INCIDENT_OPEN,
    INCIDENT_RESOLVED,
    AlertRecord,
    AlertSeverity,
    HeartbeatRecord,
    IncidentRecord,
    KillSwitchLevel,
    KillSwitchRecord,
    MetricSample,
    StateSnapshotRecord,
)

_SCHEMA: Final[tuple[str, ...]] = (
    """
    CREATE TABLE IF NOT EXISTS monitoring_metrics (
        metric_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT    NOT NULL,
        value          REAL    NOT NULL,
        tags           TEXT    NOT NULL,
        recorded_at_ms INTEGER NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_monitoring_metrics_name_time
    ON monitoring_metrics (name, recorded_at_ms)
    """,
    """
    CREATE TABLE IF NOT EXISTS monitoring_heartbeats (
        component      TEXT    PRIMARY KEY,
        beat_at_ms     INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS monitoring_alerts (
        alert_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        severity       TEXT    NOT NULL,
        category       TEXT    NOT NULL,
        message        TEXT    NOT NULL,
        dedup_key      TEXT    NOT NULL,
        count          INTEGER NOT NULL,
        first_at_ms    INTEGER NOT NULL,
        last_at_ms     INTEGER NOT NULL,
        incident_id    INTEGER
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_dedup
    ON monitoring_alerts (dedup_key, last_at_ms)
    """,
    """
    CREATE TABLE IF NOT EXISTS monitoring_incidents (
        incident_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        opened_at_ms   INTEGER NOT NULL,
        severity       TEXT    NOT NULL,
        summary        TEXT    NOT NULL,
        dedup_key      TEXT    NOT NULL,
        status         TEXT    NOT NULL,
        resolved_at_ms INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS monitoring_snapshots (
        snapshot_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        taken_at_ms    INTEGER NOT NULL,
        payload        TEXT    NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS monitoring_killswitch (
        entry_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        level          TEXT    NOT NULL,
        reason         TEXT    NOT NULL,
        actor          TEXT    NOT NULL,
        changed_at_ms  INTEGER NOT NULL
    )
    """,
)


class SqliteMonitoringRepository:
    """Durable observability memory behind the telemetry surfaces."""

    def __init__(self, *, database_path: Path) -> None:
        self._path = database_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure the schema exists."""
        if self._connection is not None:
            raise StorageError("monitoring repository is already open", code="STO-100")
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
            raise StorageError("monitoring repository is not open", code="STO-101")
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

    # --- Metrics ---------------------------------------------------------------

    async def insert_metrics(self, samples: list[MetricSample]) -> int:
        """Append a batch of metric samples; returns the count stored."""
        if not samples:
            return 0
        connection = self._require()
        rows = [
            (
                sample.name,
                sample.value,
                json.dumps(sample.tags, sort_keys=True),
                sample.recorded_at.epoch_ms,
            )
            for sample in samples
        ]

        def write() -> int:
            with connection:
                connection.executemany(
                    "INSERT INTO monitoring_metrics (name, value, tags,"
                    " recorded_at_ms) VALUES (?,?,?,?)",
                    rows,
                )
            return len(rows)

        async with self._lock:
            return await asyncio.to_thread(write)

    async def metric_values(
        self, name: str, *, since_ms: int, limit: int = 1_000
    ) -> list[tuple[int, float]]:
        """(recorded_at_ms, value) pairs for one metric, oldest first."""
        rows = await self._fetch(
            "SELECT recorded_at_ms, value FROM monitoring_metrics "
            "WHERE name = ? AND recorded_at_ms >= ? "
            "ORDER BY recorded_at_ms, metric_id LIMIT ?",
            (name, since_ms, limit),
        )
        return [(int(str(at)), float(str(value))) for at, value in rows]

    async def count_metric(self, name: str, *, since_ms: int) -> int:
        """How many samples of one metric landed since the cutoff."""
        rows = await self._fetch(
            "SELECT COUNT(*) FROM monitoring_metrics "
            "WHERE name = ? AND recorded_at_ms >= ?",
            (name, since_ms),
        )
        return int(str(rows[0][0]))

    # --- Heartbeats ------------------------------------------------------------

    async def beat(self, component: str, at: Timestamp) -> None:
        """Record one component's liveness beat (upsert)."""
        await self._execute(
            "INSERT INTO monitoring_heartbeats (component, beat_at_ms) VALUES (?,?) "
            "ON CONFLICT(component) DO UPDATE SET beat_at_ms = excluded.beat_at_ms",
            (component, at.epoch_ms),
        )

    async def heartbeats(self) -> list[HeartbeatRecord]:
        """Every component's latest beat, by component name."""
        rows = await self._fetch(
            "SELECT component, beat_at_ms FROM monitoring_heartbeats "
            "ORDER BY component",
            (),
        )
        return [
            HeartbeatRecord(
                component=str(component),
                beat_at=Timestamp(epoch_ms=int(str(beat_at_ms))),
            )
            for component, beat_at_ms in rows
        ]

    # --- Alerts ------------------------------------------------------------------

    async def recent_alert(self, dedup_key: str, *, since_ms: int) -> AlertRecord | None:
        """The newest alert with this dedup key since the cutoff, if any."""
        rows = await self._fetch(
            "SELECT * FROM monitoring_alerts WHERE dedup_key = ? AND last_at_ms >= ? "
            "ORDER BY last_at_ms DESC, alert_id DESC LIMIT 1",
            (dedup_key, since_ms),
        )
        return self._to_alert(rows[0]) if rows else None

    async def insert_alert(
        self,
        *,
        severity: AlertSeverity,
        category: str,
        message: str,
        dedup_key: str,
        at: Timestamp,
        incident_id: int | None = None,
    ) -> int:
        """Append a new alert; returns its id."""
        return await self._execute(
            "INSERT INTO monitoring_alerts (severity, category, message, dedup_key,"
            " count, first_at_ms, last_at_ms, incident_id) VALUES (?,?,?,?,1,?,?,?)",
            (
                severity.value, category, message, dedup_key,
                at.epoch_ms, at.epoch_ms, incident_id,
            ),
        )

    async def bump_alert(
        self, alert_id: int, *, at: Timestamp, severity: AlertSeverity
    ) -> None:
        """Fold a recurrence into an existing alert (26.22 dedup)."""
        await self._execute(
            "UPDATE monitoring_alerts SET count = count + 1, last_at_ms = ?, "
            "severity = ? WHERE alert_id = ?",
            (at.epoch_ms, severity.value, alert_id),
        )

    async def alerts(self, *, limit: int = 20) -> list[AlertRecord]:
        """Most recent alerts, newest first."""
        rows = await self._fetch(
            "SELECT * FROM monitoring_alerts ORDER BY last_at_ms DESC,"
            " alert_id DESC LIMIT ?",
            (limit,),
        )
        return [self._to_alert(row) for row in rows]

    # --- Incidents -------------------------------------------------------------------

    async def open_incident_for(self, dedup_key: str) -> IncidentRecord | None:
        """The open incident carrying this dedup key, if any."""
        rows = await self._fetch(
            "SELECT * FROM monitoring_incidents WHERE dedup_key = ? AND status = ? "
            "ORDER BY incident_id DESC LIMIT 1",
            (dedup_key, INCIDENT_OPEN),
        )
        return self._to_incident(rows[0]) if rows else None

    async def insert_incident(
        self,
        *,
        opened_at: Timestamp,
        severity: AlertSeverity,
        summary: str,
        dedup_key: str,
    ) -> int:
        """Open a new incident; returns its id."""
        return await self._execute(
            "INSERT INTO monitoring_incidents (opened_at_ms, severity, summary,"
            " dedup_key, status, resolved_at_ms) VALUES (?,?,?,?,?,NULL)",
            (opened_at.epoch_ms, severity.value, summary, dedup_key, INCIDENT_OPEN),
        )

    async def resolve_incident(self, incident_id: int, *, at: Timestamp) -> None:
        """Mark one incident resolved."""
        await self._execute(
            "UPDATE monitoring_incidents SET status = ?, resolved_at_ms = ? "
            "WHERE incident_id = ?",
            (INCIDENT_RESOLVED, at.epoch_ms, incident_id),
        )

    async def open_incidents(self) -> list[IncidentRecord]:
        """Every open incident, oldest first."""
        rows = await self._fetch(
            "SELECT * FROM monitoring_incidents WHERE status = ? "
            "ORDER BY incident_id",
            (INCIDENT_OPEN,),
        )
        return [self._to_incident(row) for row in rows]

    # --- Snapshots -------------------------------------------------------------------

    async def insert_snapshot(self, *, taken_at: Timestamp, payload: str) -> int:
        """Append one state snapshot; returns its id."""
        return await self._execute(
            "INSERT INTO monitoring_snapshots (taken_at_ms, payload) VALUES (?,?)",
            (taken_at.epoch_ms, payload),
        )

    async def snapshots(self, *, limit: int = 10) -> list[StateSnapshotRecord]:
        """Most recent snapshots, newest first."""
        rows = await self._fetch(
            "SELECT * FROM monitoring_snapshots ORDER BY snapshot_id DESC LIMIT ?",
            (limit,),
        )
        return [
            StateSnapshotRecord(
                snapshot_id=int(str(snapshot_id)),
                taken_at=Timestamp(epoch_ms=int(str(taken_at_ms))),
                payload=str(payload),
            )
            for snapshot_id, taken_at_ms, payload in rows
        ]

    async def snapshot_count(self) -> int:
        """How many snapshots are stored."""
        rows = await self._fetch("SELECT COUNT(*) FROM monitoring_snapshots", ())
        return int(str(rows[0][0]))

    # --- Kill switch --------------------------------------------------------------------

    async def insert_kill_switch(
        self, *, level: KillSwitchLevel, reason: str, actor: str, at: Timestamp
    ) -> int:
        """Append one kill-switch transition; returns its entry id."""
        return await self._execute(
            "INSERT INTO monitoring_killswitch (level, reason, actor, changed_at_ms)"
            " VALUES (?,?,?,?)",
            (level.value, reason, actor, at.epoch_ms),
        )

    async def current_kill_switch(self) -> KillSwitchRecord | None:
        """The latest kill-switch state entry, if any transition exists."""
        rows = await self._fetch(
            "SELECT * FROM monitoring_killswitch ORDER BY entry_id DESC LIMIT 1", ()
        )
        return self._to_kill_switch(rows[0]) if rows else None

    async def kill_switch_history(self, *, limit: int = 20) -> list[KillSwitchRecord]:
        """Recent kill-switch transitions, newest first."""
        rows = await self._fetch(
            "SELECT * FROM monitoring_killswitch ORDER BY entry_id DESC LIMIT ?",
            (limit,),
        )
        return [self._to_kill_switch(row) for row in rows]

    # --- Retention ---------------------------------------------------------------------

    async def prune(self, *, older_than_ms: int) -> int:
        """Delete aged metric samples and snapshots; returns rows removed."""
        removed = 0
        connection = self._require()

        def write() -> int:
            with connection:
                metrics = connection.execute(
                    "DELETE FROM monitoring_metrics WHERE recorded_at_ms < ?",
                    (older_than_ms,),
                ).rowcount
                snapshots = connection.execute(
                    "DELETE FROM monitoring_snapshots WHERE taken_at_ms < ?",
                    (older_than_ms,),
                ).rowcount
            return int(metrics) + int(snapshots)

        async with self._lock:
            removed = await asyncio.to_thread(write)
        return removed

    # --- Row mapping -----------------------------------------------------------------

    def _to_alert(self, row: tuple[object, ...]) -> AlertRecord:
        (
            alert_id, severity, category, message, dedup_key,
            count, first_at_ms, last_at_ms, incident_id,
        ) = row
        return AlertRecord(
            alert_id=int(str(alert_id)),
            severity=AlertSeverity(str(severity)),
            category=str(category),
            message=str(message),
            dedup_key=str(dedup_key),
            count=int(str(count)),
            first_at=Timestamp(epoch_ms=int(str(first_at_ms))),
            last_at=Timestamp(epoch_ms=int(str(last_at_ms))),
            incident_id=int(str(incident_id)) if incident_id is not None else None,
        )

    def _to_incident(self, row: tuple[object, ...]) -> IncidentRecord:
        (
            incident_id, opened_at_ms, severity, summary,
            dedup_key, status, resolved_at_ms,
        ) = row
        return IncidentRecord(
            incident_id=int(str(incident_id)),
            opened_at=Timestamp(epoch_ms=int(str(opened_at_ms))),
            severity=AlertSeverity(str(severity)),
            summary=str(summary),
            dedup_key=str(dedup_key),
            status=str(status),
            resolved_at=(
                Timestamp(epoch_ms=int(str(resolved_at_ms)))
                if resolved_at_ms is not None
                else None
            ),
        )

    def _to_kill_switch(self, row: tuple[object, ...]) -> KillSwitchRecord:
        entry_id, level, reason, actor, changed_at_ms = row
        return KillSwitchRecord(
            entry_id=int(str(entry_id)),
            level=KillSwitchLevel(str(level)),
            reason=str(reason),
            actor=str(actor),
            changed_at=Timestamp(epoch_ms=int(str(changed_at_ms))),
        )

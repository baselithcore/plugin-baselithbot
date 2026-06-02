"""Durable backends for the BaselithMed audit ledger.

The in-memory :class:`~plugins.baselithmed.audit.AuditLedger` survives only
as long as the process. Compliance requirements (EU MDR, GDPR art. 30) need
the chain to outlast restarts, so this module provides a pluggable
``AuditPersistenceBackend`` plus a file-based SQLite implementation.

SQLite is chosen over Postgres for the MVP because:
    * It is in the Python stdlib — zero new dependencies, no infra to set up.
    * Audit writes are append-only and infrequent (≤ ~10 per triage
      session) — SQLite's single-writer model is more than enough.
    * The same ``AuditPersistenceBackend`` protocol can later be implemented
      against Postgres or any other store without touching ledger code.

The backend persists every appended entry **including its computed
``this_hash`` and ``prev_hash``** so a cold start can rehydrate the chain
verbatim and ``verify()`` still returns ``True``.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Protocol

from .audit import AuditEntry, AuditEventType


class AuditPersistenceBackend(Protocol):
    """Append-only durable store for :class:`AuditEntry` instances."""

    def append(self, entry: AuditEntry) -> None: ...

    def load_all(self) -> list[AuditEntry]: ...

    def close(self) -> None: ...


class _SchemaBootstrap:
    """SQLite DDL kept here so the table layout is reviewable in one spot."""

    CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS med_audit_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            session_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            this_hash TEXT NOT NULL
        );
    """
    CREATE_SESSION_INDEX = (
        "CREATE INDEX IF NOT EXISTS med_audit_session_idx "
        "ON med_audit_entries(session_id);"
    )


class SQLiteAuditBackend:
    """File-based SQLite implementation of :class:`AuditPersistenceBackend`."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # ``check_same_thread=False`` together with the internal RLock makes
        # the backend safe to share across the asyncio event loop and any
        # worker threads FastAPI may spawn.
        self._conn = sqlite3.connect(
            str(self._path), check_same_thread=False, isolation_level=None
        )
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute(_SchemaBootstrap.CREATE_TABLE)
        self._conn.execute(_SchemaBootstrap.CREATE_SESSION_INDEX)
        self._lock = RLock()

    def append(self, entry: AuditEntry) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO med_audit_entries ("
                "event_id, event_type, session_id, actor, timestamp, "
                "payload_hash, summary_json, prev_hash, this_hash"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.event_id,
                    entry.event_type.value,
                    entry.session_id,
                    entry.actor,
                    entry.timestamp,
                    entry.payload_hash,
                    json.dumps(entry.summary, sort_keys=True),
                    entry.prev_hash,
                    entry.this_hash,
                ),
            )

    def load_all(self) -> list[AuditEntry]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT event_id, event_type, session_id, actor, timestamp, "
                "payload_hash, summary_json, prev_hash, this_hash "
                "FROM med_audit_entries ORDER BY id ASC"
            )
            rows = cur.fetchall()
        entries: list[AuditEntry] = []
        for row in rows:
            (
                event_id,
                event_type,
                session_id,
                actor,
                timestamp,
                payload_hash,
                summary_json,
                prev_hash,
                this_hash,
            ) = row
            summary: dict[str, Any] = json.loads(summary_json)
            entries.append(
                AuditEntry(
                    event_id=event_id,
                    event_type=AuditEventType(event_type),
                    session_id=session_id,
                    actor=actor,
                    timestamp=timestamp,
                    payload_hash=payload_hash,
                    summary=summary,
                    prev_hash=prev_hash,
                    this_hash=this_hash,
                )
            )
        return entries

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001 — close must never raise
                pass

"""Hash-chained audit ledger for the BaselithMed lifecycle.

Every session-affecting event is appended to a per-plugin ledger as an
:class:`AuditEntry`. Each entry stores ``prev_hash`` (the previous entry's
``this_hash``) and ``this_hash`` (a SHA-256 of its own canonical JSON), so
any post-hoc tampering is detectable via :meth:`AuditLedger.verify`.

The ledger is intentionally **payload-light**: only stable identifiers and
a redacted summary are stored. Personal data (raw quotes, free-text notes)
is hashed away — auditors get proof a turn happened, not the turn's verbatim
content.

This in-memory implementation is a stepping stone toward a persisted ledger
(PostgreSQL + signed entries). The public surface (``append``, ``entries``,
``verify``) is stable; swapping the backend is a single class swap.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import TYPE_CHECKING, Any, Final
from uuid import uuid4

from core.context import get_tenant_or_default

if TYPE_CHECKING:
    from .persistence import AuditPersistenceBackend

# Canonical genesis hash: SHA-256 of the literal string "baselithmed:genesis".
# Pinning this value keeps the chain reproducible across processes.
GENESIS_HASH: Final[str] = hashlib.sha256(b"baselithmed:genesis").hexdigest()


class AuditEventType(StrEnum):
    """The lifecycle moments the ledger records."""

    SESSION_CREATED = "session.created"
    INTERVIEW_TURN = "interview.turn"
    TRIAGE_FINALIZED = "triage.finalized"
    VALIDATION_RECORDED = "validation.recorded"


@dataclass(frozen=True)
class AuditEntry:
    """A single ledger entry. Frozen — entries are append-only."""

    event_id: str
    event_type: AuditEventType
    session_id: str
    actor: str
    timestamp: str  # ISO-8601 UTC
    payload_hash: str  # sha256 over the unredacted payload (proof, not data)
    summary: dict[str, Any]  # PHI-free metadata
    prev_hash: str
    this_hash: str
    # Owning tenant. Deliberately NOT part of ``_compute_this_hash`` so existing
    # chains stay valid and the single deployment-wide integrity chain is
    # preserved; it is a read-scoping dimension only (see ``entries``).
    tenant_id: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "payload_hash": self.payload_hash,
            "summary": self.summary,
            "prev_hash": self.prev_hash,
            "this_hash": self.this_hash,
            "tenant_id": self.tenant_id,
        }


def _canonical_json(payload: Any) -> str:
    """Stable JSON form for hashing: sorted keys, no whitespace, UTF-8."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _compute_this_hash(
    *,
    event_id: str,
    event_type: AuditEventType,
    session_id: str,
    actor: str,
    timestamp: str,
    payload_hash: str,
    summary: dict[str, Any],
    prev_hash: str,
) -> str:
    material = _canonical_json(
        {
            "event_id": event_id,
            "event_type": event_type.value,
            "session_id": session_id,
            "actor": actor,
            "timestamp": timestamp,
            "payload_hash": payload_hash,
            "summary": summary,
            "prev_hash": prev_hash,
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class AuditLedger:
    """Append-only, hash-chained ledger for one plugin instance."""

    def __init__(
        self,
        backend: "AuditPersistenceBackend | None" = None,
    ) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = RLock()
        self._backend = backend
        if backend is not None:
            # Cold-start: hydrate from durable store. Chain order is
            # preserved via the insertion-order index, so verify() will
            # report the chain valid as long as the persisted rows are
            # untouched.
            self._entries.extend(backend.load_all())

    def append(
        self,
        *,
        event_type: AuditEventType,
        session_id: str,
        actor: str,
        payload: Any,
        summary: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Append a new entry and return it.

        ``payload`` is hashed but never stored verbatim. ``summary`` should
        contain only PHI-free fields safe for clinician/auditor review.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        event_id = str(uuid4())
        payload_hash = _hash_payload(payload)
        clean_summary = summary or {}
        with self._lock:
            prev_hash = self._entries[-1].this_hash if self._entries else GENESIS_HASH
            this_hash = _compute_this_hash(
                event_id=event_id,
                event_type=event_type,
                session_id=session_id,
                actor=actor,
                timestamp=timestamp,
                payload_hash=payload_hash,
                summary=clean_summary,
                prev_hash=prev_hash,
            )
            entry = AuditEntry(
                event_id=event_id,
                event_type=event_type,
                session_id=session_id,
                actor=actor,
                timestamp=timestamp,
                payload_hash=payload_hash,
                summary=clean_summary,
                prev_hash=prev_hash,
                this_hash=this_hash,
                tenant_id=get_tenant_or_default(),
            )
            self._entries.append(entry)
            if self._backend is not None:
                # Persist after the in-memory append so a backend failure
                # surfaces as an exception rather than a chain-break: the
                # caller can retry; the in-memory state and the backend
                # disagree only transiently.
                self._backend.append(entry)
            return entry

    def entries(self, *, session_id: str | None = None) -> list[AuditEntry]:
        """Return a snapshot of the current tenant's entries, optionally by session.

        Scoped to the active tenant so one tenant never reads another's audit
        trail. The integrity chain (:meth:`verify`) stays deployment-wide and is
        unaffected — it walks the full in-memory chain regardless of tenant.
        """
        tenant = get_tenant_or_default()
        with self._lock:
            return [
                e
                for e in self._entries
                if e.tenant_id == tenant
                and (session_id is None or e.session_id == session_id)
            ]

    def verify(self) -> bool:
        """Re-hash the entire chain and assert link integrity."""
        with self._lock:
            prev_hash = GENESIS_HASH
            for entry in self._entries:
                if entry.prev_hash != prev_hash:
                    return False
                recomputed = _compute_this_hash(
                    event_id=entry.event_id,
                    event_type=entry.event_type,
                    session_id=entry.session_id,
                    actor=entry.actor,
                    timestamp=entry.timestamp,
                    payload_hash=entry.payload_hash,
                    summary=entry.summary,
                    prev_hash=entry.prev_hash,
                )
                if recomputed != entry.this_hash:
                    return False
                prev_hash = entry.this_hash
            return True

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

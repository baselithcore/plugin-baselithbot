"""The :class:`TwinStore` persistence contract shared by every backend.

The service talks to this small Protocol, never to a concrete backend, so the
in-memory default and the durable Postgres implementation are interchangeable.
Every method is ``async`` even where the in-memory impl could be synchronous, so
swapping in a real I/O backend never ripples through callers.

State is partitioned per owner via an ``owner_id`` (the human the twin
represents) — a lightweight tenancy seam mirroring the rest of the framework.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..audit.models import TwinAuditEvent
from ..gateway.models import InboundMessage
from ..models import PendingReply, SalientFact, WhitelistEntry
from ..style.models import StyleProfile

# Per-owner retained message window (bounds memory; recent messages win).
MAX_MESSAGES_PER_OWNER = 10000
# Per-owner salient-fact cap.
MAX_FACTS_PER_OWNER = 5000
# Per-owner audit-trail retention window (append-only; oldest evicted).
MAX_AUDIT_PER_OWNER = 5000
# Per-owner processed-message-id window for inbound idempotency.
MAX_SEEN_PER_OWNER = 20000


@runtime_checkable
class TwinStore(Protocol):
    """Abstract persistence contract for the twin's durable state."""

    async def initialize(self) -> None:
        """Prepare the backend (e.g. create schema). No-op for in-memory."""
        ...

    # -- Message log -------------------------------------------------------

    async def add_message(self, owner_id: str, message: InboundMessage) -> None:
        """Append an observed inbound/outbound message to the owner's log."""
        ...

    async def recent_messages(
        self, owner_id: str, contact_id: str | None = None, limit: int = 50
    ) -> list[InboundMessage]:
        """Return the recent message window, newest last, optionally per contact."""
        ...

    async def owner_messages(self, owner_id: str) -> list[InboundMessage]:
        """Return all messages authored by the owner (``from_me``)."""
        ...

    # -- Style profile -----------------------------------------------------

    async def save_style(self, owner_id: str, profile: StyleProfile) -> None:
        """Persist the latest learned style profile for the owner."""
        ...

    async def get_style(self, owner_id: str) -> StyleProfile | None:
        """Fetch the owner's style profile, or None if not yet trained."""
        ...

    # -- Salient facts (LTM index) ----------------------------------------

    async def add_fact(self, owner_id: str, fact: SalientFact) -> SalientFact:
        """Store a salient fact in the owner's long-term memory index."""
        ...

    async def list_facts(
        self, owner_id: str, contact_id: str | None = None
    ) -> list[SalientFact]:
        """List salient facts, optionally scoped to a contact."""
        ...

    # -- Whitelist ---------------------------------------------------------

    async def add_whitelist(self, owner_id: str, entry: WhitelistEntry) -> None:
        """Authorise a contact for auto-reply."""
        ...

    async def remove_whitelist(self, owner_id: str, contact_id: str) -> bool:
        """Revoke a contact's auto-reply authorisation; True if it existed."""
        ...

    async def list_whitelist(self, owner_id: str) -> list[WhitelistEntry]:
        """Return the owner's auto-reply whitelist."""
        ...

    async def is_whitelisted(self, owner_id: str, contact_id: str) -> bool:
        """Return whether a contact is authorised for auto-reply."""
        ...

    # -- Pending replies (HITL queue) -------------------------------------

    async def save_pending(self, owner_id: str, pending: PendingReply) -> PendingReply:
        """Insert or update a pending reply in the approval queue."""
        ...

    async def get_pending(self, owner_id: str, reply_id: str) -> PendingReply | None:
        """Fetch a pending reply by id, or None if unknown."""
        ...

    async def list_pending(
        self, owner_id: str, only_queued: bool = False
    ) -> list[PendingReply]:
        """List pending replies, newest first, optionally only queued ones."""
        ...

    # -- Audit trail (append-only) ----------------------------------------

    async def record_audit(self, owner_id: str, event: TwinAuditEvent) -> None:
        """Append an immutable audit event for the owner."""
        ...

    async def list_audit(self, owner_id: str, limit: int = 100) -> list[TwinAuditEvent]:
        """Return the most recent audit events, newest first."""
        ...

    # -- Runtime control (kill-switch) ------------------------------------

    async def set_paused(self, owner_id: str, paused: bool) -> None:
        """Persist the runtime pause flag (when paused, nothing auto-sends)."""
        ...

    async def is_paused(self, owner_id: str) -> bool:
        """Return whether auto-send is currently paused for the owner."""
        ...

    # -- Inbound idempotency ----------------------------------------------

    async def mark_seen(self, owner_id: str, message_id: str) -> bool:
        """Record a processed inbound id; return True if it is newly seen.

        A False return means the message was already processed (duplicate
        webhook delivery) and the caller must skip it.
        """
        ...


__all__ = [
    "TwinStore",
    "MAX_MESSAGES_PER_OWNER",
    "MAX_FACTS_PER_OWNER",
    "MAX_AUDIT_PER_OWNER",
    "MAX_SEEN_PER_OWNER",
]

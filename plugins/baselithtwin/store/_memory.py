"""In-memory :class:`TwinStore` — the zero-config default backend.

Holds all twin state in bounded per-owner structures. Ephemeral by design: it
is what the smoke tests run against and what the plugin uses until durable
Postgres persistence is explicitly enabled. Bounds (``MAX_*``) keep memory flat
under a long-running session by evicting the oldest entries.
"""

from __future__ import annotations

from collections import OrderedDict, defaultdict, deque

from ..audit.models import TwinAuditEvent
from ..gateway.models import InboundMessage
from ..models import PendingReply, SalientFact, WhitelistEntry
from ..style.models import StyleProfile
from ._protocol import (
    MAX_AUDIT_PER_OWNER,
    MAX_FACTS_PER_OWNER,
    MAX_MESSAGES_PER_OWNER,
    MAX_SEEN_PER_OWNER,
)


class InMemoryTwinStore:
    """A dependency-free, async-compatible store backed by Python collections."""

    def __init__(self) -> None:
        self._messages: dict[str, deque[InboundMessage]] = defaultdict(
            lambda: deque(maxlen=MAX_MESSAGES_PER_OWNER)
        )
        self._styles: dict[str, StyleProfile] = {}
        self._facts: dict[str, deque[SalientFact]] = defaultdict(
            lambda: deque(maxlen=MAX_FACTS_PER_OWNER)
        )
        self._whitelist: dict[str, dict[str, WhitelistEntry]] = defaultdict(dict)
        self._pending: dict[str, dict[str, PendingReply]] = defaultdict(dict)
        self._audit: dict[str, deque[TwinAuditEvent]] = defaultdict(
            lambda: deque(maxlen=MAX_AUDIT_PER_OWNER)
        )
        self._paused: dict[str, bool] = {}
        self._seen: dict[str, OrderedDict[str, None]] = defaultdict(OrderedDict)

    async def initialize(self) -> None:
        """No schema to prepare for the in-memory backend."""
        return None

    # -- Message log -------------------------------------------------------

    async def add_message(self, owner_id: str, message: InboundMessage) -> None:
        self._messages[owner_id].append(message)

    async def recent_messages(
        self, owner_id: str, contact_id: str | None = None, limit: int = 50
    ) -> list[InboundMessage]:
        items = list(self._messages.get(owner_id, ()))
        if contact_id is not None:
            items = [m for m in items if m.contact_id == contact_id]
        return items[-limit:] if limit else items

    async def owner_messages(self, owner_id: str) -> list[InboundMessage]:
        return [m for m in self._messages.get(owner_id, ()) if m.from_me]

    # -- Style profile -----------------------------------------------------

    async def save_style(self, owner_id: str, profile: StyleProfile) -> None:
        self._styles[owner_id] = profile

    async def get_style(self, owner_id: str) -> StyleProfile | None:
        return self._styles.get(owner_id)

    # -- Salient facts -----------------------------------------------------

    async def add_fact(self, owner_id: str, fact: SalientFact) -> SalientFact:
        self._facts[owner_id].append(fact)
        return fact

    async def list_facts(
        self, owner_id: str, contact_id: str | None = None
    ) -> list[SalientFact]:
        items = list(self._facts.get(owner_id, ()))
        if contact_id is not None:
            items = [f for f in items if f.contact_id == contact_id]
        return items

    # -- Whitelist ---------------------------------------------------------

    async def add_whitelist(self, owner_id: str, entry: WhitelistEntry) -> None:
        self._whitelist[owner_id][entry.contact_id] = entry

    async def remove_whitelist(self, owner_id: str, contact_id: str) -> bool:
        return self._whitelist[owner_id].pop(contact_id, None) is not None

    async def list_whitelist(self, owner_id: str) -> list[WhitelistEntry]:
        return list(self._whitelist.get(owner_id, {}).values())

    async def is_whitelisted(self, owner_id: str, contact_id: str) -> bool:
        return contact_id in self._whitelist.get(owner_id, {})

    # -- Pending replies ---------------------------------------------------

    async def save_pending(self, owner_id: str, pending: PendingReply) -> PendingReply:
        self._pending[owner_id][pending.id] = pending
        return pending

    async def get_pending(self, owner_id: str, reply_id: str) -> PendingReply | None:
        return self._pending.get(owner_id, {}).get(reply_id)

    async def list_pending(
        self, owner_id: str, only_queued: bool = False
    ) -> list[PendingReply]:
        items = sorted(
            self._pending.get(owner_id, {}).values(),
            key=lambda p: p.created_at,
            reverse=True,
        )
        if only_queued:
            from ..models import ReplyStatus

            items = [p for p in items if p.status is ReplyStatus.QUEUED]
        return items

    # -- Audit trail -------------------------------------------------------

    async def record_audit(self, owner_id: str, event: TwinAuditEvent) -> None:
        self._audit[owner_id].append(event)

    async def list_audit(self, owner_id: str, limit: int = 100) -> list[TwinAuditEvent]:
        items = list(self._audit.get(owner_id, ()))
        items.reverse()  # newest first
        return items[:limit] if limit else items

    # -- Runtime control ---------------------------------------------------

    async def set_paused(self, owner_id: str, paused: bool) -> None:
        self._paused[owner_id] = paused

    async def is_paused(self, owner_id: str) -> bool:
        return self._paused.get(owner_id, False)

    # -- Inbound idempotency ----------------------------------------------

    async def mark_seen(self, owner_id: str, message_id: str) -> bool:
        seen = self._seen[owner_id]
        if message_id in seen:
            return False
        seen[message_id] = None
        while len(seen) > MAX_SEEN_PER_OWNER:
            seen.popitem(last=False)  # evict oldest
        return True


__all__ = ["InMemoryTwinStore"]

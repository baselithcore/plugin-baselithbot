"""Durable Postgres-backed :class:`TwinStore` (opt-in).

A compact single-table design: every record is a JSONB blob keyed by
``(owner_id, kind, item_key)``. This keeps the durable backend small enough to
stay well under the file-size cap while remaining a faithful, queryable mirror
of the in-memory store. It reuses the platform's shared async connection pool so
timezone handling and pooling come for free.

Selected only when ``persistence: postgres`` is configured; the in-memory
backend remains the default and the test target.
"""

from __future__ import annotations

import json
from typing import Any

from core.observability.logging import get_logger

from ..audit.models import TwinAuditEvent
from ..gateway.models import InboundMessage
from ..models import PendingReply, ReplyStatus, SalientFact, WhitelistEntry
from ..style.models import StyleProfile

logger = get_logger(__name__)

_TABLE = "baselith_twin_items"
SCHEMA_DDL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    owner_id   TEXT        NOT NULL,
    kind       TEXT        NOT NULL,
    item_key   TEXT        NOT NULL,
    blob       JSONB       NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner_id, kind, item_key)
);
CREATE INDEX IF NOT EXISTS idx_twin_items_kind
    ON {_TABLE} (owner_id, kind, created_at);
"""


class PostgresTwinStore:
    """JSONB-blob persistence satisfying the :class:`TwinStore` Protocol."""

    async def initialize(self) -> None:
        """Create the backing table and index if absent."""
        from core.db.connection import get_async_cursor

        async with get_async_cursor() as cur:
            await cur.execute(SCHEMA_DDL)

    async def _upsert(self, owner_id: str, kind: str, key: str, model: Any) -> None:
        from core.db.connection import get_async_cursor
        from psycopg.types.json import Jsonb

        async with get_async_cursor() as cur:
            await cur.execute(
                f"INSERT INTO {_TABLE} (owner_id, kind, item_key, blob) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (owner_id, kind, item_key) DO UPDATE SET blob = EXCLUDED.blob",
                (owner_id, kind, key, Jsonb(model.model_dump(mode="json"))),
            )

    async def _rows(self, owner_id: str, kind: str) -> list[dict[str, Any]]:
        from core.db.connection import get_async_cursor
        from psycopg.rows import dict_row

        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore[call-overload]
            await cur.execute(
                f"SELECT blob FROM {_TABLE} WHERE owner_id = %s AND kind = %s "
                "ORDER BY created_at",
                (owner_id, kind),
            )
            return [r["blob"] for r in await cur.fetchall()]

    @staticmethod
    def _loads(blob: Any) -> dict[str, Any]:
        return blob if isinstance(blob, dict) else json.loads(blob)

    # -- Message log -------------------------------------------------------

    async def add_message(self, owner_id: str, message: InboundMessage) -> None:
        await self._upsert(owner_id, "message", message.id, message)

    async def recent_messages(
        self, owner_id: str, contact_id: str | None = None, limit: int = 50
    ) -> list[InboundMessage]:
        items = [
            InboundMessage(**self._loads(b))
            for b in await self._rows(owner_id, "message")
        ]
        if contact_id is not None:
            items = [m for m in items if m.contact_id == contact_id]
        return items[-limit:] if limit else items

    async def owner_messages(self, owner_id: str) -> list[InboundMessage]:
        items = [
            InboundMessage(**self._loads(b))
            for b in await self._rows(owner_id, "message")
        ]
        return [m for m in items if m.from_me]

    # -- Style profile -----------------------------------------------------

    async def save_style(self, owner_id: str, profile: StyleProfile) -> None:
        await self._upsert(owner_id, "style", "current", profile)

    async def get_style(self, owner_id: str) -> StyleProfile | None:
        rows = await self._rows(owner_id, "style")
        return StyleProfile(**self._loads(rows[-1])) if rows else None

    # -- Salient facts -----------------------------------------------------

    async def add_fact(self, owner_id: str, fact: SalientFact) -> SalientFact:
        await self._upsert(owner_id, "fact", fact.id, fact)
        return fact

    async def list_facts(
        self, owner_id: str, contact_id: str | None = None
    ) -> list[SalientFact]:
        items = [
            SalientFact(**self._loads(b)) for b in await self._rows(owner_id, "fact")
        ]
        if contact_id is not None:
            items = [f for f in items if f.contact_id == contact_id]
        return items

    # -- Whitelist ---------------------------------------------------------

    async def add_whitelist(self, owner_id: str, entry: WhitelistEntry) -> None:
        await self._upsert(owner_id, "whitelist", entry.contact_id, entry)

    async def remove_whitelist(self, owner_id: str, contact_id: str) -> bool:
        from core.db.connection import get_async_cursor

        async with get_async_cursor() as cur:
            await cur.execute(
                f"DELETE FROM {_TABLE} WHERE owner_id = %s AND kind = 'whitelist' "
                "AND item_key = %s",
                (owner_id, contact_id),
            )
            return cur.rowcount > 0

    async def list_whitelist(self, owner_id: str) -> list[WhitelistEntry]:
        return [
            WhitelistEntry(**self._loads(b))
            for b in await self._rows(owner_id, "whitelist")
        ]

    async def is_whitelisted(self, owner_id: str, contact_id: str) -> bool:
        return any(
            e.contact_id == contact_id for e in await self.list_whitelist(owner_id)
        )

    # -- Pending replies ---------------------------------------------------

    async def save_pending(self, owner_id: str, pending: PendingReply) -> PendingReply:
        await self._upsert(owner_id, "pending", pending.id, pending)
        return pending

    async def get_pending(self, owner_id: str, reply_id: str) -> PendingReply | None:
        for b in await self._rows(owner_id, "pending"):
            data = self._loads(b)
            if data.get("id") == reply_id:
                return PendingReply(**data)
        return None

    async def list_pending(
        self, owner_id: str, only_queued: bool = False
    ) -> list[PendingReply]:
        items = [
            PendingReply(**self._loads(b))
            for b in await self._rows(owner_id, "pending")
        ]
        items.sort(key=lambda p: p.created_at, reverse=True)
        if only_queued:
            items = [p for p in items if p.status is ReplyStatus.QUEUED]
        return items

    # -- Audit trail (append-only) ----------------------------------------

    async def record_audit(self, owner_id: str, event: TwinAuditEvent) -> None:
        await self._upsert(owner_id, "audit", event.id, event)

    async def list_audit(self, owner_id: str, limit: int = 100) -> list[TwinAuditEvent]:
        items = [
            TwinAuditEvent(**self._loads(b))
            for b in await self._rows(owner_id, "audit")
        ]
        items.sort(key=lambda e: e.at, reverse=True)
        return items[:limit] if limit else items

    # -- Runtime control ---------------------------------------------------

    async def set_paused(self, owner_id: str, paused: bool) -> None:
        from core.db.connection import get_async_cursor
        from psycopg.types.json import Jsonb

        async with get_async_cursor() as cur:
            await cur.execute(
                f"INSERT INTO {_TABLE} (owner_id, kind, item_key, blob) "
                "VALUES (%s, 'control', 'paused', %s) "
                "ON CONFLICT (owner_id, kind, item_key) DO UPDATE SET blob = EXCLUDED.blob",
                (owner_id, Jsonb({"paused": paused})),
            )

    async def is_paused(self, owner_id: str) -> bool:
        rows = await self._rows(owner_id, "control")
        return bool(self._loads(rows[-1]).get("paused")) if rows else False

    # -- Inbound idempotency ----------------------------------------------

    async def mark_seen(self, owner_id: str, message_id: str) -> bool:
        from core.db.connection import get_async_cursor
        from psycopg.types.json import Jsonb

        async with get_async_cursor() as cur:
            await cur.execute(
                f"INSERT INTO {_TABLE} (owner_id, kind, item_key, blob) "
                "VALUES (%s, 'seen', %s, %s) "
                "ON CONFLICT (owner_id, kind, item_key) DO NOTHING",
                (owner_id, message_id, Jsonb({})),
            )
            return cur.rowcount > 0


__all__ = ["PostgresTwinStore", "SCHEMA_DDL"]

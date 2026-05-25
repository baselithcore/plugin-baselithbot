"""CRUD conversations + messages.

Source of truth per la chat history (sostituisce
``localStorage.llm-wiki:conversations`` lato frontend). Tutte le query
sono RLS-aware: il filtro ``WHERE tenant_id = ...`` è IMPLICITO via le
policy della migration 006 — qui passiamo solo gli scope-narrowing
applicativi (per-conversazione, per-utente).

Struttura ritorno
=================

Conversations: ``{id, title, pinned, title_locked, created_at,
updated_at, message_count}``. ``message_count`` calcolato via subquery
per evitare JOIN espliciti su list (N+1 mitigato da indice
``idx_messages_conversation``).

Messages: ``{id, role, content, sources, metadata, created_at}``.
``sources`` è il JSONB serializzato dal RAG agent; opaque per il DB.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from llm_wiki import config
from llm_wiki.auth.tenant_context import require_tenant_id
from llm_wiki.db.connection import get_connection

# --- helpers ---------------------------------------------------------------


def _format_conversation(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ("id", "user_id", "tenant_id"):
        if key in result and result[key] is not None:
            result[key] = str(result[key])
    for key in ("created_at", "updated_at"):
        val = result.get(key)
        if val is not None and hasattr(val, "isoformat"):
            result[key] = val.isoformat()
    if "message_count" in result and result["message_count"] is not None:
        result["message_count"] = int(result["message_count"])
    return result


def _format_message(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ("id", "conversation_id", "tenant_id"):
        if key in result and result[key] is not None:
            result[key] = str(result[key])
    val = result.get("created_at")
    if val is not None and hasattr(val, "isoformat"):
        result["created_at"] = val.isoformat()
    # JSONB già dict da psycopg3.
    return result


# --- conversations ---------------------------------------------------------


def create_conversation(
    *,
    user_id: str,
    title: str = "Nuova conversazione",
) -> dict[str, Any]:
    """Crea conversation per l'utente. Tenant ricavato dal contextvar
    (RLS-enforced)."""
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")
    from psycopg.rows import dict_row

    tenant_id = require_tenant_id()
    cid = str(uuid.uuid4())
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO conversations
                    (id, tenant_id, user_id, title)
                VALUES (%s, %s, %s, %s)
                RETURNING id, tenant_id, user_id, title, title_locked,
                          pinned, created_at, updated_at
                """,
                (cid, tenant_id, user_id, title.strip() or "Nuova conversazione"),
            )
            row = cur.fetchone()
        conn.commit()
    out = _format_conversation(row) if row else {}
    out["message_count"] = 0
    return out


def list_conversations(*, user_id: str) -> list[dict[str, Any]]:
    """Lista conversations dell'utente con ``message_count``. Ordine:
    pinned-first, poi updated_at desc."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT c.id, c.tenant_id, c.user_id, c.title,
                       c.title_locked, c.pinned,
                       c.created_at, c.updated_at,
                       (SELECT COUNT(*) FROM messages m
                        WHERE m.conversation_id = c.id) AS message_count
                FROM conversations c
                WHERE c.user_id = %s
                ORDER BY c.pinned DESC, c.updated_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        conn.rollback()
    return [_format_conversation(r) for r in rows]


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT c.id, c.tenant_id, c.user_id, c.title,
                       c.title_locked, c.pinned,
                       c.created_at, c.updated_at,
                       (SELECT COUNT(*) FROM messages m
                        WHERE m.conversation_id = c.id) AS message_count
                FROM conversations c
                WHERE c.id = %s
                """,
                (conversation_id,),
            )
            row = cur.fetchone()
        conn.rollback()
    return _format_conversation(row) if row else None


def update_conversation(
    conversation_id: str,
    *,
    title: str | None = None,
    pinned: bool | None = None,
    title_locked: bool | None = None,
) -> dict[str, Any] | None:
    """Update parziale. Trigger ``trg_conversations_updated_at`` rinfresca
    il timestamp."""
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    require_tenant_id()
    updates: list[str] = []
    params: list[Any] = []
    if title is not None:
        updates.append("title = %s")
        params.append(title.strip() or "Nuova conversazione")
    if pinned is not None:
        updates.append("pinned = %s")
        params.append(pinned)
    if title_locked is not None:
        updates.append("title_locked = %s")
        params.append(title_locked)

    if not updates:
        return get_conversation(conversation_id)

    params.append(conversation_id)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # `updates` è una whitelist locale di assegnazioni "col = %s"
            # costruite dall'handler — nessun input utente entra nella stringa.
            # Tutti i valori sono bound via `params`.
            cur.execute(
                f"UPDATE conversations SET {', '.join(updates)} "  # nosec B608
                "WHERE id = %s "
                "RETURNING id, tenant_id, user_id, title, title_locked, "
                "pinned, created_at, updated_at",
                params,
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        return None
    out = _format_conversation(row)
    # message_count non incluso nella RETURNING — fetch separato è oneroso,
    # il chiamante può rifare get_conversation se serve. Skip per perf.
    return out


def delete_conversation(conversation_id: str) -> bool:
    """ON DELETE CASCADE pulisce messages."""
    if not config.POSTGRES_ENABLED:
        return False
    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM conversations WHERE id = %s",
                (conversation_id,),
            )
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


# --- messages --------------------------------------------------------------


def append_message(
    *,
    conversation_id: str,
    role: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append turno. Auto-aggiorna ``conversations.updated_at`` via
    UPDATE esplicito (il trigger 003 si attiva su UPDATE conversations,
    non su INSERT messages — semantica desiderata).
    """
    if role not in ("user", "assistant", "system"):
        raise ValueError(f"role non valido: {role!r}")
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")

    from psycopg.rows import dict_row

    tenant_id = require_tenant_id()
    mid = str(uuid.uuid4())
    sources_json = json.dumps(sources) if sources is not None else None
    metadata_json = json.dumps(metadata or {})

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO messages
                    (id, conversation_id, tenant_id, role, content,
                     sources, metadata)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                RETURNING id, conversation_id, tenant_id, role, content,
                          sources, metadata, created_at
                """,
                (
                    mid,
                    conversation_id,
                    tenant_id,
                    role,
                    content,
                    sources_json,
                    metadata_json,
                ),
            )
            row = cur.fetchone()
            # Touch updated_at della conversation (no NOOP perché campo
            # arbitrario forza il trigger BEFORE UPDATE).
            cur.execute(
                "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
                (conversation_id,),
            )
        conn.commit()
    return _format_message(row) if row else {}


def list_messages(
    *,
    conversation_id: str,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, conversation_id, tenant_id, role, content,
                       sources, metadata, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                LIMIT %s OFFSET %s
                """,
                (conversation_id, max(1, min(limit, 1000)), max(0, offset)),
            )
            rows = cur.fetchall()
        conn.rollback()
    return [_format_message(r) for r in rows]


def delete_messages_from(
    *,
    conversation_id: str,
    from_message_id: str,
) -> int:
    """Cancella ``from_message_id`` e tutti i successivi della conversation.

    Usato da regenerate/editAndResend lato frontend: l'utente tronca
    locale + chiede al backend di mantenere la stessa history. Senza
    questa cancellazione il prossimo turno vedrebbe history "vecchia"
    nel context (latest_turns include i turni rimossi client-side).

    Restituisce il numero di righe cancellate.
    """
    if not config.POSTGRES_ENABLED:
        return 0
    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM messages
                WHERE conversation_id = %s
                  AND created_at >= (
                    SELECT created_at FROM messages
                    WHERE id = %s AND conversation_id = %s
                  )
                """,
                (conversation_id, from_message_id, conversation_id),
            )
            n = cur.rowcount
            # Touch updated_at — il chat next vedrà la conv meno recente
            # senza i turni rimossi.
            cur.execute(
                "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
                (conversation_id,),
            )
        conn.commit()
    return n


def latest_turns(
    *,
    conversation_id: str,
    max_turns: int = 6,
) -> list[dict[str, Any]]:
    """Ultimi N turni in ordine cronologico crescente — usato dal RAG
    agent per costruire history context."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (conversation_id, max(1, max_turns * 2)),
            )
            rows = cur.fetchall()
        conn.rollback()
    rows.reverse()
    return [_format_message(r) for r in rows]


__all__ = [
    "create_conversation",
    "list_conversations",
    "get_conversation",
    "update_conversation",
    "delete_conversation",
    "append_message",
    "list_messages",
    "delete_messages_from",
    "latest_turns",
]

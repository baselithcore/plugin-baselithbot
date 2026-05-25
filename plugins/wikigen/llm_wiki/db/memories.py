"""CRUD metadata memorie utente.

Post-migration 019 la tabella ``memories`` tiene **solo metadata**:
id, tenant_id, user_id, kind, key, value, metadata, timestamps. Lo
storage vettoriale è demandato a Qdrant via
:mod:`llm_wiki.memories.store.MemoriesStore`, che riusa il
``VectorStoreService`` di core.

Le tre funzioni storiche ``create_memory`` / ``upsert_preference`` /
``search_similar`` accettavano un ``embedding: Sequence[float]`` —
quel parametro è scomparso. Le funzioni vettoriali vivono in
``llm_wiki.memories.store``; questo modulo è puramente Postgres CRUD.

Tassonomia ``kind`` invariata:

- ``note``: testo libero ("Ricorda che preferisco risposte concise.")
- ``fact``: affermazione dichiarativa ("Lavoro come ingegnere DevOps")
- ``preference``: key/value normalizzato ("language=it", "tone=formal")
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from llm_wiki import config
from llm_wiki.auth.tenant_context import require_tenant_id
from llm_wiki.db.connection import get_connection

# --- helpers ---------------------------------------------------------------


def _format_memory(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ("id", "tenant_id", "user_id"):
        if key in result and result[key] is not None:
            result[key] = str(result[key])
    for key in ("created_at", "updated_at"):
        val = result.get(key)
        if val is not None and hasattr(val, "isoformat"):
            result[key] = val.isoformat()
    return result


# --- CRUD ------------------------------------------------------------------


def create_memory_row(
    *,
    memory_id: str | None = None,
    user_id: str,
    value: str,
    kind: str = "note",
    key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inserisce solo la riga Postgres. L'embedding viene indicizzato in
    Qdrant separatamente da :class:`MemoriesStore`. La doppia scrittura
    è coordinata lì (Postgres prima, Qdrant subito dopo)."""
    if kind not in ("note", "fact", "preference"):
        raise ValueError(f"kind non valido: {kind!r}")
    if kind == "preference" and not key:
        raise ValueError("kind='preference' richiede key non vuota")
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")

    from psycopg.rows import dict_row

    tenant_id = require_tenant_id()
    mid = memory_id or str(uuid.uuid4())
    metadata_json = json.dumps(metadata or {})

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO memories
                    (id, tenant_id, user_id, kind, key, value, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id, tenant_id, user_id, kind, key, value,
                          metadata, created_at, updated_at
                """,
                (
                    mid,
                    tenant_id,
                    user_id,
                    kind,
                    (key or "").strip() or None,
                    value.strip(),
                    metadata_json,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return _format_memory(row) if row else {}


def upsert_preference_row(
    *,
    user_id: str,
    key: str,
    value: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Set-or-replace su unique ``idx_memories_preference_unique``.

    Ritorna ``(record, replaced)`` — ``replaced=True`` se ha sovrascritto
    una preferenza esistente (l'embedding precedente in Qdrant va
    eliminato dal chiamante via ``MemoriesStore.delete`` sul vecchio id).
    """
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")
    from psycopg.rows import dict_row

    tenant_id = require_tenant_id()
    mid = str(uuid.uuid4())
    metadata_json = json.dumps(metadata or {})

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Cattura l'id pre-esistente se presente: serve al chiamante
            # per ripulire il vecchio vettore Qdrant prima di reindicizzare
            # il nuovo.
            cur.execute(
                """
                SELECT id::text AS id FROM memories
                WHERE tenant_id = %s
                  AND kind = 'preference' AND key = %s
                """,
                (tenant_id, key.strip()),
            )
            prev = cur.fetchone()
            prev_id = prev["id"] if prev else None

            cur.execute(
                """
                INSERT INTO memories
                    (id, tenant_id, user_id, kind, key, value, metadata)
                VALUES (%s, %s, %s, 'preference', %s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, key)
                    WHERE kind = 'preference' AND key IS NOT NULL
                DO UPDATE SET
                    value = EXCLUDED.value,
                    metadata = EXCLUDED.metadata
                RETURNING id, tenant_id, user_id, kind, key, value,
                          metadata, created_at, updated_at
                """,
                (
                    mid,
                    tenant_id,
                    user_id,
                    key.strip(),
                    value.strip(),
                    metadata_json,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    record = _format_memory(row) if row else {}
    # replaced=True se l'id finale coincide con quello pre-esistente.
    replaced = bool(prev_id) and record.get("id") == prev_id
    return record, replaced


def list_memories(
    *,
    user_id: str,
    kind: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    require_tenant_id()
    where = ["user_id = %s"]
    params: list[Any] = [user_id]
    if kind:
        where.append("kind = %s")
        params.append(kind)
    params.append(max(1, min(limit, 1000)))

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT id, tenant_id, user_id, kind, key, value,
                       metadata, created_at, updated_at
                FROM memories
                WHERE {" AND ".join(where)}
                ORDER BY updated_at DESC
                LIMIT %s
                """,  # nosec B608 — `where` whitelist locale, valori in params
                params,
            )
            rows = cur.fetchall()
        conn.rollback()
    return [_format_memory(r) for r in rows]


def get_memory(memory_id: str) -> dict[str, Any] | None:
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, tenant_id, user_id, kind, key, value,
                       metadata, created_at, updated_at
                FROM memories WHERE id = %s
                """,
                (memory_id,),
            )
            row = cur.fetchone()
        conn.rollback()
    return _format_memory(row) if row else None


def get_memories_by_ids(memory_ids: list[str]) -> list[dict[str, Any]]:
    """Batch fetch usato dalla similarity search Qdrant per joinare i
    top-K hit con il metadata Postgres. RLS continua a filtrare per
    ``tenant_id`` lato DB anche su ``IN``."""
    if not config.POSTGRES_ENABLED or not memory_ids:
        return []
    from psycopg.rows import dict_row

    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, tenant_id, user_id, kind, key, value,
                       metadata, created_at, updated_at
                FROM memories WHERE id = ANY(%s::uuid[])
                """,
                (memory_ids,),
            )
            rows = cur.fetchall()
        conn.rollback()
    return [_format_memory(r) for r in rows]


def delete_memory_row(memory_id: str) -> bool:
    if not config.POSTGRES_ENABLED:
        return False
    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


__all__ = [
    "create_memory_row",
    "upsert_preference_row",
    "list_memories",
    "get_memory",
    "get_memories_by_ids",
    "delete_memory_row",
]

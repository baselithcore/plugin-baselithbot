"""CRUD memorie utente — RAG personale via pgvector.

Memorie sono "fatti dichiarati dall'utente" che il RAG agent recupera
PRIMA di rispondere. Tassonomia leggera:

- ``note``: testo libero ("Ricorda che preferisco risposte concise.")
- ``fact``: affermazione dichiarativa ("Lavoro come ingegnere DevOps")
- ``preference``: key/value normalizzato ("language=it", "tone=formal")

Lookup ibrido a runtime:

1. Wiki Qdrant (SHARED) → top-K wiki chunks.
2. ``memories`` Postgres → top-K via pgvector cosine + filtro
   ``tenant_id=current`` (RLS garantisce hard filter al DB).
3. Merge + rerank → context al LLM.

Embedding: BGE-M3 1024-dim. Generazione delegata al chiamante (router
POST /api/memories chiama ``vectorstore.embedder.get_embedder()`` —
qui questa modulo non importa l'embedder per evitare dep heavy).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any

from llm_wiki import config
from llm_wiki.auth.tenant_context import require_tenant_id
from llm_wiki.db.connection import get_connection

# --- helpers ---------------------------------------------------------------


def _format_memory(row: dict[str, Any], *, include_embedding: bool = False) -> dict[str, Any]:
    result = dict(row)
    for key in ("id", "tenant_id", "user_id"):
        if key in result and result[key] is not None:
            result[key] = str(result[key])
    for key in ("created_at", "updated_at"):
        val = result.get(key)
        if val is not None and hasattr(val, "isoformat"):
            result[key] = val.isoformat()
    if not include_embedding:
        result.pop("embedding", None)
    if "similarity" in result and result["similarity"] is not None:
        result["similarity"] = float(result["similarity"])
    return result


def _vector_literal(embedding: Sequence[float]) -> str:
    """Serialize a list[float] in formato pgvector text input.

    pgvector accetta letterale ``'[1.0,2.0,...]'``. Bind diretto via
    psycopg3 funziona se vector_register è chiamato — qui usiamo cast
    esplicito ``::vector`` che evita la dipendenza extra ``pgvector``.
    """
    return "[" + ",".join(f"{float(x):.7f}" for x in embedding) + "]"


# --- CRUD ------------------------------------------------------------------


def create_memory(
    *,
    user_id: str,
    value: str,
    embedding: Sequence[float],
    kind: str = "note",
    key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Crea memoria. Embedding obbligatorio: il chiamante è responsabile
    di calcolarlo (sincrono — stessa request che crea la riga).

    Per ``kind='preference'`` l'unique index su ``(tenant_id, key)``
    impone una sola memoria per chiave per tenant. Usa
    :func:`upsert_preference` se vuoi semantica "set or replace".
    """
    if kind not in ("note", "fact", "preference"):
        raise ValueError(f"kind non valido: {kind!r}")
    if kind == "preference" and not key:
        raise ValueError("kind='preference' richiede key non vuota")
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")

    from psycopg.rows import dict_row

    tenant_id = require_tenant_id()
    mid = str(uuid.uuid4())
    metadata_json = json.dumps(metadata or {})
    vec_lit = _vector_literal(embedding)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO memories
                    (id, tenant_id, user_id, kind, key, value,
                     embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb)
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
                    vec_lit,
                    metadata_json,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return _format_memory(row) if row else {}


def upsert_preference(
    *,
    user_id: str,
    key: str,
    value: str,
    embedding: Sequence[float],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Set-or-replace preferenza. Usa l'unique constraint
    ``idx_memories_preference_unique`` per ON CONFLICT."""
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")
    from psycopg.rows import dict_row

    tenant_id = require_tenant_id()
    mid = str(uuid.uuid4())
    metadata_json = json.dumps(metadata or {})
    vec_lit = _vector_literal(embedding)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO memories
                    (id, tenant_id, user_id, kind, key, value,
                     embedding, metadata)
                VALUES (%s, %s, %s, 'preference', %s, %s,
                        %s::vector, %s::jsonb)
                ON CONFLICT (tenant_id, key)
                    WHERE kind = 'preference' AND key IS NOT NULL
                DO UPDATE SET
                    value = EXCLUDED.value,
                    embedding = EXCLUDED.embedding,
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
                    vec_lit,
                    metadata_json,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return _format_memory(row) if row else {}


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
            # `where` whitelist locale di clausole "col = %s"; valori bound via params.
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


def delete_memory(memory_id: str) -> bool:
    if not config.POSTGRES_ENABLED:
        return False
    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


def search_similar(
    *,
    user_id: str | None,
    query_embedding: Sequence[float],
    top_k: int = 5,
    kind: str | None = None,
    min_similarity: float = 0.0,
) -> list[dict[str, Any]]:
    """Top-K per similarità coseno. ``user_id=None`` = cerca su tutte
    le memorie del tenant (raro: di solito si filtra per utente).

    Restituisce dict con campo extra ``similarity`` (1 - cosine_distance,
    range [-1, 1] ma con embedding normalizzati BGE-M3 effettivamente
    [0, 1]). Filtro ``min_similarity`` lato Postgres prima del LIMIT
    riduce noise nel context.
    """
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    require_tenant_id()
    where = ["1 = 1"]
    params: list[Any] = []
    if user_id:
        where.append("user_id = %s")
        params.append(user_id)
    if kind:
        where.append("kind = %s")
        params.append(kind)
    vec_lit = _vector_literal(query_embedding)
    # cosine distance (<=>) nativo pgvector. similarity = 1 - distance.
    where.append("(1 - (embedding <=> %s::vector)) >= %s")
    params.extend([vec_lit, float(min_similarity)])
    # Order by distance asc = most similar first. Aggiungiamo il vector
    # ANCHE qui per usare l'indice HNSW.
    params.append(vec_lit)
    params.append(max(1, min(top_k, 50)))

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # `where` whitelist locale; valori bound via params.
            cur.execute(
                f"""
                SELECT id, tenant_id, user_id, kind, key, value,
                       metadata, created_at, updated_at,
                       (1 - (embedding <=> %s::vector)) AS similarity
                FROM memories
                WHERE {" AND ".join(where)}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,  # nosec B608 — `where` whitelist locale, valori in params
                # Attenzione: il primo %s::vector nel SELECT serve per
                # calcolare similarity; dobbiamo passarlo come PRIMO
                # parametro, poi gli altri della WHERE/ORDER BY.
                [vec_lit, *params],
            )
            rows = cur.fetchall()
        conn.rollback()
    return [_format_memory(r) for r in rows]


__all__ = [
    "create_memory",
    "upsert_preference",
    "list_memories",
    "get_memory",
    "delete_memory",
    "search_similar",
]

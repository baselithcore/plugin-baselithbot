"""CRUD feedback — write/list/get/delete + update_triage (mig 018).

Tenant scoping via RLS (mig 006): nessun ``WHERE tenant_id = ...``
sparso, basta che il context tenant sia popolato. ``require_tenant_id``
fallisce loud se chiamato fuori da una richiesta autenticata.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from llm_wiki import config
from llm_wiki.auth.tenant_context import require_tenant_id
from llm_wiki.db.connection import get_connection

from ._format import ALLOWED_STATUSES, format_feedback, normalize_tags

# Colonna selection condivisa con il LEFT JOIN su messages per
# esporre ``conversation_id`` (deep-link UI). ``users`` join già
# fornisce l'email; aggiungiamo anche la display del resolver.
_ADMIN_SELECT = """
    SELECT f.id, f.tenant_id, f.user_id, f.message_id,
           f.rating, f.reason, f.question, f.answer,
           f.sources, f.created_at,
           f.status, f.tags, f.resolution_note,
           f.resolved_by_user_id, f.resolved_at,
           u.email AS user_email,
           r.email AS resolved_by_email,
           m.conversation_id AS conversation_id
    FROM feedback f
    LEFT JOIN users u ON u.id = f.user_id
    LEFT JOIN users r ON r.id = f.resolved_by_user_id
    LEFT JOIN messages m ON m.id = f.message_id
"""


def write_feedback(
    *,
    user_id: str,
    rating: str,
    message_id: str | None = None,
    reason: str | None = None,
    question: str | None = None,
    answer: str | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if rating not in ("up", "down"):
        raise ValueError(f"rating non valido: {rating!r}")
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")

    from psycopg.rows import dict_row

    tenant_id = require_tenant_id()
    fid = str(uuid.uuid4())
    sources_json = json.dumps(sources) if sources is not None else None

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO feedback
                    (id, tenant_id, user_id, message_id, rating,
                     reason, question, answer, sources)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id, tenant_id, user_id, message_id, rating,
                          reason, question, answer, sources, created_at,
                          status, tags, resolution_note,
                          resolved_by_user_id, resolved_at
                """,
                (
                    fid,
                    tenant_id,
                    user_id,
                    message_id,
                    rating,
                    reason,
                    question,
                    answer,
                    sources_json,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return format_feedback(row) if row else {}


def list_feedback(
    *,
    user_id: str | None = None,
    rating: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Lista feedback per-utente (vista personale `GET /api/feedback`)."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    require_tenant_id()
    where = ["1 = 1"]
    params: list[Any] = []
    if user_id:
        where.append("user_id = %s")
        params.append(user_id)
    if rating in ("up", "down"):
        where.append("rating = %s")
        params.append(rating)
    params.append(max(1, min(limit, 1000)))

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT id, tenant_id, user_id, message_id, rating,
                       reason, question, answer, sources, created_at,
                       status, tags, resolution_note,
                       resolved_by_user_id, resolved_at
                FROM feedback
                WHERE {" AND ".join(where)}
                ORDER BY created_at DESC
                LIMIT %s
                """,  # nosec B608 — whitelist locale, valori bound
                params,
            )
            rows = cur.fetchall()
        conn.rollback()
    return [format_feedback(r) for r in rows]


def _admin_where_clause(
    *,
    rating: str | None,
    user_id: str | None,
    message_id: str | None,
    since: datetime | None,
    until: datetime | None,
    search: str | None,
    status: str | None,
    tag: str | None,
) -> tuple[list[str], list[Any]]:
    where: list[str] = ["1 = 1"]
    params: list[Any] = []
    if rating in ("up", "down"):
        where.append("f.rating = %s")
        params.append(rating)
    if user_id:
        where.append("f.user_id = %s")
        params.append(user_id)
    if message_id:
        where.append("f.message_id = %s")
        params.append(message_id)
    if since is not None:
        where.append("f.created_at >= %s")
        params.append(since)
    if until is not None:
        where.append("f.created_at <= %s")
        params.append(until)
    if status and status in ALLOWED_STATUSES:
        where.append("f.status = %s")
        params.append(status)
    if tag:
        where.append("f.tags @> ARRAY[%s]::TEXT[]")
        params.append(tag.strip().lower())
    if search:
        like = f"%{search}%"
        where.append(
            "(f.question ILIKE %s OR f.answer ILIKE %s "
            "OR f.reason ILIKE %s OR f.resolution_note ILIKE %s)"
        )
        params.extend([like, like, like, like])
    return where, params


def list_feedback_admin(
    *,
    rating: str | None = None,
    user_id: str | None = None,
    message_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    search: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    if not config.POSTGRES_ENABLED:
        return ([], 0)
    from psycopg.rows import dict_row

    require_tenant_id()
    where, params = _admin_where_clause(
        rating=rating,
        user_id=user_id,
        message_id=message_id,
        since=since,
        until=until,
        search=search,
        status=status,
        tag=tag,
    )
    where_sql = " AND ".join(where)
    page_params = list(params)
    page_params.extend([max(1, min(limit, 1000)), max(0, offset)])

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                {_ADMIN_SELECT}
                WHERE {where_sql}
                ORDER BY f.created_at DESC
                LIMIT %s OFFSET %s
                """,  # nosec B608
                page_params,
            )
            rows = cur.fetchall()
            cur.execute(
                f"""
                SELECT COUNT(*) AS n FROM feedback f
                WHERE {where_sql}
                """,  # nosec B608
                params,
            )
            total_row = cur.fetchone()
        conn.rollback()
    total = int(total_row["n"]) if total_row else 0
    return ([format_feedback(r) for r in rows], total)


def get_feedback_by_id(feedback_id: str) -> dict[str, Any] | None:
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"{_ADMIN_SELECT} WHERE f.id = %s",
                (feedback_id,),
            )
            row = cur.fetchone()
        conn.rollback()
    return format_feedback(row) if row else None


def delete_feedback(feedback_id: str) -> bool:
    if not config.POSTGRES_ENABLED:
        return False
    require_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE id = %s", (feedback_id,))
            deleted = cur.rowcount or 0
        conn.commit()
    return deleted > 0


def update_triage(
    feedback_id: str,
    *,
    actor_user_id: str,
    status: str | None = None,
    tags: list[str] | None = None,
    resolution_note: str | None = None,
) -> dict[str, Any] | None:
    """PATCH triage. Tutti i field opzionali — applichiamo solo i
    presenti (sentinel ``None`` = "non toccare", per delete del campo
    passare ``""`` su ``resolution_note`` o ``[]`` su ``tags``).

    Side-effect: quando ``status`` passa a ``resolved`` o ``dismissed``
    settiamo automaticamente ``resolved_by_user_id`` + ``resolved_at``;
    quando torna a ``open`` o ``triaged`` li nulliamo.
    """
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")
    if status is not None and status not in ALLOWED_STATUSES:
        raise ValueError(
            f"status non valido: {status!r}. Atteso uno di {sorted(ALLOWED_STATUSES)}."
        )

    from psycopg.rows import dict_row

    require_tenant_id()
    sets: list[str] = []
    params: list[Any] = []
    if status is not None:
        sets.append("status = %s")
        params.append(status)
        # auto-fill resolved_* coerente con lo stato.
        if status in ("resolved", "dismissed"):
            sets.append("resolved_by_user_id = %s")
            params.append(actor_user_id)
            sets.append("resolved_at = NOW()")
        else:
            sets.append("resolved_by_user_id = NULL")
            sets.append("resolved_at = NULL")
    if tags is not None:
        sets.append("tags = %s::TEXT[]")
        params.append(normalize_tags(tags))
    if resolution_note is not None:
        # Stringa vuota = clear; preserviamo None = "non toccare".
        sets.append("resolution_note = %s")
        params.append(resolution_note or None)
    if not sets:
        # No-op: ritorna lo stato corrente senza UPDATE.
        return get_feedback_by_id(feedback_id)

    params.append(feedback_id)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                UPDATE feedback
                SET {", ".join(sets)}
                WHERE id = %s
                """,  # nosec B608 — `sets` whitelist locale, valori bound
                params,
            )
            if (cur.rowcount or 0) == 0:
                conn.rollback()
                return None
        conn.commit()
    return get_feedback_by_id(feedback_id)


__all__ = [
    "write_feedback",
    "list_feedback",
    "list_feedback_admin",
    "get_feedback_by_id",
    "delete_feedback",
    "update_triage",
]

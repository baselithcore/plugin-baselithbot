"""CRUD tabella tenants.

Adattato da ``agent-jira/app/db/tenants.py``. Differenze:
- Niente ``ensure_*_schema()``: schema gestito esclusivamente da Alembic
  (single source of truth — il pattern agent-jira con CREATE TABLE in
  Python era retrocompat per pre-Alembic, qui partiamo già con migrations).
- Bypass a sicurezza: tutte le operazioni cross-tenant (lista, conteggio
  globale, lookup-by-slug-arbitrario) richiedono che il chiamante giri
  come superuser o `BYPASSRLS`. Da app code (`app_runtime`) sono ammesse
  solo letture/scritture sul tenant attivo del contextvar.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _serialize_settings(settings: dict[str, Any] | None) -> str:
    return json.dumps(settings or {})


def _format_tenant(row: dict[str, Any]) -> dict[str, Any]:
    """UUID → str, datetime → ISO 8601 string. JSONB già dict da psycopg3."""
    result = dict(row)
    if "id" in result and result["id"] is not None:
        result["id"] = str(result["id"])
    for key in ("created_at", "updated_at"):
        val = result.get(key)
        if val is not None and hasattr(val, "isoformat"):
            result[key] = val.isoformat()
    return result


def create_tenant(
    name: str,
    slug: str,
    *,
    plan: str = "free",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Crea un tenant standalone (caso raro: creazione via admin tool).

    Path normale = :func:`create_tenant_with_owner` in transazione singola.
    """
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato — create_tenant indisponibile.")

    from psycopg.rows import dict_row

    tenant_id = str(uuid.uuid4())
    now = _now_iso()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO tenants
                    (id, name, slug, plan, settings, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                RETURNING id, name, slug, plan, is_active, settings,
                          created_at, updated_at
                """,
                (
                    tenant_id,
                    name.strip(),
                    slug.strip().lower(),
                    plan,
                    _serialize_settings(settings),
                    now,
                    now,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return _format_tenant(row) if row else {}


def create_tenant_with_owner(
    *,
    tenant_name: str,
    tenant_slug: str,
    user_email: str,
    user_password_hash: str,
    user_display_name: str = "",
    plan: str = "free",
    role: str = "user",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Crea tenant + user owner in transazione atomica.

    Garantisce invariante 1:1 user↔tenant: se il commit user fallisce
    (email duplicata) il tenant è rollback-ato — niente tenant orfani.

    ``role`` di default ``"user"``. Il bootstrap admin del lifespan passa
    ``role="admin"``.

    Restituisce ``{"tenant": {...}, "user": {...}}``.
    Solleva ``psycopg.errors.UniqueViolation`` su email/slug duplicato.
    """
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")

    from psycopg.rows import dict_row

    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    now = _now_iso()

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO tenants
                        (id, name, slug, plan, settings, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                    RETURNING id, name, slug, plan, is_active, settings,
                              created_at, updated_at
                    """,
                    (
                        tenant_id,
                        tenant_name.strip(),
                        tenant_slug.strip().lower(),
                        plan,
                        _serialize_settings(settings),
                        now,
                        now,
                    ),
                )
                tenant_row = cur.fetchone()

                cur.execute(
                    """
                    INSERT INTO users
                        (id, email, password_hash, display_name,
                         tenant_id, role, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, email, display_name, tenant_id, role,
                              is_active, created_at
                    """,
                    (
                        user_id,
                        user_email.strip().lower(),
                        user_password_hash,
                        user_display_name.strip(),
                        tenant_id,
                        role,
                        now,
                    ),
                )
                user_row = cur.fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "tenant": _format_tenant(tenant_row) if tenant_row else {},
        "user": _format_user_from_join(user_row) if user_row else {},
    }


def _format_user_from_join(row: dict[str, Any]) -> dict[str, Any]:
    """Mirror di ``llm_wiki.db.users._format_user`` — tenuto qui locale
    per evitare import ciclico durante il bootstrap."""
    result = dict(row)
    result.pop("password_hash", None)
    for key in ("id", "tenant_id"):
        if key in result and result[key] is not None:
            result[key] = str(result[key])
    val = result.get("created_at")
    if val is not None and hasattr(val, "isoformat"):
        result["created_at"] = val.isoformat()
    return result


def get_tenant_by_id(tenant_id: str) -> dict[str, Any] | None:
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, name, slug, plan, is_active, settings, "
                "created_at, updated_at FROM tenants WHERE id = %s",
                (tenant_id,),
            )
            row = cur.fetchone()
        conn.rollback()
    return _format_tenant(row) if row else None


def get_tenant_by_slug(slug: str) -> dict[str, Any] | None:
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, name, slug, plan, is_active, settings, "
                "created_at, updated_at FROM tenants "
                "WHERE slug = %s AND is_active = TRUE",
                (slug.strip().lower(),),
            )
            row = cur.fetchone()
        conn.rollback()
    return _format_tenant(row) if row else None


def list_tenants(*, active_only: bool = True) -> list[dict[str, Any]]:
    """Lista tenants. Richiede ruolo bypass-RLS (admin/superuser)."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            query = (
                "SELECT id, name, slug, plan, is_active, settings, "
                "created_at, updated_at FROM tenants"
            )
            if active_only:
                query += " WHERE is_active = TRUE"
            query += " ORDER BY created_at ASC"
            cur.execute(query)
            rows = cur.fetchall()
        conn.rollback()
    return [_format_tenant(row) for row in rows]


def count_tenants(*, active_only: bool = True) -> int:
    if not config.POSTGRES_ENABLED:
        return 0
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                query = "SELECT COUNT(*) FROM tenants"
                if active_only:
                    query += " WHERE is_active = TRUE"
                cur.execute(query)
                row = cur.fetchone()
        finally:
            conn.rollback()
    return int(row[0]) if row else 0


def update_tenant(
    tenant_id: str,
    *,
    name: str | None = None,
    plan: str | None = None,
    is_active: bool | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Update parziale. ``updated_at`` aggiornato dal trigger 001."""
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    updates: list[str] = []
    params: list[Any] = []
    if name is not None:
        updates.append("name = %s")
        params.append(name.strip())
    if plan is not None:
        updates.append("plan = %s")
        params.append(plan)
    if is_active is not None:
        updates.append("is_active = %s")
        params.append(is_active)
    if settings is not None:
        updates.append("settings = %s::jsonb")
        params.append(_serialize_settings(settings))

    if not updates:
        return get_tenant_by_id(tenant_id)

    params.append(tenant_id)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # `updates` whitelist locale di "col = %s"; valori bound via params.
            cur.execute(
                f"UPDATE tenants SET {', '.join(updates)} WHERE id = %s "  # nosec B608
                "RETURNING id, name, slug, plan, is_active, settings, "
                "created_at, updated_at",
                params,
            )
            row = cur.fetchone()
        conn.commit()
    return _format_tenant(row) if row else None


def delete_tenant(tenant_id: str) -> bool:
    """Cancellazione hard. ON DELETE CASCADE pulisce users, conversations,
    messages, memories, feedback, refresh_tokens. Cleanup risorse esterne
    (filesystem wiki — N/A perché shared, Qdrant user_memories filter,
    Redis cache) è responsabilità del chiamante app-level."""
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


__all__ = [
    "create_tenant",
    "create_tenant_with_owner",
    "get_tenant_by_id",
    "get_tenant_by_slug",
    "list_tenants",
    "count_tenants",
    "update_tenant",
    "delete_tenant",
]

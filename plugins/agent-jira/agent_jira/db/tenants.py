"""
Gestione tenant per supporto multi-tenancy.
Ogni tenant rappresenta un'organizzazione isolata con le proprie risorse.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

from psycopg.rows import dict_row

from agent_jira.config import APP_TIMEZONE, APP_TIMEZONE_NAME, POSTGRES_ENABLED

from .connection import get_connection


def _now_iso() -> str:
    return datetime.datetime.now(APP_TIMEZONE).isoformat()


def ensure_tenant_schema() -> None:
    """Crea la tabella tenants se non esiste."""

    if not POSTGRES_ENABLED:
        return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    plan TEXT NOT NULL DEFAULT 'free',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    settings JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants (slug)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants (is_active) WHERE is_active = TRUE"
            )
        conn.commit()


def create_tenant(
    name: str,
    slug: str,
    *,
    plan: str = "free",
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Crea un nuovo tenant e restituisce il record creato."""

    tenant_id = str(uuid.uuid4())
    now = _now_iso()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                """
                INSERT INTO tenants (id, name, slug, plan, settings, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                RETURNING id, name, slug, plan, is_active, settings, created_at, updated_at
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
            row = cursor.fetchone()
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
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Crea tenant + utente owner in una singola transazione atomica.

    Garantisce l'invariante "1 tenant = 1 utente": se la creazione dell'utente
    fallisce (email duplicata, ecc.) il tenant NON viene creato, evitando
    tenant orfani.

    Il password_hash va fornito già hashato dal chiamante (vedi
    app.db.users.hash_password). Non accettiamo password in chiaro qui per
    ridurre la superficie d'errore.

    Restituisce: {"tenant": {...}, "user": {...}}
    Solleva: psycopg.errors.UniqueViolation in caso di conflitto.
    """
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    now = _now_iso()

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
                cursor.execute(
                    """
                    INSERT INTO tenants (id, name, slug, plan, settings, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                    RETURNING id, name, slug, plan, is_active, settings, created_at, updated_at
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
                tenant_row = cursor.fetchone()

                cursor.execute(
                    """
                    INSERT INTO users (id, email, password_hash, display_name, tenant_id, role, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, email, display_name, tenant_id, role, is_active, created_at
                    """,
                    (
                        user_id,
                        user_email.strip().lower(),
                        user_password_hash,
                        user_display_name.strip(),
                        tenant_id,
                        "admin",
                        now,
                    ),
                )
                user_row = cursor.fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "tenant": _format_tenant(tenant_row) if tenant_row else {},
        "user": _format_user_from_tenant_ctx(user_row) if user_row else {},
    }


def _format_user_from_tenant_ctx(row: Dict[str, Any]) -> Dict[str, Any]:
    """Helper di formattazione user coerente con app.db.users._format_user."""
    result = dict(row)
    result.pop("password_hash", None)
    for key in ("id", "tenant_id"):
        if key in result and result[key] is not None:
            result[key] = str(result[key])
    val = result.get("created_at")
    if val is not None and hasattr(val, "isoformat"):
        if val.tzinfo is None:
            val = val.replace(tzinfo=APP_TIMEZONE)
        else:
            val = val.astimezone(APP_TIMEZONE)
        result["created_at"] = val.isoformat()
    return result


def delete_tenant(tenant_id: str) -> bool:
    """
    Cancella definitivamente un tenant e tutti i dati tenant-scoped a livello DB.

    Grazie ai vincoli ON DELETE CASCADE introdotti dalla migration 005 e 002,
    la cancellazione del tenant propaga a:
      - users (ON DELETE CASCADE)
      - feedback (ON DELETE CASCADE dallo Sprint 2)

    Per Qdrant, FalkorDB, filesystem, cache Redis il cleanup è responsabilità
    del chiamante di livello applicativo (see app.routers.auth._purge_tenant_data).

    Restituisce True se il tenant esisteva ed è stato cancellato.
    """
    if not POSTGRES_ENABLED:
        return False

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
            deleted = cursor.rowcount > 0
        conn.commit()
    return deleted


def get_tenant_by_id(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Recupera un tenant per ID."""

    if not POSTGRES_ENABLED:
        return None

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                "SELECT id, name, slug, plan, is_active, settings, created_at, updated_at "
                "FROM tenants WHERE id = %s",
                (tenant_id,),
            )
            row = cursor.fetchone()
        conn.rollback()
    return _format_tenant(row) if row else None


def get_tenant_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Recupera un tenant per slug."""

    if not POSTGRES_ENABLED:
        return None

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                "SELECT id, name, slug, plan, is_active, settings, created_at, updated_at "
                "FROM tenants WHERE slug = %s AND is_active = TRUE",
                (slug.strip().lower(),),
            )
            row = cursor.fetchone()
        conn.rollback()
    return _format_tenant(row) if row else None


def list_tenants(*, active_only: bool = True) -> List[Dict[str, Any]]:
    """Restituisce la lista dei tenant."""

    if not POSTGRES_ENABLED:
        return []

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            query = (
                "SELECT id, name, slug, plan, is_active, settings, created_at, updated_at "
                "FROM tenants"
            )
            if active_only:
                query += " WHERE is_active = TRUE"
            query += " ORDER BY created_at ASC"
            cursor.execute(query)
            rows = cursor.fetchall()
        conn.rollback()
    return [_format_tenant(row) for row in rows]


def update_tenant(
    tenant_id: str,
    *,
    name: Optional[str] = None,
    plan: Optional[str] = None,
    is_active: Optional[bool] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Aggiorna un tenant esistente. Restituisce il record aggiornato."""

    updates = []
    params: List[Any] = []

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

    updates.append("updated_at = %s")
    params.append(_now_iso())
    params.append(tenant_id)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                f"UPDATE tenants SET {', '.join(updates)} WHERE id = %s "
                "RETURNING id, name, slug, plan, is_active, settings, created_at, updated_at",
                params,
            )
            row = cursor.fetchone()
        conn.commit()
    return _format_tenant(row) if row else None


def _serialize_settings(settings: Optional[Dict[str, Any]]) -> str:
    import json

    return json.dumps(settings or {})


def _format_tenant(row: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(row)
    # Converti UUID in stringa
    if "id" in result:
        result["id"] = str(result["id"])
    # Converti timestamps
    for key in ("created_at", "updated_at"):
        val = result.get(key)
        if val is not None and hasattr(val, "isoformat"):
            if val.tzinfo is None:
                val = val.replace(tzinfo=APP_TIMEZONE)
            else:
                val = val.astimezone(APP_TIMEZONE)
            result[key] = val.isoformat()
    return result

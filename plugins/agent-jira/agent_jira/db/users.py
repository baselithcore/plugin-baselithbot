"""
Gestione utenti per autenticazione built-in.
Progettato per essere sostituibile con un IdP esterno (Okta, Microsoft, ecc.).
"""

from __future__ import annotations

import datetime
import hashlib
import secrets
import uuid
from typing import Any, Dict, Optional

from psycopg.rows import dict_row

from agent_jira.config import APP_TIMEZONE, APP_TIMEZONE_NAME, POSTGRES_ENABLED

from .connection import get_connection

_PBKDF2_ITERATIONS = 260_000


def ensure_users_schema() -> None:
    """Crea la tabella users se non esiste."""

    if not POSTGRES_ENABLED:
        return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    tenant_id UUID REFERENCES tenants(id),
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_login_at TIMESTAMPTZ
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_tenant ON users (tenant_id)"
            )
        conn.commit()


def hash_password(password: str) -> str:
    """Hash password con PBKDF2-SHA256 (stesso formato usato da security.py)."""
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(encoded: str, candidate: str) -> bool:
    """Verifica password contro hash PBKDF2-SHA256."""
    try:
        scheme, iter_str, salt_hex, hash_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        digest = bytes.fromhex(hash_hex)
    except Exception:
        return False
    derived = hashlib.pbkdf2_hmac("sha256", candidate.encode("utf-8"), salt, iterations)
    return secrets.compare_digest(derived, digest)


def create_user(
    email: str,
    password: str,
    *,
    display_name: str = "",
    tenant_id: Optional[str] = None,
    role: str = "user",
) -> Dict[str, Any]:
    """Crea un nuovo utente. Restituisce il record creato (senza password_hash)."""

    user_id = str(uuid.uuid4())
    now = datetime.datetime.now(APP_TIMEZONE).isoformat()
    pw_hash = hash_password(password)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                """
                INSERT INTO users (id, email, password_hash, display_name, tenant_id, role, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, display_name, tenant_id, role, is_active, created_at
                """,
                (
                    user_id,
                    email.strip().lower(),
                    pw_hash,
                    display_name.strip(),
                    tenant_id,
                    role,
                    now,
                ),
            )
            row = cursor.fetchone()
        conn.commit()
    return _format_user(row) if row else {}


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Recupera un utente per email (include password_hash per verifica login)."""

    if not POSTGRES_ENABLED:
        return None

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                "SELECT id, email, password_hash, display_name, tenant_id, role, is_active, created_at "
                "FROM users WHERE email = %s",
                (email.strip().lower(),),
            )
            row = cursor.fetchone()
        conn.rollback()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Recupera un utente per ID (senza password_hash)."""

    if not POSTGRES_ENABLED:
        return None

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                "SELECT id, email, display_name, tenant_id, role, is_active, created_at, last_login_at "
                "FROM users WHERE id = %s",
                (user_id,),
            )
            row = cursor.fetchone()
        conn.rollback()
    return _format_user(row) if row else None


def count_users_by_tenant(tenant_id: str) -> int:
    """Restituisce il numero di utenti attivi di un tenant."""

    if not POSTGRES_ENABLED:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE tenant_id = %s AND is_active = TRUE",
                (tenant_id,),
            )
            row = cursor.fetchone()
        conn.rollback()
    return row[0] if row else 0


def count_users() -> int:
    """Numero totale utenti (cross-tenant). Usato dal bootstrap gate per
    rilevare il first-boot. Read-only: rollback esplicito sulla connessione
    per evitare leak di transazione idle."""

    if not POSTGRES_ENABLED:
        return 0

    with get_connection() as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users")
                row = cursor.fetchone()
        finally:
            conn.rollback()
    return int(row[0]) if row else 0


def list_users_by_tenant(tenant_id: str) -> list[Dict[str, Any]]:
    """Restituisce tutti gli utenti di un tenant."""

    if not POSTGRES_ENABLED:
        return []

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                "SELECT id, email, display_name, tenant_id, role, is_active, created_at, last_login_at "
                "FROM users WHERE tenant_id = %s ORDER BY created_at ASC",
                (tenant_id,),
            )
            rows = cursor.fetchall()
        conn.rollback()
    return [_format_user(row) for row in rows]


def update_user(
    user_id: str,
    *,
    display_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Aggiorna un utente esistente."""

    updates = []
    params: list = []
    if display_name is not None:
        updates.append("display_name = %s")
        params.append(display_name.strip())
    if role is not None:
        updates.append("role = %s")
        params.append(role)
    if is_active is not None:
        updates.append("is_active = %s")
        params.append(is_active)

    if not updates:
        return get_user_by_id(user_id)

    params.append(user_id)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            cursor.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = %s "
                "RETURNING id, email, display_name, tenant_id, role, is_active, created_at, last_login_at",
                params,
            )
            row = cursor.fetchone()
        conn.commit()
    return _format_user(row) if row else None


def update_last_login(user_id: str) -> None:
    """Aggiorna il timestamp dell'ultimo login."""

    now = datetime.datetime.now(APP_TIMEZONE).isoformat()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_login_at = %s WHERE id = %s",
                (now, user_id),
            )
        conn.commit()


def _format_user(row: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(row)
    result.pop("password_hash", None)
    if "id" in result:
        result["id"] = str(result["id"])
    if "tenant_id" in result and result["tenant_id"] is not None:
        result["tenant_id"] = str(result["tenant_id"])
    for key in ("created_at", "last_login_at"):
        val = result.get(key)
        if val is not None and hasattr(val, "isoformat"):
            if val.tzinfo is None:
                val = val.replace(tzinfo=APP_TIMEZONE)
            else:
                val = val.astimezone(APP_TIMEZONE)
            result[key] = val.isoformat()
    return result

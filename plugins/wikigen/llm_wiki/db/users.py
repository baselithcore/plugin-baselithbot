"""CRUD tabella users + password hashing.

Adattato da ``agent-jira/app/db/users.py``. Differenze:
- Schema gestito da Alembic (no ``ensure_users_schema()``).
- Tutti i path che leggono ``password_hash`` sono espliciti
  (:func:`get_user_by_email_with_credentials`) — gli altri lookup
  rimuovono il campo prima del return.
- Modello 1:1 user↔tenant — ``count_users_by_tenant`` resta come
  guard ma valore atteso è sempre 0 o 1.
"""

from __future__ import annotations

import datetime
import hashlib
import secrets
import uuid
from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection

# PBKDF2-SHA256 a 260k iterazioni — allineato OWASP 2023 baseline.
# Hash format: ``pbkdf2_sha256$<iter>$<salt_hex>$<hash_hex>``.
_PBKDF2_ITERATIONS = 260_000


# --- password ---------------------------------------------------------------


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(encoded: str, candidate: str) -> bool:
    """Verifica password con confronto a tempo costante."""
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


# --- formatting -------------------------------------------------------------


def _format_user(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result.pop("password_hash", None)
    for key in ("id", "tenant_id"):
        if key in result and result[key] is not None:
            result[key] = str(result[key])
    for key in ("created_at", "last_login_at"):
        val = result.get(key)
        if val is not None and hasattr(val, "isoformat"):
            result[key] = val.isoformat()
    return result


# --- CRUD -------------------------------------------------------------------


def create_user(
    email: str,
    password: str,
    *,
    display_name: str = "",
    tenant_id: str | None = None,
    role: str = "user",
) -> dict[str, Any]:
    """Crea utente standalone.

    Path normale = :func:`tenants.create_tenant_with_owner` (transazione
    singola). Questa funzione utile solo per migrations dati o tool admin
    che operano su tenant pre-esistenti.

    ``tenant_id`` è ``NOT NULL`` a livello DB (migration 001). Passare
    ``None`` qui solleverà un IntegrityError — esplicito apposta.
    """
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")
    from psycopg.rows import dict_row

    user_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pw_hash = hash_password(password)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
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
                    email.strip().lower(),
                    pw_hash,
                    display_name.strip(),
                    tenant_id,
                    role,
                    now,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return _format_user(row) if row else {}


def get_user_by_email_with_credentials(email: str) -> dict[str, Any] | None:
    """Lookup per login: include ``password_hash`` per la verifica.

    NON esporre il return verbatim ai client — usare solo dentro il
    flow di authenticate(). Per qualsiasi altro caso, preferire
    :func:`get_user_by_email`.
    """
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, email, password_hash, display_name, tenant_id, "
                "role, is_active, password_must_change, created_at "
                "FROM users WHERE email = %s",
                (email.strip().lower(),),
            )
            row = cur.fetchone()
        conn.rollback()
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Lookup safe: senza ``password_hash``."""
    raw = get_user_by_email_with_credentials(email)
    return _format_user(raw) if raw else None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, email, display_name, tenant_id, role, "
                "is_active, password_must_change, created_at, last_login_at "
                "FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
        conn.rollback()
    return _format_user(row) if row else None


def get_user_by_tenant(tenant_id: str) -> dict[str, Any] | None:
    """Owner del tenant (1:1 invariant). Comodo per amministrazione."""
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, email, display_name, tenant_id, role, "
                "is_active, password_must_change, created_at, last_login_at "
                "FROM users WHERE tenant_id = %s",
                (tenant_id,),
            )
            row = cur.fetchone()
        conn.rollback()
    return _format_user(row) if row else None


def count_users_by_tenant(tenant_id: str) -> int:
    """Sempre 0 o 1 sotto l'invariante 1:1. Tieni come guard."""
    if not config.POSTGRES_ENABLED:
        return 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM users WHERE tenant_id = %s AND is_active = TRUE",
                (tenant_id,),
            )
            row = cur.fetchone()
        conn.rollback()
    return int(row[0]) if row else 0


def list_users() -> list[dict[str, Any]]:
    """Lista globale utenti — richiede ruolo bypass-RLS (admin)."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, email, display_name, tenant_id, role, "
                "is_active, password_must_change, created_at, last_login_at "
                "FROM users ORDER BY created_at ASC"
            )
            rows = cur.fetchall()
        conn.rollback()
    return [_format_user(row) for row in rows]


def count_users() -> int:
    """Conta totale utenti. Usato dal lifespan per detect "first boot"."""
    if not config.POSTGRES_ENABLED:
        return 0
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                row = cur.fetchone()
        finally:
            # Chiudi transazione esplicitamente: senza questo il pool
            # logga "rolling back returned connection [INTRANS]" ad ogni
            # checkout. Read-only query → rollback safe.
            conn.rollback()
    return int(row[0]) if row else 0


def update_user(
    user_id: str,
    *,
    display_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any] | None:
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    updates: list[str] = []
    params: list[Any] = []
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
        with conn.cursor(row_factory=dict_row) as cur:
            # `updates` whitelist locale di "col = %s"; valori bound via params.
            cur.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = %s "  # nosec B608
                "RETURNING id, email, display_name, tenant_id, role, "
                "is_active, created_at, last_login_at",
                params,
            )
            row = cur.fetchone()
        conn.commit()
    return _format_user(row) if row else None


def set_password_must_change(user_id: str, value: bool) -> bool:
    """Setta/azzera flag ``password_must_change``. Tipicamente:

    - ``True`` da bootstrap autostart (password generata) e da
      password reset admin-driven.
    - ``False`` automaticamente da :func:`update_password` (cambio
      effettuato dall'utente stesso).
    """
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_must_change = %s WHERE id = %s",
                (value, user_id),
            )
            updated = cur.rowcount > 0
        conn.commit()
    return updated


def update_password(user_id: str, new_password: str) -> bool:
    """Cambio password. Azzera automaticamente ``password_must_change``
    (l'utente ha appena scelto la sua password). Il chiamante è
    responsabile della revoca dei refresh token
    (``llm_wiki.auth.tokens.revoke_all_for_user``)."""
    if not config.POSTGRES_ENABLED:
        return False
    pw_hash = hash_password(new_password)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, password_must_change = FALSE WHERE id = %s",
                (pw_hash, user_id),
            )
            updated = cur.rowcount > 0
        conn.commit()
    return updated


def update_last_login(user_id: str) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login_at = %s WHERE id = %s",
                (now, user_id),
            )
        conn.commit()


def delete_user(user_id: str) -> bool:
    """Hard delete utente. CASCADE su `users.id` rimuove:

    - ``refresh_tokens`` (002)
    - ``conversations`` (003) → cascade ``messages``
    - ``memories`` (004)
    - ``feedback`` (005)
    - ``user_roles`` / ``user_domains`` (007/008)

    `audit_events.user_id` ha SET NULL → traccia anonimizzata
    persiste (richiesto per accountability log retention).

    Caller deve aver già verificato:
    - utente non è ultimo superuser (vedi roles.revoke_role)
    - se DSAR delete-by-self, la sessione è autenticata.
    """
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


__all__ = [
    "hash_password",
    "verify_password",
    "create_user",
    "get_user_by_email",
    "get_user_by_email_with_credentials",
    "get_user_by_id",
    "get_user_by_tenant",
    "count_users_by_tenant",
    "list_users",
    "count_users",
    "update_user",
    "set_password_must_change",
    "update_password",
    "update_last_login",
    "delete_user",
]

"""Embeds CRUD + token verify (mig 017).

API surface
-----------

- :func:`generate_token` — produce ``(plaintext, hash, prefix)``. Il
  plaintext va consegnato all'admin **una volta** (creazione/rotazione)
  e mai più stampato/loggato.
- :func:`verify_token` — lookup pubblico via hash. NON imposta il
  tenant context; il caller (router) lo fa via
  :func:`auth.tenant_context.set_current_tenant` dopo la verifica.
- CRUD (list/get/create/update/delete/rotate) — tenant-scoped esplicito
  (no RLS, vedi mig 017 docstring).

Tutte le funzioni sono no-op ``return None``/``[]`` se ``POSTGRES_ENABLED=
false`` — coerenza con il resto del db layer (setup mode non rompe).
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection

logger = logging.getLogger(__name__)


TOKEN_PREFIX = "emb_"
TOKEN_RANDOM_BYTES = 32
TOKEN_PREFIX_DISPLAY_LEN = 12  # "emb_xxxxxxxx" stored per UI list


# --- helpers --------------------------------------------------------------


def generate_token() -> tuple[str, str, str]:
    """Produci ``(plaintext, sha256_hex, display_prefix)``.

    Plaintext: ``emb_<64 hex>`` (256 bit entropy). Memorizziamo solo
    ``sha256(plaintext)``; il plaintext va consegnato all'admin una sola
    volta. Display prefix = primi 12 char del plaintext, salvato per
    rendering in UI list ("Token: emb_abc12345…").
    """
    random_hex = secrets.token_hex(TOKEN_RANDOM_BYTES)
    plaintext = f"{TOKEN_PREFIX}{random_hex}"
    token_hash = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    display_prefix = plaintext[:TOKEN_PREFIX_DISPLAY_LEN]
    return plaintext, token_hash, display_prefix


def hash_token(plaintext: str) -> str:
    """sha256 hex del plaintext. Esposto per i test."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _format(row: dict[str, Any]) -> dict[str, Any]:
    """Mapper riga DB → dict serializzabile JSON. NON include token_hash."""
    out: dict[str, Any] = {
        "id": str(row["id"]),
        "slug": row["slug"],
        "name": row["name"],
        "description": row.get("description", "") or "",
        "tenant_id": str(row["tenant_id"]),
        "token_prefix": row["token_prefix"],
        "origin_allowlist": list(row.get("origin_allowlist") or []),
        "theme": dict(row.get("theme") or {}),
        "welcome_message": row.get("welcome_message", "") or "",
        "suggested_questions": list(row.get("suggested_questions") or []),
        "rate_limit_per_minute": int(row.get("rate_limit_per_minute") or 30),
        "is_enabled": bool(row.get("is_enabled", True)),
        "created_by": str(row["created_by"]) if row.get("created_by") else None,
    }
    for key in ("created_at", "updated_at", "last_used_at"):
        val = row.get(key)
        if val is not None and hasattr(val, "isoformat"):
            out[key] = val.isoformat()
        elif val is not None:
            out[key] = val
        else:
            out[key] = None
    return out


# --- CRUD -----------------------------------------------------------------


def list_embeds(tenant_id: str) -> list[dict[str, Any]]:
    """Tutti gli embed di ``tenant_id``. No RLS — filtro esplicito."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, slug, name, description, tenant_id,
                           token_prefix, origin_allowlist, theme,
                           welcome_message, suggested_questions,
                           rate_limit_per_minute, is_enabled, created_by,
                           last_used_at, created_at, updated_at
                    FROM embeds
                    WHERE tenant_id = %s
                    ORDER BY created_at DESC
                    """,
                    (tenant_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [_format(r) for r in rows]


def get_embed_by_id(embed_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    """Lookup admin per id. Se ``tenant_id`` fornito, valida tenant match."""
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                if tenant_id:
                    cur.execute(
                        """
                        SELECT * FROM embeds WHERE id = %s AND tenant_id = %s
                        """,
                        (embed_id, tenant_id),
                    )
                else:
                    cur.execute("SELECT * FROM embeds WHERE id = %s", (embed_id,))
                row = cur.fetchone()
        finally:
            conn.rollback()
    return _format(row) if row else None


def create_embed(
    *,
    tenant_id: str,
    slug: str,
    name: str,
    description: str = "",
    origin_allowlist: list[str] | None = None,
    theme: dict[str, Any] | None = None,
    welcome_message: str = "",
    suggested_questions: list[str] | None = None,
    rate_limit_per_minute: int = 30,
    created_by: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Crea embed + token. Ritorna ``(record, plaintext_token)``.

    Plaintext NON viene ri-letto da `_format`; il caller deve consegnarlo
    all'admin nella response di POST e dimenticarlo subito dopo.
    """
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")
    import json as _json

    from psycopg.rows import dict_row

    plaintext, token_hash, display_prefix = generate_token()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO embeds (
                    slug, name, description, tenant_id,
                    token_hash, token_prefix,
                    origin_allowlist, theme,
                    welcome_message, suggested_questions,
                    rate_limit_per_minute, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s)
                RETURNING *
                """,
                (
                    slug.strip(),
                    name.strip(),
                    description.strip(),
                    tenant_id,
                    token_hash,
                    display_prefix,
                    list(origin_allowlist or []),
                    _json.dumps(theme or {}),
                    welcome_message.strip(),
                    _json.dumps(list(suggested_questions or [])),
                    max(0, int(rate_limit_per_minute)),
                    created_by,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("INSERT embeds non ha restituito righe")
    return _format(row), plaintext


def update_embed(
    embed_id: str,
    tenant_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    origin_allowlist: list[str] | None = None,
    theme: dict[str, Any] | None = None,
    welcome_message: str | None = None,
    suggested_questions: list[str] | None = None,
    rate_limit_per_minute: int | None = None,
    is_enabled: bool | None = None,
) -> dict[str, Any] | None:
    """PATCH parziale. Slug e token NON modificabili da update (rotate
    è op separata). Tenant fix per cross-tenant guard."""
    if not config.POSTGRES_ENABLED:
        return None
    import json as _json

    updates: list[str] = []
    params: list[Any] = []
    if name is not None:
        updates.append("name = %s")
        params.append(name.strip())
    if description is not None:
        updates.append("description = %s")
        params.append(description.strip())
    if origin_allowlist is not None:
        updates.append("origin_allowlist = %s")
        params.append(list(origin_allowlist))
    if theme is not None:
        updates.append("theme = %s::jsonb")
        params.append(_json.dumps(theme))
    if welcome_message is not None:
        updates.append("welcome_message = %s")
        params.append(welcome_message.strip())
    if suggested_questions is not None:
        updates.append("suggested_questions = %s::jsonb")
        params.append(_json.dumps(list(suggested_questions)))
    if rate_limit_per_minute is not None:
        updates.append("rate_limit_per_minute = %s")
        params.append(max(0, int(rate_limit_per_minute)))
    if is_enabled is not None:
        updates.append("is_enabled = %s")
        params.append(bool(is_enabled))
    if not updates:
        return get_embed_by_id(embed_id, tenant_id)
    params.extend([embed_id, tenant_id])
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE embeds SET {', '.join(updates)} "  # nosec B608 — colonne whitelist sopra
                "WHERE id = %s AND tenant_id = %s",
                params,
            )
        conn.commit()
    return get_embed_by_id(embed_id, tenant_id)


def delete_embed(embed_id: str, tenant_id: str) -> bool:
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM embeds WHERE id = %s AND tenant_id = %s",
                (embed_id, tenant_id),
            )
            removed = cur.rowcount > 0
        conn.commit()
    return removed


def rotate_token(embed_id: str, tenant_id: str) -> tuple[dict[str, Any], str] | None:
    """Genera nuovo token, sovrascrive hash+prefix in atomic UPDATE.
    Ritorna ``(record, plaintext)`` o ``None`` se non trovato.
    """
    if not config.POSTGRES_ENABLED:
        return None
    plaintext, token_hash, display_prefix = generate_token()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE embeds SET token_hash = %s, token_prefix = %s
                WHERE id = %s AND tenant_id = %s
                """,
                (token_hash, display_prefix, embed_id, tenant_id),
            )
            updated = cur.rowcount > 0
        conn.commit()
    if not updated:
        return None
    record = get_embed_by_id(embed_id, tenant_id)
    if not record:
        return None
    return record, plaintext


# --- public verify --------------------------------------------------------


def verify_token(plaintext: str, *, origin: str | None) -> dict[str, Any] | None:
    """Risolvi un token plaintext + Origin → record embed.

    Ritorna ``None`` se:
    - token non esiste / hash non match,
    - embed disabled (``is_enabled=false``),
    - ``origin`` mancante (no Origin header) E ``origin_allowlist`` non vuoto,
    - ``origin`` non in ``origin_allowlist``.

    Allowlist vuota = nessun embed valido (deny by default): l'admin
    deve esplicitamente autorizzare i siti. Match esatto del literal
    (no wildcard, no path-substring).
    """
    if not config.POSTGRES_ENABLED:
        return None
    if not plaintext or not plaintext.startswith(TOKEN_PREFIX):
        return None
    token_hash = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()

    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM embeds WHERE token_hash = %s AND is_enabled = TRUE
                    """,
                    (token_hash,),
                )
                row = cur.fetchone()
        finally:
            conn.rollback()
    if not row:
        return None

    allowlist = list(row.get("origin_allowlist") or [])
    if not allowlist:
        # Deny-by-default: admin non ha configurato siti.
        return None
    if not origin or origin not in allowlist:
        return None

    return _format(row)


def touch_last_used(embed_id: str) -> None:
    """Aggiorna ``last_used_at = NOW()``. Best-effort, mai solleva."""
    if not config.POSTGRES_ENABLED:
        return
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE embeds SET last_used_at = NOW() WHERE id = %s",
                    (embed_id,),
                )
            conn.commit()
    except Exception as exc:
        logger.debug("[embeds] touch_last_used failed: %s", exc)


__all__ = [
    "generate_token",
    "hash_token",
    "list_embeds",
    "get_embed_by_id",
    "create_embed",
    "update_embed",
    "delete_embed",
    "rotate_token",
    "verify_token",
    "touch_last_used",
    "TOKEN_PREFIX",
]

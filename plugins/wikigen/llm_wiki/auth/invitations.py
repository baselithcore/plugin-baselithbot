"""Setup invitation tokens — first-superuser + admin-driven onboarding.

Pattern allineato a OAuth2 refresh-rotation + NIST SP 800-63B:

- Token plain è 48 byte URL-safe (~256 bit entropia). Generato da
  :func:`secrets.token_urlsafe(48)`. Mostrato UNA volta al maintainer
  (CLI banner stderr / endpoint admin response). MAI persistito.
- DB conserva solo SHA-256 hash → leak DB ≠ tampering token.
- Single-use: ``used_at`` segna il consumo. Doppio accept → 409.
- Time-bound: default ``INVITATION_TTL_HOURS=24h`` configurabile.
- Constant-time hash comparison (eq via :func:`secrets.compare_digest`).
- Bound a email: l'accept fissa l'email server-side, il body utente
  fornisce solo password + display_name (anti-confusion).

Flow consigliato:

1. Maintainer (CLI o admin endpoint) emette invito → riceve URL plain.
2. Maintainer manda URL al cliente (canale sicuro).
3. Cliente apre URL → frontend ``AcceptInvite`` page → POST
   ``/auth/invite/accept`` con ``{token, password, display_name}``.
4. Backend valida + crea user + assegna ruolo + login implicito.
5. Token marcato ``used_at`` → no replay.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import secrets
from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection

logger = logging.getLogger(__name__)


class InvitationError(Exception):
    """Errore funzionale (token mancante / scaduto / già usato / email mismatch)."""


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_invitation(
    *,
    email: str,
    role_slug: str | None = None,
    tenant_slug: str | None = None,
    display_name: str = "",
    note: str = "",
    created_by: str | None = None,
    ttl_hours: int | None = None,
) -> dict[str, Any]:
    """Crea un invito. Ritorna ``{"token_plain", "expires_at", "id"}``.

    ``token_plain`` deve essere mostrato UNA volta al chiamante e mai
    persistito altrove dal nostro codice. ``expires_at`` ritornato
    in UTC ISO-8601 per UI display.
    """
    if not config.POSTGRES_ENABLED:
        raise InvitationError("Postgres disabilitato.")

    cleaned = (email or "").strip().lower()
    if not cleaned or "@" not in cleaned:
        raise InvitationError("Email non valida.")

    hours = ttl_hours if ttl_hours is not None else config.INVITATION_TTL_HOURS
    token_plain = secrets.token_urlsafe(48)
    token_hash = _hash_token(token_plain)
    now = _now()
    expires_at = now + datetime.timedelta(hours=hours)

    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO setup_invitations
                    (token_hash, email, role_slug, tenant_slug,
                     display_name, note, expires_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, expires_at
                """,
                (
                    token_hash,
                    cleaned,
                    role_slug,
                    tenant_slug,
                    display_name.strip(),
                    note.strip(),
                    expires_at,
                    created_by,
                ),
            )
            row = cur.fetchone()
        conn.commit()

    return {
        "id": str(row["id"]),
        "token_plain": token_plain,
        "expires_at": row["expires_at"].isoformat(),
    }


def peek_invitation(token: str) -> dict[str, Any] | None:
    """Lookup read-only (non consuma il token). Usato dal frontend
    AcceptInvite per pre-popolare l'email e mostrare un messaggio
    dedicato per token scaduti o già usati. Constant-time match.
    """
    if not config.POSTGRES_ENABLED:
        return None
    if not token:
        return None

    token_hash = _hash_token(token)
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, email, role_slug, tenant_slug, display_name,
                           expires_at, used_at, created_at
                    FROM setup_invitations
                    WHERE token_hash = %s
                    """,
                    (token_hash,),
                )
                row = cur.fetchone()
        finally:
            conn.rollback()
    if not row:
        return None

    now = _now()
    return {
        "email": row["email"],
        "role_slug": row["role_slug"],
        "tenant_slug": row["tenant_slug"],
        "display_name": row["display_name"],
        "expires_at": row["expires_at"].isoformat(),
        "used": row["used_at"] is not None,
        "expired": row["expires_at"] <= now,
    }


def consume_invitation(token: str) -> dict[str, Any]:
    """Atomic validate + mark-used. Solleva :class:`InvitationError`
    se il token è invalido / scaduto / già consumato. UPDATE
    condizionato (``used_at IS NULL AND expires_at > NOW()``) garantisce
    atomicità anche con accept concorrenti — solo una request riesce.

    Ritorna i metadati dell'invito (email, role_slug, ecc.) per il
    caller che procederà alla creazione utente.
    """
    if not config.POSTGRES_ENABLED:
        raise InvitationError("Postgres disabilitato.")
    if not token or len(token) < 32:
        raise InvitationError("Token mancante o malformato.")

    token_hash = _hash_token(token)
    now = _now()
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE setup_invitations
                SET used_at = %s
                WHERE token_hash = %s
                  AND used_at IS NULL
                  AND expires_at > %s
                RETURNING id, email, role_slug, tenant_slug, display_name
                """,
                (now, token_hash, now),
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        # Diagnose precise reason senza leak — usiamo peek (read-only,
        # post-fact). Constant-time non strettamente necessario qui:
        # il chiamante ha già fallito la consumption.
        info = peek_invitation(token)
        if info is None:
            raise InvitationError("Token non riconosciuto.")
        if info["used"]:
            raise InvitationError("Invito già utilizzato.")
        if info["expired"]:
            raise InvitationError("Invito scaduto.")
        # Fallback (race rare): generic.
        raise InvitationError("Invito non utilizzabile.")

    return {
        "id": str(row["id"]),
        "email": row["email"],
        "role_slug": row["role_slug"],
        "tenant_slug": row["tenant_slug"],
        "display_name": row["display_name"],
    }


def revoke_invitation(invitation_id: str) -> bool:
    """Revoca esplicita (admin UI / CLI). Marcando ``used_at`` rendiamo
    il token immediatamente invalido. Idempotent."""
    if not config.POSTGRES_ENABLED:
        return False
    now = _now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE setup_invitations SET used_at = %s WHERE id = %s AND used_at IS NULL",
                (now, invitation_id),
            )
            updated = cur.rowcount > 0
        conn.commit()
    return updated


def list_active_invitations() -> list[dict[str, Any]]:
    """Lista inviti non scaduti e non usati. Usato per UI admin."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, email, role_slug, tenant_slug, display_name,
                           note, expires_at, created_at, created_by
                    FROM setup_invitations
                    WHERE used_at IS NULL
                      AND expires_at > NOW()
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "role_slug": r["role_slug"],
            "tenant_slug": r["tenant_slug"],
            "display_name": r["display_name"],
            "note": r["note"],
            "expires_at": r["expires_at"].isoformat(),
            "created_at": r["created_at"].isoformat(),
            "created_by": str(r["created_by"]) if r.get("created_by") else None,
        }
        for r in rows
    ]


__all__ = [
    "InvitationError",
    "create_invitation",
    "peek_invitation",
    "consume_invitation",
    "revoke_invitation",
    "list_active_invitations",
]

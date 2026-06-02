"""JWT access token issuance + opaque refresh token rotation chain.

Adattato da ``agent-jira/app/auth_tokens.py``. TTL configurabili via
``config.ACCESS_TOKEN_TTL_MINUTES`` / ``config.REFRESH_TOKEN_TTL_DAYS``.

Modello sicurezza
=================

Access token: JWT HS256 firmato con ``config.SECRET_KEY``. Claim
``sub``/``uid``/``tenant_id``/``role``/``typ=access``. Mai persistito.

Refresh token: 64-char URL-safe random (~384 bit). In chiaro mai
salvato — DB conserva solo SHA-256 hash. Rotation: ogni use produce
un nuovo refresh, il vecchio è marcato ``replaced_by`` + ``revoked_at``.

Replay detection: se un client presenta un token già revocato/sostituito
significa che è stato copiato → revoca tutta la ``family_id`` (forza
re-login ovunque). Pattern OAuth2 refresh rotation.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import secrets
import uuid
from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection

logger = logging.getLogger(__name__)


class TokenError(Exception):
    """Errore nel ciclo di vita dei token (invalido/scaduto/revocato/replay)."""


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _require_secret() -> str:
    secret = (config.SECRET_KEY or "").strip()
    if not secret:
        raise RuntimeError(
            "SECRET_KEY non configurata. Imposta in .env un secret >=32 byte "
            'random (es: `python -c "import secrets; print(secrets.token_urlsafe(48))"`).'
        )
    return secret


# --- access token (JWT HS256) ----------------------------------------------


def issue_access_token(
    *, user_id: str, tenant_id: str, role: str
) -> tuple[str, datetime.datetime]:
    """Genera JWT HS256 con TTL = ``ACCESS_TOKEN_TTL_MINUTES``."""
    import jwt as pyjwt

    now = _now()
    exp = now + datetime.timedelta(minutes=config.ACCESS_TOKEN_TTL_MINUTES)
    payload = {
        "sub": user_id,
        "uid": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "typ": "access",
        "iat": now,
        "exp": exp,
    }
    token = pyjwt.encode(payload, _require_secret(), algorithm="HS256")
    return token, exp


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodifica e verifica firma + scadenza. Restituisce None se invalido.

    Non verifica la coerenza ``claim.tenant_id`` ↔ ``users.tenant_id`` —
    quella è responsabilità del :class:`TenantMiddleware` (anti-tampering
    JWT). Qui solo "il JWT è formalmente valido".
    """
    import jwt as pyjwt

    try:
        return pyjwt.decode(token, _require_secret(), algorithms=["HS256"])
    except pyjwt.PyJWTError:
        return None


# --- refresh token (opaque, hashed in DB) ----------------------------------


def issue_refresh_token(
    *,
    user_id: str,
    tenant_id: str,
    family_id: str | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, datetime.datetime, str]:
    """Emette refresh opaque. Restituisce ``(token_plain, expires_at, family_id)``.

    Il valore in chiaro va al client SOLO via cookie httpOnly e mai
    persistito altrove. Il DB conserva solo SHA-256.
    """
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato — refresh token impossibili.")

    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    fid = family_id or str(uuid.uuid4())
    now = _now()
    expires_at = now + datetime.timedelta(days=config.REFRESH_TOKEN_TTL_DAYS)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO refresh_tokens
                    (token_hash, family_id, user_id, tenant_id,
                     issued_at, expires_at, user_agent, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    token_hash,
                    fid,
                    user_id,
                    tenant_id,
                    now,
                    expires_at,
                    (user_agent or "")[:500] or None,
                    ip_address,
                ),
            )
        conn.commit()
    return token, expires_at, fid


def rotate_refresh_token(
    presented_token: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    """Valida + ruota + restituisce ``(access, refresh)`` nuovi.

    Replay detection: se il token presentato è già revocato/sostituito,
    revoca TUTTA la ``family_id`` (l'attaccante l'ha copiato — forza
    re-login). Audit event ``auth.refresh.replay`` scritto dal router.

    Solleva :class:`TokenError` su invalido/scaduto/revocato/replay.
    """
    from psycopg.rows import dict_row

    presented_hash = _hash_token(presented_token)
    now = _now()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, family_id, user_id, tenant_id,
                       expires_at, revoked_at, replaced_by
                FROM refresh_tokens
                WHERE token_hash = %s
                """,
                (presented_hash,),
            )
            row = cur.fetchone()
            if not row:
                raise TokenError("refresh token non riconosciuto")

            if row["revoked_at"] is not None or row["replaced_by"] is not None:
                logger.warning(
                    "[auth] refresh replay: family=%s user=%s — revoca famiglia",
                    row["family_id"],
                    row["user_id"],
                )
                cur.execute(
                    """
                    UPDATE refresh_tokens
                    SET revoked_at = %s
                    WHERE family_id = %s AND revoked_at IS NULL
                    """,
                    (now, row["family_id"]),
                )
                conn.commit()
                raise TokenError("refresh token replay: session revocata")

            if row["expires_at"] <= now:
                raise TokenError("refresh token scaduto")

            cur.execute(
                "SELECT id, tenant_id, role, is_active FROM users WHERE id = %s",
                (row["user_id"],),
            )
            user_row = cur.fetchone()
            if not user_row or not user_row["is_active"]:
                raise TokenError("utente non più attivo")

            cur.execute(
                "UPDATE refresh_tokens SET revoked_at = %s WHERE id = %s",
                (now, row["id"]),
            )
            conn.commit()

    # Nuovi token fuori dalla transazione precedente: issue_refresh_token
    # apre la propria. La family resta la stessa.
    new_refresh, refresh_exp, _ = issue_refresh_token(
        user_id=str(row["user_id"]),
        tenant_id=str(row["tenant_id"]),
        family_id=str(row["family_id"]),
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Collega vecchio → nuovo per audit chain.
    new_hash = _hash_token(new_refresh)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM refresh_tokens WHERE token_hash = %s",
                (new_hash,),
            )
            new_row = cur.fetchone()
            if new_row:
                cur.execute(
                    "UPDATE refresh_tokens SET replaced_by = %s WHERE id = %s",
                    (new_row[0], row["id"]),
                )
        conn.commit()

    access, access_exp = issue_access_token(
        user_id=str(row["user_id"]),
        tenant_id=str(row["tenant_id"]),
        role=user_row["role"],
    )

    return {
        "access_token": access,
        "access_token_expires_at": access_exp,
        "refresh_token": new_refresh,
        "refresh_token_expires_at": refresh_exp,
        "user_id": str(row["user_id"]),
        "tenant_id": str(row["tenant_id"]),
    }


def revoke_refresh_token(presented_token: str) -> bool:
    """Logout singola sessione."""
    if not config.POSTGRES_ENABLED:
        return False
    presented_hash = _hash_token(presented_token)
    now = _now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked_at = %s "
                "WHERE token_hash = %s AND revoked_at IS NULL",
                (now, presented_hash),
            )
            revoked = cur.rowcount > 0
        conn.commit()
    return revoked


def revoke_all_for_user(user_id: str) -> int:
    """Logout everywhere (password change, security incident).

    Restituisce numero token revocati.
    """
    if not config.POSTGRES_ENABLED:
        return 0
    now = _now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked_at = %s "
                "WHERE user_id = %s AND revoked_at IS NULL",
                (now, user_id),
            )
            n = cur.rowcount
        conn.commit()
    return n


__all__ = [
    "TokenError",
    "issue_access_token",
    "decode_access_token",
    "issue_refresh_token",
    "rotate_refresh_token",
    "revoke_refresh_token",
    "revoke_all_for_user",
]

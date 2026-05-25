"""
Refresh + access token management (Sprint 11).

Pattern: access token JWT con TTL breve (default 15 min) + refresh token
opaco random persistito in DB con rotation.

Rotation: ogni refresh ritorna un nuovo token; il vecchio è marcato
`replaced_by`. Il replay di un token già ruotato (furto) revoca tutta
la famiglia, forzando re-login.

Flow:
    login()
      → issue_access(user)               → JWT 15m in response body
      → issue_refresh(user, family=new)  → opaque 30d in httpOnly cookie

    refresh(token)
      → rotate_refresh(token)
        - se valid e non usato → nuovo access + nuovo refresh
        - se già usato (replay) → revoca FAMILY_ID → 401

    logout()
      → revoke_refresh(token)
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import secrets
import uuid
from typing import Any, Dict, Optional

import jwt as pyjwt
from psycopg.rows import dict_row

from agent_jira.db.connection import get_connection
from agent_jira.config import SECRET_KEY

logger = logging.getLogger(__name__)

ACCESS_TOKEN_TTL_MINUTES = 1440  # 24h — frontend non ha auto-refresh del token
REFRESH_TOKEN_TTL_DAYS = 30


class TokenError(Exception):
    """Errore nel ciclo di vita dei token (invalido, scaduto, revocato, replay)."""


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_access_token(
    *, user_id: str, tenant_id: str, role: str
) -> tuple[str, datetime.datetime]:
    """Genera un JWT access token HS256 con TTL breve."""
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    payload = {
        "sub": user_id,
        "uid": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "typ": "access",
        "iat": now,
        "exp": exp,
    }
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY non configurata")
    token = pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token, exp


def issue_refresh_token(
    *,
    user_id: str,
    tenant_id: str,
    family_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> tuple[str, datetime.datetime, str]:
    """
    Emette un refresh token opaco. Restituisce (token_plain, expires_at, family_id).

    Il valore in chiaro DEVE essere restituito al client via httpOnly cookie
    e mai persistito altrove. Il DB conserva solo l'hash.
    """
    token = secrets.token_urlsafe(48)  # 64 char, 384 bit
    token_hash = _hash_token(token)
    fid = family_id or str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now + datetime.timedelta(days=REFRESH_TOKEN_TTL_DAYS)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
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
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Valida il refresh token, lo ruota e restituisce (access, refresh) nuovi.

    Replay detection: se presented_token risulta già revocato/sostituito,
    tutta la `family_id` viene revocata (l'attaccante ha copiato il token
    e noi forziamo logout ovunque).

    Raise TokenError in caso di invalido/scaduto/revocato.
    """
    presented_hash = _hash_token(presented_token)
    now = datetime.datetime.now(datetime.timezone.utc)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, family_id, user_id, tenant_id,
                       expires_at, revoked_at, replaced_by
                FROM refresh_tokens
                WHERE token_hash = %s
                """,
                (presented_hash,),
            )
            row = cursor.fetchone()
            if not row:
                raise TokenError("refresh token non riconosciuto")

            # Replay / double-use detection: se il token è già stato ruotato,
            # è un furto → revoca tutta la famiglia.
            if row["revoked_at"] is not None or row["replaced_by"] is not None:
                logger.warning(
                    "Refresh token replay detectato: family_id=%s user=%s — revoca famiglia",
                    row["family_id"],
                    row["user_id"],
                )
                cursor.execute(
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

            # Carica user per ricavare il role corrente (in caso cambi).
            cursor.execute(
                "SELECT id, tenant_id, role, is_active FROM users WHERE id = %s",
                (row["user_id"],),
            )
            user_row = cursor.fetchone()
            if not user_row or not user_row["is_active"]:
                raise TokenError("utente non più attivo")

            # Mark vecchio come revocato (il replaced_by verrà settato sotto).
            cursor.execute(
                "UPDATE refresh_tokens SET revoked_at = %s WHERE id = %s",
                (now, row["id"]),
            )
            conn.commit()

    # Nuovi token emessi fuori dalla transazione precedente perché issue_refresh_token
    # apre la propria connessione. La famiglia è preservata.
    new_refresh, refresh_exp, _ = issue_refresh_token(
        user_id=str(row["user_id"]),
        tenant_id=str(row["tenant_id"]),
        family_id=str(row["family_id"]),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    new_hash = _hash_token(new_refresh)

    # Collega vecchio → nuovo per audit chain.
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM refresh_tokens WHERE token_hash = %s",
                (new_hash,),
            )
            new_row = cursor.fetchone()
            if new_row:
                cursor.execute(
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
    """Revoca un refresh token specifico (logout singola sessione)."""
    presented_hash = _hash_token(presented_token)
    now = datetime.datetime.now(datetime.timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE refresh_tokens SET revoked_at = %s "
                "WHERE token_hash = %s AND revoked_at IS NULL",
                (now, presented_hash),
            )
            revoked = cursor.rowcount > 0
        conn.commit()
    return revoked


def revoke_all_for_user(user_id: str) -> int:
    """Revoca ogni refresh del user (logout everywhere / password change)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE refresh_tokens SET revoked_at = %s "
                "WHERE user_id = %s AND revoked_at IS NULL",
                (now, user_id),
            )
            n = cursor.rowcount
        conn.commit()
    return n

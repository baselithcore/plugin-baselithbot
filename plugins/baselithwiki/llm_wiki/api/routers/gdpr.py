"""GDPR / DSAR endpoints.

Endpoint:

- ``GET    /api/me/export`` — Data Subject Access Request (Art. 15 GDPR).
  Restituisce JSON dump completo dei dati personali dell'utente
  autenticato: profilo, conversazioni + messaggi, memorie, feedback,
  audit events.
- ``DELETE /api/me`` — Right to Erasure (Art. 17 GDPR). Hard delete
  account utente. CASCADE rimuove conversazioni, memorie, feedback,
  refresh tokens, role grants. ``audit_events.user_id`` SET NULL
  preserva traccia anonimizzata (accountability — Art. 5(2)).

Vincoli:

- Endpoint richiedono autenticazione (``require_user``).
- Self-service: l'utente opera solo sui propri dati. Admin DSAR
  per-altro-utente passa da endpoint RBAC dedicato (TODO se richiesto).
- Last-superuser protection: se l'utente è l'ultimo superuser,
  ``DELETE`` viene rifiutato con 409 Conflict.
- Tutti gli accessi DSAR sono auditati (``gdpr.export`` / ``gdpr.delete``)
  per dimostrare conformità in caso di audit ispettivo.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from psycopg.rows import dict_row

from llm_wiki import config
from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import _client_ip, require_user
from llm_wiki.auth.tokens import revoke_all_for_user
from llm_wiki.db.connection import get_connection
from llm_wiki.db.conversations import list_conversations, list_messages
from llm_wiki.db.feedback import list_feedback
from llm_wiki.db.memories import list_memories
from llm_wiki.db.roles import get_user_roles
from llm_wiki.db.users import delete_user, get_user_by_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/me", tags=["gdpr"])


# --- export ---------------------------------------------------------------


@router.get("/export")
def export_my_data(
    request: Request,
    user: dict = Depends(require_user),
) -> dict[str, Any]:
    """DSAR Art. 15 — esporta tutti i dati personali dell'utente.

    Output structure stabile per integrazione esterna (DPO toolchain):

    .. code-block:: json

       {
         "exported_at": "...",
         "schema_version": 1,
         "user": {...},
         "conversations": [{"id": "...", "messages": [...]}, ...],
         "memories": [...],
         "feedback": [...],
         "audit_events": [...]
       }
    """
    user_id = str(user["id"])
    tenant_id = str(user.get("tenant_id") or "")

    profile = get_user_by_id(user_id) or {}
    profile.pop("password_hash", None)  # never export hash

    convs = list_conversations(user_id=user_id) or []
    convs_full: list[dict[str, Any]] = []
    for c in convs:
        msgs = list_messages(conversation_id=str(c["id"]), limit=1000)
        c_dump = dict(c)
        c_dump["messages"] = msgs
        convs_full.append(c_dump)

    memories = list_memories(user_id=user_id, limit=1000)
    feedback = list_feedback(user_id=user_id, limit=1000)
    audit = _list_audit_for_user(user_id)

    write_event(
        kind="gdpr.export",
        tenant_id=tenant_id or None,
        user_id=user_id,
        payload={
            "conversations": len(convs_full),
            "memories": len(memories),
            "feedback": len(feedback),
            "audit_events": len(audit),
        },
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "schema_version": 1,
        "user": profile,
        "conversations": convs_full,
        "memories": memories,
        "feedback": feedback,
        "audit_events": audit,
    }


# --- delete ---------------------------------------------------------------


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_my_account(
    request: Request,
    user: dict = Depends(require_user),
) -> None:
    """DSAR Art. 17 — right to erasure self-service.

    CASCADE su ``users.id`` cancella conversazioni, messaggi, memorie,
    feedback, refresh tokens, role/domain grants. ``audit_events.user_id``
    SET NULL — traccia anonimizzata persiste.
    """
    user_id = str(user["id"])
    tenant_id = str(user.get("tenant_id") or "")

    # Last-superuser guard: se l'utente è ultimo superuser, rifiuta.
    # Importazione locale per evitare cicli al boot.
    if _is_last_superuser(user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Impossibile cancellare l'unico superuser. Promuovi prima un "
                "altro utente al ruolo superuser."
            ),
        )

    # Audit PRIMA della delete (user_id ancora referenziato).
    write_event(
        kind="gdpr.delete",
        tenant_id=tenant_id or None,
        user_id=user_id,
        payload={"email_hash": _email_hash(user.get("email", ""))},
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    revoke_all_for_user(user_id)
    if not delete_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cancellazione account fallita.",
        )


# --- internals ------------------------------------------------------------


def _email_hash(email: str) -> str:
    """SHA-256 trunc 16 dell'email per audit anonimizzato (no PII)."""
    import hashlib

    if not email:
        return ""
    return hashlib.sha256(email.lower().encode("utf-8")).hexdigest()[:16]


def _is_last_superuser(user_id: str) -> bool:
    """Conta superuser globali (system role, tenant_id NULL).

    Atomicità relativa: questa è una check pre-delete; il vero blocco
    è la migrazione 008 ``revoke_role(protect_last_superuser=True)``,
    ma qui non revochiamo il ruolo — cancelliamo l'utente. Il rischio
    di race è la finestra fra check e DELETE; mitigato perché:
    1. UI normale non promuove/cancella superuser concorrentemente.
    2. CASCADE su ``user_roles`` rimuove il grant; un secondo superuser
       creato fra check e DELETE comunque sopravvive.
    """
    if not config.POSTGRES_ENABLED:
        return False
    roles = get_user_roles(user_id)
    is_super = any(r.get("slug") == "superuser" for r in roles)
    if not is_super:
        return False
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM user_roles ur
                    JOIN roles r ON r.id = ur.role_id
                    WHERE r.slug = 'superuser'
                      AND r.is_system = TRUE
                      AND ur.user_id <> %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
        finally:
            conn.rollback()
    return int(row[0]) == 0 if row else True


def _list_audit_for_user(user_id: str, limit: int = 1000) -> list[dict[str, Any]]:
    if not config.POSTGRES_ENABLED:
        return []
    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, kind, payload, ip_address, user_agent, created_at
                    FROM audit_events
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return rows


__all__ = ["router"]

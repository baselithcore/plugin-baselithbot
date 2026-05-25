"""
Audit logging helper (Sprint 6).

Registra eventi sensibili su `audit_events` per compliance GDPR Art. 32
e forensics. Append-only, non-blocking: se il log fallisce (DB giù, ecc.)
l'errore viene loggato ma NON blocca la request principale.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from starlette.requests import Request

from agent_jira.db.connection import get_connection
from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.config import POSTGRES_ENABLED

logger = logging.getLogger(__name__)


def record(
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """
    Registra un evento audit. Non solleva eccezioni al chiamante.

    Args:
        action: es. "jira_settings.update", "workspace.delete"
        resource_type: es. "tenant", "user", "jira_config"
        resource_id: id risorsa oggetto dell'azione
        user_id: se None, eredita dal context (non implementato qui)
        tenant_id: se None, eredita dal contextvar
        metadata: dict JSON-serializzabile (evita PII!)
        request: opzionale, estrae IP e user-agent dagli header
    """
    if not POSTGRES_ENABLED:
        return

    if tenant_id is None:
        tenant_id = get_current_tenant_id()

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    if request is not None:
        try:
            # X-Forwarded-For ha precedenza se dietro proxy (prendi il primo hop).
            xff = request.headers.get("x-forwarded-for", "")
            if xff:
                ip_address = xff.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host
            user_agent = request.headers.get("user-agent", "")[:500] or None
        except Exception:
            pass

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_events (
                        tenant_id, user_id, action, resource_type, resource_id,
                        metadata, ip_address, user_agent
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    """,
                    (
                        tenant_id,
                        user_id,
                        action,
                        resource_type,
                        resource_id,
                        json.dumps(metadata or {}),
                        ip_address,
                        user_agent,
                    ),
                )
            conn.commit()
    except Exception as exc:
        # Non bloccare mai la request principale per un fallimento audit.
        logger.warning(
            "Audit log failed action=%s resource=%s: %s",
            action,
            resource_type,
            exc,
        )

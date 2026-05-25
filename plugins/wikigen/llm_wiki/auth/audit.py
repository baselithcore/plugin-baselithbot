"""Append-only audit log writer.

Sottile wrapper sopra ``audit_events`` (migration 005). Esposto come
modulo separato perché chiamato da auth/router/middleware/bootstrap —
una sola implementazione del formato evento + safety net (logging
fallback se DB irraggiungibile, mai bloccante).

Vocabolario kind (esteso ad-hoc):

- ``auth.login``, ``auth.login.failed``
- ``auth.logout``, ``auth.refresh``, ``auth.refresh.replay``
- ``auth.register``
- ``admin.bootstrap``, ``admin.scaffold``, ``admin.tenant.delete``
- ``memory.delete``, ``conversation.delete``
"""

from __future__ import annotations

import json
import logging
from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection

logger = logging.getLogger(__name__)


def write_event(
    kind: str,
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persistenza best-effort.

    Mai solleva: logging downgrade su WARNING se la write fallisce.
    L'audit non deve far fallire l'operazione utente (login OK ma audit
    KO → utente entra comunque, sysop vede warning su stderr).
    """
    if not config.POSTGRES_ENABLED:
        return

    serialized = json.dumps(payload or {}, default=str)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_events
                        (tenant_id, user_id, kind, payload,
                         ip_address, user_agent)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                    """,
                    (
                        tenant_id,
                        user_id,
                        kind,
                        serialized,
                        ip_address,
                        (user_agent or "")[:500] or None,
                    ),
                )
            conn.commit()
    except Exception as exc:
        logger.warning("[audit] write failed (%s): %s", kind, exc)


__all__ = ["write_event"]

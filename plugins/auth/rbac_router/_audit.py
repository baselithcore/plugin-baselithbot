"""Best-effort audit logging for RBAC mutations.

Never raises — an audit failure must not block an RBAC operation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request

from core.observability.logging import get_logger

logger = get_logger(__name__)


def audit_rbac(
    request: Optional[Request],
    actor_id: str,
    action: str,
    target_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Write an RBAC audit entry via the registered AuditLogger, if available."""
    try:
        from core.di.container import ServiceRegistry
        from plugins.auth.audit import AuditLogger

        audit = ServiceRegistry.get(AuditLogger)
        if audit is None:
            return
        ip = request.client.host if request and request.client else None
        audit.log(action, actor_id, target_id=target_id, details=details, ip_address=ip)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RBAC audit logging failed: %s", exc)


__all__ = ["audit_rbac"]

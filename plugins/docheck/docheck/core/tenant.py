"""Tenant context propagation. MVP single-tenant (`tenant_id="default"`).

In multi-tenant deploy, tenant_id estratto da JWT claim `tid` o header `X-Tenant-Id`.
ContextVar isolato per request → safe under asyncio concurrency.
"""

from contextvars import ContextVar
from typing import Any

from .config import settings

_tenant_var: ContextVar[str] = ContextVar("docheck_tenant_id", default="default")


def current_tenant() -> str:
    return _tenant_var.get()


def set_tenant(tenant_id: str) -> Any:
    """Set tenant for current async context. Returns token for reset."""
    return _tenant_var.set(tenant_id)


def reset_tenant(token: Any) -> None:
    _tenant_var.reset(token)


def resolve_tenant_from_request(headers: dict[str, str], jwt_claims: dict[str, Any] | None = None) -> str:
    """Priority: JWT `tid` claim > header `X-Tenant-Id` > default."""
    if not settings.multitenant_enabled:
        return "default"
    if jwt_claims and "tid" in jwt_claims:
        return str(jwt_claims["tid"])
    return headers.get("x-tenant-id") or headers.get("X-Tenant-Id") or "default"

"""
Webhook management router (scope-gated CRUD).

Thin HTTP surface over :mod:`core.webhooks`. Endpoints are tenant-scoped: a
request can only see and mutate webhooks owned by the authenticated identity's
tenant. Capabilities:

* ``webhooks:read``  — list endpoints, list deliveries.
* ``webhooks:write`` — create/delete endpoints, replay deliveries.

The ``ADMIN`` role holds the ``*`` wildcard and satisfies both implicitly.
The signing secret is returned **once** at creation and never again (the stored
endpoint redacts it).
"""

from __future__ import annotations

import secrets
from typing import Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth.types import AuthUser, InsufficientScopeError
from core.middleware import require_user
from core.observability.logging import get_logger
from core.webhooks import WebhookSSRFError, get_webhook_service

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _scope_guard(required: str) -> Callable[..., AuthUser]:
    """Build a dependency that enforces a single capability ``scope``."""

    def _dep(request: Request, _: str = Depends(require_user)) -> AuthUser:
        user = getattr(request.state, "user", None)
        if not isinstance(user, AuthUser) or not user.has_scope(required):
            raise InsufficientScopeError(
                f"Scope '{required}' is required for this webhook operation."
            )
        return user

    return _dep


require_read = _scope_guard("webhooks:read")
require_write = _scope_guard("webhooks:write")


class CreateWebhookRequest(BaseModel):
    """Payload to register a new webhook endpoint."""

    url: str = Field(..., min_length=1)
    event_types: Optional[List[str]] = None
    description: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


@router.post("", status_code=201)
async def create_webhook(
    body: CreateWebhookRequest, user: AuthUser = Depends(require_write)
) -> dict:
    """Register an endpoint; returns the signing secret once (then redacted)."""
    service = get_webhook_service()
    secret = f"whsec_{secrets.token_urlsafe(32)}"
    try:
        endpoint = await service.register_endpoint(
            body.url,
            secret,
            tenant_id=user.tenant_id,
            event_types=set(body.event_types) if body.event_types else None,
            description=body.description,
            headers=body.headers,
        )
    except WebhookSSRFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"secret": secret, "endpoint": endpoint.redacted()}


@router.get("")
async def list_webhooks(user: AuthUser = Depends(require_read)) -> dict:
    """List the tenant's registered endpoints (secrets redacted)."""
    service = get_webhook_service()
    endpoints = await service.list_endpoints(user.tenant_id)
    return {"endpoints": [ep.redacted() for ep in endpoints]}


@router.get("/deliveries")
async def list_deliveries(user: AuthUser = Depends(require_read)) -> dict:
    """List recent delivery attempts for the tenant."""
    service = get_webhook_service()
    deliveries = await service.store.list_deliveries(user.tenant_id)
    return {"deliveries": [d.model_dump() for d in deliveries]}


@router.post("/deliveries/{delivery_id}/replay")
async def replay_delivery(
    delivery_id: str, user: AuthUser = Depends(require_write)
) -> dict:
    """Re-attempt a stored delivery (tenant-scoped); 404 if not found."""
    service = get_webhook_service()
    delivery = await service.replay_delivery(delivery_id, tenant_id=user.tenant_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")
    return {"delivery": delivery.model_dump()}


@router.delete("/{endpoint_id}")
async def delete_webhook(
    endpoint_id: str, user: AuthUser = Depends(require_write)
) -> dict:
    """Delete an endpoint owned by the tenant; 404 if missing/cross-tenant."""
    service = get_webhook_service()
    deleted = await service.delete_endpoint(endpoint_id, tenant_id=user.tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Endpoint not found.")
    return {"status": "deleted"}

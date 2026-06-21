"""Self-service multi-tenancy endpoints, mounted under ``/auth/tenants``.

Let an authenticated user see the tenants they belong to and switch their
active tenant. Switching re-issues an access token scoped to the chosen tenant
(after verifying membership) and persists it as the user's default, so the
choice survives a token refresh. The refresh-token session is untouched.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthManager, AuthUser
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
    require_auth,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._models import TokenResponse
from plugins.auth.router._tenant_models import MyTenantOut, SwitchTenantRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/tenants")


@router.get("", response_model=List[MyTenantOut])
async def my_tenants(
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> List[MyTenantOut]:
    """Tenants the current user belongs to (empty when on a personal tenant)."""
    rows = persistence.list_user_tenants(user.user_id)
    return [
        MyTenantOut(
            id=str(r["id"]),
            slug=r["slug"],
            name=r["name"],
            status=r["status"],
            role=r["role"],
            is_default=bool(r["is_default"]),
        )
        for r in rows
    ]


@router.post("/switch", response_model=TokenResponse)
async def switch_tenant(
    body: SwitchTenantRequest,
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
    config: AuthConfig = Depends(get_auth_config_dep),
) -> TokenResponse:
    """Switch the active tenant and mint a fresh access token scoped to it.

    Membership is verified server-side — a user can only switch to a tenant
    they belong to, so this is not a path to cross-tenant access.
    """
    if not persistence.is_member(user.user_id, body.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of the requested tenant",
        )

    # Persist the choice so a later /refresh resolves the same tenant, then mint
    # a new access token carrying it. The refresh cookie/session is unchanged.
    persistence.set_default_tenant(user.user_id, body.tenant_id)
    access_token = await auth_manager.create_token(
        user.user_id, user.roles, tenant_id=body.tenant_id
    )
    logger.info("User %s switched active tenant to %s", user.user_id, body.tenant_id)
    return TokenResponse(
        access_token=access_token,
        expires_in=config.session_lifetime,
    )

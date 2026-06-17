"""Personal access token (API key) self-service endpoints under /me/api-keys."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    forbid_while_impersonating,
    get_auth_config_dep,
    get_auth_persistence_dep,
    get_current_active_user,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._models import (
    ApiKeyCreated,
    ApiKeyCreateRequest,
    ApiKeyInfo,
    MessageResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/me/api-keys")


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


def _to_info(row: dict) -> ApiKeyInfo:
    return ApiKeyInfo(
        id=str(row["id"]),
        name=row["name"],
        prefix=row["prefix"],
        scopes=list(row.get("scopes") or []),
        expires_at=_iso(row.get("expires_at")),
        last_used_at=_iso(row.get("last_used_at")),
        revoked_at=_iso(row.get("revoked_at")),
        created_at=_iso(row.get("created_at")),
    )


@router.get("", response_model=list[ApiKeyInfo])
async def list_my_keys(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """List the current user's API keys (metadata only)."""
    return [_to_info(r) for r in persistence.list_api_keys(user.user_id)]


@router.post(
    "",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(forbid_while_impersonating)],
)
async def create_my_key(
    body: ApiKeyCreateRequest,
    user: AuthUser = Depends(get_current_active_user),
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Mint a new API key. The raw secret is returned exactly once."""
    if not config.api_keys_enabled:
        raise HTTPException(status_code=403, detail="API keys are disabled")

    expires_at = None
    max_days = config.api_key_max_lifetime_days
    days = body.expires_in_days
    if max_days and days and days > max_days:
        days = max_days
    if max_days and not days:
        days = max_days
    if days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    raw, record = persistence.create_api_key(
        user_id=user.user_id,
        name=body.name,
        scopes=body.scopes or [],
        expires_at=expires_at,
        created_by=user.user_id,
    )
    persistence.record_login_event(user.user_id, "api_key_created", method="api_key")
    logger.info("User %s created API key %s", user.user_id, record["prefix"])
    return ApiKeyCreated(key=raw, info=_to_info(record))


@router.delete("/{key_id}", response_model=MessageResponse)
async def revoke_my_key(
    key_id: str,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Revoke one of the current user's API keys."""
    if not persistence.revoke_api_key(key_id, user.user_id):
        raise HTTPException(status_code=404, detail="API key not found")
    persistence.record_login_event(user.user_id, "api_key_revoked", method="api_key")
    return MessageResponse(message="API key revoked.")

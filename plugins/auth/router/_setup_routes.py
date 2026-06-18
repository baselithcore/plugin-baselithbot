"""First-run setup endpoints: detect an un-provisioned system and create the
initial admin via the UI wizard.

Both routes are intentionally public (no auth) — a fresh install has no account
to authenticate with. ``/setup/initialize`` is protected instead by the
fail-closed invariant in :mod:`plugins.auth.setup_service`: it only works while
the user table is empty, and is rate-limited to blunt brute-force racing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from core.observability.logging import get_logger
from plugins.auth.audit import AuditAction
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.rate_limiting import RateLimit as RateLimiter
from plugins.auth.admin_router._helpers import get_client_ip
from plugins.auth.router._helpers import issue_tokens
from plugins.auth.router._models import TokenResponse
from plugins.auth.setup_service import (
    SetupAlreadyCompleted,
    SetupValidationError,
    create_initial_admin,
    is_setup_needed,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/setup", tags=["Setup"])


class SetupStatusResponse(BaseModel):
    """Whether the first-run wizard should be shown."""

    needs_setup: bool


class SetupInitializeRequest(BaseModel):
    """Payload to create the initial admin."""

    email: str = Field(..., description="Admin email")
    password: str = Field(..., min_length=8)
    username: str | None = Field(None, description="Optional username")


@router.get("/status", response_model=SetupStatusResponse)
async def setup_status(
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> SetupStatusResponse:
    """Report whether the system still needs its initial admin."""
    return SetupStatusResponse(needs_setup=is_setup_needed(persistence))


@router.post(
    "/initialize",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    responses={
        400: {"description": "Validation failed"},
        409: {"description": "Setup already completed"},
        429: {"description": "Too many requests"},
    },
)
async def setup_initialize(
    data: SetupInitializeRequest,
    request: Request,
    response: Response,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    config: AuthConfig = Depends(get_auth_config_dep),
    auth_manager=Depends(get_auth_manager_dep),
    audit=Depends(get_audit_logger_dep),
) -> TokenResponse:
    """Create the initial admin and log them in.

    Returns access + refresh tokens so the wizard can immediately drive the
    mandatory MFA enrollment (``/mfa/setup`` → ``/mfa/enable``).
    """
    try:
        user = await create_initial_admin(
            persistence,
            config,
            email=data.email,
            password=data.password,
            username=data.username,
        )
    except SetupAlreadyCompleted as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except SetupValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    audit.log(
        action=AuditAction.USER_CREATED,
        actor_id=user.id,
        target_id=user.id,
        details={
            "email": user.email,
            "roles": [r.value for r in user.roles],
            "via": "setup_wizard",
        },
        ip_address=get_client_ip(request),
    )
    logger.info("Setup wizard completed: admin %s created", user.email)

    return await issue_tokens(
        user.id, user.roles, response, persistence, auth_manager, config
    )


__all__ = ["router"]

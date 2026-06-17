"""Admin user lifecycle: email invitations and suspend/deactivate/reactivate."""

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import AuthRole, AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._helpers import get_client_ip
from plugins.auth.admin_router._models import (
    InvitationResponse,
    InviteUserRequest,
    MessageResponse,
    SetStatusRequest,
)
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_admin,
)
from plugins.auth.mailer import get_mailer
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._helpers import resolve_locale

logger = get_logger(__name__)

router = APIRouter()


@router.post("/invitations", response_model=InvitationResponse, status_code=201)
async def invite_user(
    body: InviteUserRequest,
    request: Request,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """Invite a user by email; they accept and set their own password."""
    if persistence.get_user_by_email(body.email):
        raise HTTPException(
            status_code=409, detail="A user with this email already exists"
        )
    token = persistence.create_invitation(body.email, body.roles, admin.user_id)
    await get_mailer().send_invitation(body.email, token, resolve_locale(request))
    audit.log(
        action=AuditAction.USER_INVITED,
        actor_id=admin.user_id,
        target_id=None,
        details={"email": body.email, "roles": body.roles},
        ip_address=get_client_ip(request),
    )
    logger.info("Admin %s invited %s", admin.user_id, body.email)
    invites = persistence.list_invitations()
    latest = next((i for i in invites if i["email"] == body.email.lower()), None)
    return InvitationResponse(
        id=str(latest["id"]) if latest else "",
        email=body.email,
        roles=body.roles,
        expires_at=latest.get("expires_at") if latest else None,
        created_at=latest.get("created_at") if latest else None,
    )


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    _: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """List pending invitations."""
    return [
        InvitationResponse(
            id=str(i["id"]),
            email=i["email"],
            roles=list(i["roles"]),
            expires_at=i.get("expires_at"),
            accepted_at=i.get("accepted_at"),
            created_at=i.get("created_at"),
        )
        for i in persistence.list_invitations()
    ]


@router.delete("/invitations/{invitation_id}", response_model=MessageResponse)
async def revoke_invitation(
    invitation_id: str,
    request: Request,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """Revoke a pending invitation."""
    if not persistence.revoke_invitation(invitation_id):
        raise HTTPException(status_code=404, detail="Invitation not found")
    audit.log(
        action=AuditAction.INVITATION_REVOKED,
        actor_id=admin.user_id,
        target_id=None,
        details={"invitation_id": invitation_id},
        ip_address=get_client_ip(request),
    )
    return MessageResponse(message="Invitation revoked.")


@router.post("/users/{user_id}/status", response_model=MessageResponse)
async def set_user_status(
    user_id: str,
    body: SetStatusRequest,
    request: Request,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """Suspend, deactivate, or reactivate a user account."""
    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Don't let the last active admin disable themselves out of the system.
    if (
        body.status != "active"
        and AuthRole.ADMIN in user.roles
        and persistence.count_active_admins() <= 1
    ):
        raise HTTPException(
            status_code=400, detail="Cannot disable the last active admin"
        )

    persistence.set_user_status(user_id, body.status)
    if body.status != "active":
        persistence.revoke_all_user_tokens(user_id)
    audit.log(
        action=AuditAction.USER_STATUS_CHANGED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"email": user.email, "status": body.status},
        ip_address=get_client_ip(request),
    )
    logger.info("Admin %s set user %s status=%s", admin.user_id, user_id, body.status)
    return MessageResponse(message=f"User status set to {body.status}.")

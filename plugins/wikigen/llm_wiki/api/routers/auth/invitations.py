"""Invitation flow: create / peek / accept."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from llm_wiki import config
from llm_wiki.api.routers.auth.helpers import (
    check_rate,
    client_ip,
    set_refresh_cookie,
    ua,
)
from llm_wiki.api.routers.auth.models import (
    InviteAcceptRequest,
    InviteCreateRequest,
    InviteCreateResponse,
    InvitePeekResponse,
    TokenResponse,
)
from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import require_admin
from llm_wiki.auth.tokens import issue_access_token, issue_refresh_token

router = APIRouter()


@router.post(
    "/invite",
    response_model=InviteCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation_endpoint(
    body: InviteCreateRequest,
    request: Request,
    actor: dict = Depends(require_admin),
) -> InviteCreateResponse:
    """Crea invitation per un nuovo utente (raccomandato per onboarding
    cliente). L'actor deve essere superuser o admin (tier 008+).

    Per ruoli ``superuser``/``admin``: l'actor deve possedere il
    permesso ``rbac.assign.<role_slug>`` corrispondente. Per
    ``moderator``/``user``: idem. Per ruolo ``None`` (auto-detect):
    primo invite di sistema → ``superuser``; altrimenti → ``user``.

    Risposta include ``accept_url`` plain — UNICA esposizione del
    token. Maintainer mostra/invia al destinatario via canale sicuro.
    """
    from llm_wiki.auth.invitations import InvitationError, create_invitation
    from llm_wiki.auth.permissions import ROLE_ASSIGN_PERMISSION

    if body.role_slug:
        required = ROLE_ASSIGN_PERMISSION.get(body.role_slug)
        if not required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ruolo system non riconosciuto: '{body.role_slug}'.",
            )
        if required not in (actor.get("perms") or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permesso richiesto: {required}.",
            )

    try:
        info = create_invitation(
            email=body.email,
            role_slug=body.role_slug,
            tenant_slug=body.tenant_slug,
            display_name=body.display_name,
            note=body.note,
            created_by=actor["id"],
            ttl_hours=body.ttl_hours,
        )
    except InvitationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    write_event(
        "auth.invite.create",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "invitation_id": info["id"],
            "target_email": body.email,
            "role_slug": body.role_slug,
        },
        ip_address=client_ip(request),
    )

    accept_url = f"/setup/invite?token={info['token_plain']}"
    return InviteCreateResponse(
        id=info["id"],
        email=body.email,
        accept_url=accept_url,
        expires_at=info["expires_at"],
    )


@router.get("/invite/{token}", response_model=InvitePeekResponse)
def peek_invitation_endpoint(token: str) -> InvitePeekResponse:
    """Lookup pubblico (non consuma). Frontend AcceptInvite chiama
    questo per pre-popolare il form. Stato 200 sempre — il flag
    ``valid`` indica se il token è utilizzabile."""
    from llm_wiki.auth.invitations import peek_invitation

    info = peek_invitation(token)
    if info is None:
        return InvitePeekResponse(valid=False, reason="unknown")
    if info["used"]:
        return InvitePeekResponse(valid=False, reason="used")
    if info["expired"]:
        return InvitePeekResponse(valid=False, reason="expired")
    return InvitePeekResponse(
        valid=True,
        email=info["email"],
        role_slug=info["role_slug"],
        display_name=info["display_name"],
        expires_at=info["expires_at"],
    )


@router.post("/invite/accept", response_model=TokenResponse)
def accept_invitation_endpoint(
    body: InviteAcceptRequest,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Consuma l'invitation: crea utente + assegna ruolo + login.

    - ``role_slug`` dell'invito determina ruolo system. Se NULL e non
      esistono altri user → ``superuser`` (primo bootstrap via invite).
      Se NULL e users esistono → ``user`` (default conservativo).
    - Email viene presa dall'invito server-side (non dal body) per
      prevenire confusion attacks.
    - Login implicito: access + refresh cookie già armati.
    """
    from llm_wiki.auth.bootstrap import BootstrapError, create_superuser
    from llm_wiki.auth.invitations import InvitationError, consume_invitation
    from llm_wiki.db.users import count_users

    check_rate(
        identifier=f"invite-accept:{client_ip(request)}",
        limit=max(1, config.RATE_LIMIT_ADMIN_PER_MINUTE // 6),
        window=config.RATE_LIMIT_WINDOW_SECONDS,
    )

    try:
        invite = consume_invitation(body.token)
    except InvitationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    role_slug = invite.get("role_slug")
    if not role_slug:
        try:
            role_slug = "superuser" if count_users() == 0 else "user"
        except Exception:
            role_slug = "user"

    if role_slug == "superuser":
        try:
            info = create_superuser(
                email=invite["email"],
                password=body.password,
                display_name=body.display_name or invite.get("display_name") or "",
                tenant_slug=invite.get("tenant_slug") or None,
                source="invite",
            )
        except BootstrapError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        user_id = info["user_id"]
        tenant_id = info["tenant_id"]
    else:
        from llm_wiki.db.roles import assign_role_to_user, list_roles
        from llm_wiki.db.tenants import create_tenant_with_owner
        from llm_wiki.db.users import hash_password

        tenant_slug = (
            invite.get("tenant_slug")
            or (invite["email"].replace("@", "-").replace(".", "-")[:50])
        )
        try:
            result = create_tenant_with_owner(
                tenant_name=f"{invite['email']} Workspace",
                tenant_slug=tenant_slug,
                user_email=invite["email"],
                user_password_hash=hash_password(body.password),
                user_display_name=(
                    body.display_name or invite.get("display_name") or ""
                ),
                plan="free",
                role="user",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflitto creazione utente: {exc}",
            ) from exc
        user_id = str(result["user"]["id"])
        tenant_id = str(result["tenant"]["id"])
        role_row = next(
            (r for r in list_roles() if r["slug"] == role_slug and r["is_system"]),
            None,
        )
        if role_row:
            assign_role_to_user(user_id, role_row["id"])

    write_event(
        "auth.invite.accept",
        tenant_id=tenant_id,
        user_id=user_id,
        payload={
            "invitation_id": invite["id"],
            "email": invite["email"],
            "role_slug": role_slug,
        },
        ip_address=client_ip(request),
        user_agent=ua(request),
    )

    access, access_exp = issue_access_token(
        user_id=user_id, tenant_id=tenant_id, role="admin"
    )
    refresh_token, refresh_exp, _family = issue_refresh_token(
        user_id=user_id,
        tenant_id=tenant_id,
        user_agent=ua(request),
        ip_address=client_ip(request),
    )
    set_refresh_cookie(response, refresh_token, refresh_exp)
    return TokenResponse(
        access_token=access,
        expires_at=access_exp,
        user_id=user_id,
        tenant_id=tenant_id,
        role="admin",
        email=invite["email"],
    )

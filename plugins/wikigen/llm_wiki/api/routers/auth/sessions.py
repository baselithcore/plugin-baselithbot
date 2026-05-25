"""Session lifecycle: register, login, refresh, logout, me, password."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from llm_wiki import config
from llm_wiki.api.routers.auth.helpers import (
    REFRESH_COOKIE_NAME,
    RL_LOGIN_PER_MIN_EMAIL,
    RL_LOGIN_PER_MIN_IP,
    RL_REFRESH_PER_MIN_IP,
    RL_REGISTER_PER_HOUR_IP,
    check_rate,
    clear_refresh_cookie,
    client_ip,
    set_refresh_cookie,
    slugify,
    ua,
)
from llm_wiki.api.routers.auth.models import (
    GroupRef,
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    TokenResponse,
    UserMeResponse,
)
from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import require_admin, require_user
from llm_wiki.auth.passwords import verify_password
from llm_wiki.auth.tokens import (
    TokenError,
    issue_access_token,
    issue_refresh_token,
    revoke_all_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
)
from llm_wiki.db.tenants import (
    create_tenant_with_owner,
    get_tenant_by_slug,
)
from llm_wiki.db.users import (
    get_user_by_email_with_credentials,
    hash_password,
    update_last_login,
    update_password,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Crea tenant + user. Apre subito una sessione (login implicito).

    Modalità:
    - ``AUTH_PUBLIC_REGISTRATION=true`` → chiunque può registrarsi.
    - ``AUTH_PUBLIC_REGISTRATION=false`` (default) → richiede bearer admin.
    """
    ip = client_ip(request)
    check_rate(f"register:ip:{ip}", RL_REGISTER_PER_HOUR_IP, 3600)

    if not config.AUTH_PUBLIC_REGISTRATION:
        # Admin-gated: richiede chi chiama sia admin loggato.
        # `require_admin` non si può usare come dependency qui se vogliamo
        # che il flag aperto consenta anonimi. Trick: se chiamato senza
        # auth, raise; altrimenti verifica role.
        admin = require_admin(request)
        logger.info("[auth] admin %s sta registrando %s", admin["email"], body.email)

    tenant_slug_base = (
        slugify(body.tenant_name) if body.tenant_name else slugify(body.email.split("@")[0])
    )

    tenant_slug = tenant_slug_base
    if get_tenant_by_slug(tenant_slug):
        import secrets as _s

        tenant_slug = f"{tenant_slug_base}-{_s.token_hex(3)}"

    try:
        result = create_tenant_with_owner(
            tenant_name=body.tenant_name or body.display_name or body.email,
            tenant_slug=tenant_slug,
            user_email=body.email,
            user_password_hash=hash_password(body.password),
            user_display_name=body.display_name,
            plan="free",
            role="user",
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="email già registrata",
            ) from exc
        logger.exception("[auth] register failed")
        raise HTTPException(status_code=500, detail="registrazione fallita") from exc

    user = result["user"]
    tenant = result["tenant"]
    access, access_exp = issue_access_token(
        user_id=user["id"], tenant_id=tenant["id"], role=user["role"]
    )
    refresh, refresh_exp, _family = issue_refresh_token(
        user_id=user["id"],
        tenant_id=tenant["id"],
        user_agent=ua(request),
        ip_address=ip,
    )
    set_refresh_cookie(response, refresh, refresh_exp)

    write_event(
        "auth.register",
        tenant_id=tenant["id"],
        user_id=user["id"],
        payload={"email": user["email"], "tenant_slug": tenant["slug"]},
        ip_address=ip,
        user_agent=ua(request),
    )

    return TokenResponse(
        access_token=access,
        expires_at=access_exp,
        user_id=user["id"],
        tenant_id=tenant["id"],
        role=user["role"],
        email=user["email"],
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, response: Response) -> TokenResponse:
    ip = client_ip(request)
    check_rate(f"login:ip:{ip}", RL_LOGIN_PER_MIN_IP, 60)
    check_rate(f"login:email:{body.email.lower()}", RL_LOGIN_PER_MIN_EMAIL, 60)

    user = get_user_by_email_with_credentials(str(body.email))
    if not user or not user.get("is_active"):
        write_event(
            "auth.login.failed",
            payload={"email": str(body.email), "reason": "no_user"},
            ip_address=ip,
            user_agent=ua(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenziali non valide",
        )
    if not verify_password(user["password_hash"], body.password):
        write_event(
            "auth.login.failed",
            tenant_id=str(user.get("tenant_id") or ""),
            user_id=str(user["id"]),
            payload={"email": str(body.email), "reason": "bad_password"},
            ip_address=ip,
            user_agent=ua(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenziali non valide",
        )

    user_id = str(user["id"])
    tenant_id = str(user["tenant_id"])
    role = user["role"]

    access, access_exp = issue_access_token(user_id=user_id, tenant_id=tenant_id, role=role)
    refresh, refresh_exp, _family = issue_refresh_token(
        user_id=user_id,
        tenant_id=tenant_id,
        user_agent=ua(request),
        ip_address=ip,
    )
    set_refresh_cookie(response, refresh, refresh_exp)
    update_last_login(user_id)

    write_event(
        "auth.login",
        tenant_id=tenant_id,
        user_id=user_id,
        payload={"email": user["email"]},
        ip_address=ip,
        user_agent=ua(request),
    )

    return TokenResponse(
        access_token=access,
        expires_at=access_exp,
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        email=user["email"],
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response) -> TokenResponse:
    ip = client_ip(request)
    check_rate(f"refresh:ip:{ip}", RL_REFRESH_PER_MIN_IP, 60)

    presented = request.cookies.get(REFRESH_COOKIE_NAME)
    if not presented:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token mancante",
        )

    try:
        result = rotate_refresh_token(presented, user_agent=ua(request), ip_address=ip)
    except TokenError as exc:
        # Cookie corrotto/scaduto/replay → cancellalo, force re-login.
        clear_refresh_cookie(response)
        write_event(
            "auth.refresh.failed",
            payload={"reason": str(exc)},
            ip_address=ip,
            user_agent=ua(request),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    set_refresh_cookie(response, result["refresh_token"], result["refresh_token_expires_at"])

    from llm_wiki.db.users import get_user_by_id

    user = get_user_by_id(result["user_id"])
    role = (user or {}).get("role", "user")
    email = (user or {}).get("email", "")

    return TokenResponse(
        access_token=result["access_token"],
        expires_at=result["access_token_expires_at"],
        user_id=result["user_id"],
        tenant_id=result["tenant_id"],
        role=role,
        email=email,
    )


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    presented = request.cookies.get(REFRESH_COOKIE_NAME)
    revoked = False
    if presented:
        revoked = revoke_refresh_token(presented)
    clear_refresh_cookie(response)
    write_event(
        "auth.logout",
        payload={"revoked": revoked},
        ip_address=client_ip(request),
        user_agent=ua(request),
    )
    return {"status": "ok", "revoked": revoked}


@router.post("/logout-all")
def logout_all(
    request: Request,
    response: Response,
    user: dict = Depends(require_user),
) -> dict:
    """Revoca TUTTI i refresh token dell'utente (logout everywhere)."""
    n = revoke_all_for_user(user["id"])
    clear_refresh_cookie(response)
    write_event(
        "auth.logout.all",
        tenant_id=user["tenant_id"],
        user_id=user["id"],
        payload={"revoked_count": n},
        ip_address=client_ip(request),
        user_agent=ua(request),
    )
    return {"status": "ok", "revoked_count": n}


@router.get("/me", response_model=UserMeResponse)
def me(user: dict = Depends(require_user)) -> UserMeResponse:
    # Group membership lookup best-effort: se la query fallisce per
    # qualunque motivo (DB down, mig non applicata) restiamo a [] —
    # la chat non deve crashare per un dato accessorio.
    groups: list[GroupRef] = []
    try:
        from llm_wiki.db.groups import get_user_groups

        groups = [
            GroupRef(id=g["id"], slug=g["slug"], name=g["name"], is_system=g["is_system"])
            for g in get_user_groups(user["id"])
        ]
    except Exception as exc:  # noqa: BLE001 — degrade graceful
        logger.warning("[auth.me] get_user_groups failed: %s", exc)
    return UserMeResponse(
        id=user["id"],
        email=user["email"],
        display_name=user.get("display_name", ""),
        tenant_id=user["tenant_id"],
        role=user["role"],
        is_active=user.get("is_active", True),
        created_at=user.get("created_at"),
        last_login_at=user.get("last_login_at"),
        roles=list(user.get("roles") or []),
        permissions=list(user.get("perms") or []),
        domains=list(user.get("domains") or []),
        groups=groups,
        must_change_password=bool(user.get("password_must_change", False)),
    )


@router.post("/password")
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    response: Response,
    user: dict = Depends(require_user),
) -> dict:
    """Cambio password. Revoca tutti i refresh token dopo il commit
    (logout everywhere) — best practice 2026."""
    full = get_user_by_email_with_credentials(user["email"])
    if not full or not verify_password(full["password_hash"], body.current_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="password attuale non corretta",
        )
    update_password(user["id"], body.new_password)
    revoked = revoke_all_for_user(user["id"])
    clear_refresh_cookie(response)

    write_event(
        "auth.password.change",
        tenant_id=user["tenant_id"],
        user_id=user["id"],
        payload={"revoked_count": revoked},
        ip_address=client_ip(request),
        user_agent=ua(request),
    )
    return {"status": "ok", "revoked_count": revoked}

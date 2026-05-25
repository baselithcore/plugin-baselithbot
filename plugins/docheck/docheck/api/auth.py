"""Auth endpoints: login (password) + me + first-boot bootstrap. OIDC stub-ready."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.jwt import issue_token
from ..core.security import Principal, hash_password, verify_password
from ..core.tenant import current_tenant
from ..db import get_session
from ..db.models import Role, User, UserRole
from ..services import audit
from .deps import current_principal

router = APIRouter()


_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"}


def _is_loopback(request: Request) -> bool:
    """True when caller is on localhost. Anti-LAN-attacker hardening for
    the bootstrap endpoint — wizard must run on the same host as engine
    during first-time setup."""
    host = request.client.host if request.client else None
    if host is None:
        return False
    return host in _LOOPBACK_HOSTS


class LoginRequest(BaseModel):
    # Plain str (not EmailStr) — EmailStr rejects reserved TLDs (.local) used in tests/intranet
    email: str = Field(
        min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    password: str = Field(min_length=1, max_length=512)


class LoginResponse(BaseModel):
    user_id: str
    email: str
    roles: list[str]
    # MVP: token = user_id. Replace with JWT/OIDC in F4.
    token: str


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    req: LoginRequest, db: AsyncSession = Depends(get_session)
) -> LoginResponse:
    user = (
        await db.execute(select(User).where(User.email == req.email))
    ).scalar_one_or_none()

    if user is None or user.disabled_at is not None or not user.pw_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not verify_password(user.pw_hash, req.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    rows = await db.execute(select(UserRole.role_id).where(UserRole.user_id == user.id))
    roles = [r for (r,) in rows.all()]

    await audit.append_audit(
        db,
        action="login",
        user_id=user.id,
        resource=None,
        payload={"email": user.email},
    )

    token = issue_token(
        user_id=user.id,
        email=user.email,
        roles=roles,
        tenant_id=user.tenant_id or current_tenant(),
    )
    return LoginResponse(user_id=user.id, email=user.email, roles=roles, token=token)


@router.get("/auth/me")
async def me(principal: Principal = Depends(current_principal)) -> dict[str, Any]:
    return {
        "user_id": principal.user_id,
        "email": principal.email,
        "roles": sorted(principal.roles),
    }


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=8, max_length=512)


@router.post("/auth/change-password")
async def change_password(
    body: ChangePasswordRequest,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await db.get(User, principal.user_id)
    if user is None or user.disabled_at is not None or not user.pw_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid principal")
    if not verify_password(user.pw_hash, body.current_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password mismatch")
    if body.current_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must differ")

    user.pw_hash = hash_password(body.new_password)
    await audit.append_audit(
        db,
        action="auth.password_changed",
        user_id=user.id,
        resource=None,
        payload={},
    )
    await db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────
# First-boot bootstrap (mirrors wikigen / dbview pattern)
# ──────────────────────────────────────────────────────────────────────────


class BootstrapStatusResponse(BaseModel):
    needs_bootstrap: bool
    users_count: int


class BootstrapRequest(BaseModel):
    email: str = Field(
        min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    password: str = Field(min_length=12, max_length=512)
    display_name: str | None = Field(default=None, max_length=120)


@router.get("/auth/bootstrap/status", response_model=BootstrapStatusResponse)
async def bootstrap_status(
    db: AsyncSession = Depends(get_session),
) -> BootstrapStatusResponse:
    """Public, side-effect-free probe. Returns whether the wizard should
    appear. fail-open: on DB error returns ``needs_bootstrap=false`` so
    a broken probe never hides the legacy login flow."""
    try:
        n = (await db.execute(select(func.count(User.id)))).scalar_one()
    except Exception:
        return BootstrapStatusResponse(needs_bootstrap=False, users_count=0)
    return BootstrapStatusResponse(needs_bootstrap=(int(n) == 0), users_count=int(n))


@router.post("/auth/bootstrap", response_model=LoginResponse)
async def bootstrap_admin(
    body: BootstrapRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """Create the very first admin. Hardening:

    - 403 if any user already exists (idempotent).
    - 403 unless caller is on loopback (anti-LAN-attacker during setup).

    On success: creates user + admin role binding, audit event, opens a
    session in one shot (same shape as POST /auth/login).
    """
    n = (await db.execute(select(func.count(User.id)))).scalar_one()
    if int(n) > 0:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bootstrap already completed")

    if not _is_loopback(request):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Bootstrap is restricted to loopback origins",
        )

    # Ensure built-in admin role exists (mirrors seed_admin.py).
    if await db.get(Role, "admin") is None:
        db.add(Role(id="admin", label="Administrator"))
        await db.flush()

    email = body.email.strip().lower()
    user_id = f"u-{uuid.uuid4().hex[:12]}"
    db.add(
        User(
            id=user_id,
            email=email,
            display_name=(body.display_name or email.split("@")[0]).strip() or "Admin",
            pw_hash=hash_password(body.password),
        )
    )
    db.add(UserRole(user_id=user_id, role_id="admin"))

    await audit.append_audit(
        db,
        action="auth.bootstrap",
        user_id=user_id,
        resource=None,
        payload={"email": email, "source": "web"},
    )
    await db.commit()

    token = issue_token(
        user_id=user_id,
        email=email,
        roles=["admin"],
        tenant_id=current_tenant(),
    )
    return LoginResponse(user_id=user_id, email=email, roles=["admin"], token=token)

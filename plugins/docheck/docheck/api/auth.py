"""Auth endpoints: login (password) + me. OIDC stub-ready."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.jwt import issue_token
from ..core.security import Principal, hash_password, verify_password
from ..core.tenant import current_tenant
from ..db import get_session
from ..db.models import User, UserRole
from ..services import audit
from .deps import current_principal

router = APIRouter()


class LoginRequest(BaseModel):
    # Plain str (not EmailStr) — EmailStr rejects reserved TLDs (.local) used in tests/intranet
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=1, max_length=512)


class LoginResponse(BaseModel):
    user_id: str
    email: str
    roles: list[str]
    # MVP: token = user_id. Replace with JWT/OIDC in F4.
    token: str


@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_session)) -> LoginResponse:
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()

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

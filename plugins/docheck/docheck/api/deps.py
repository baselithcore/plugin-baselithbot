"""Shared FastAPI dependencies (auth + RBAC). JWT-aware."""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.jwt import verify_token
from ..core.security import Principal
from ..core.tenant import set_tenant
from ..db import get_session
from ..db.models import Permission, User, UserRole


async def current_principal(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_session),
) -> Principal:
    """Resolve principal from Bearer JWT first; fallback to X-User-Id (legacy MVP)."""
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if token:
        try:
            claims = await verify_token(token)
        except Exception as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc
        user_id = claims.get("sub")
        tenant_id = claims.get("tid", "default")
        set_tenant(tenant_id)
        roles = frozenset(claims.get("roles") or [])
        email = claims.get("email") or ""
        if not user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing sub claim")
        return Principal(user_id=user_id, email=email, roles=roles)

    # Legacy fallback (header-based, MVP only)
    if not x_user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing credentials")
    user = await db.get(User, x_user_id)
    if user is None or user.disabled_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid principal")
    rows = await db.execute(select(UserRole.role_id).where(UserRole.user_id == user.id))
    roles = frozenset(r for (r,) in rows.all())
    return Principal(user_id=user.id, email=user.email, roles=roles)


def require(resource: str, action: str) -> Callable[..., Awaitable[Principal]]:
    """RBAC enforcer."""

    async def _dep(
        principal: Principal = Depends(current_principal),
        db: AsyncSession = Depends(get_session),
    ) -> Principal:
        rows = await db.execute(
            select(Permission).where(
                Permission.role_id.in_(principal.roles),
                Permission.resource == resource,
                Permission.action == action,
            )
        )
        if rows.first() is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Missing permission: {resource}:{action}",
            )
        return principal

    return _dep

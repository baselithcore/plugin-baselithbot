"""Auth + RBAC primitives. MVP: local user/password (argon2id). OIDC stub ready."""

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..db.models import Permission, User, UserRole

_hasher = PasswordHasher()


def hash_password(pw: str) -> str:
    return _hasher.hash(pw)


def verify_password(pw_hash: str, pw: str) -> bool:
    try:
        _hasher.verify(pw_hash, pw)
        return True
    except VerifyMismatchError:
        return False


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    roles: frozenset[str]


async def _resolve_principal(token: str | None, db: AsyncSession) -> Principal:
    """MVP: token = user_id. Replace with OIDC/JWT validation in F4."""
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing credentials")
    user = await db.get(User, token)
    if user is None or user.disabled_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid principal")
    rows = await db.execute(select(UserRole.role_id).where(UserRole.user_id == user.id))
    roles = frozenset(r for (r,) in rows.all())
    return Principal(user_id=user.id, email=user.email, roles=roles)


def get_current_principal(
    db: AsyncSession = Depends(get_session),
) -> Callable[..., Awaitable[Principal]]:
    async def _dep(x_user_id: str | None = None) -> Principal:
        return await _resolve_principal(x_user_id, db)

    return _dep


async def has_permission(db: AsyncSession, principal: Principal, resource: str, action: str) -> bool:
    rows = await db.execute(
        select(Permission).where(
            Permission.role_id.in_(principal.roles),
            Permission.resource == resource,
            Permission.action == action,
        )
    )
    return rows.first() is not None


def require_permission(
    resource: str, action: str
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator factory enforcing RBAC on FastAPI route handlers."""

    def deco(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(fn)
        async def wrapper(*args: Any, principal: Principal, db: AsyncSession, **kwargs: Any) -> Any:
            if not await has_permission(db, principal, resource, action):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    f"Missing permission: {resource}:{action}",
                )
            return await fn(*args, principal=principal, db=db, **kwargs)

        return wrapper

    return deco


def require_roles(
    allowed: Iterable[str],
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    allowed_set = frozenset(allowed)

    def deco(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(fn)
        async def wrapper(*args: Any, principal: Principal, **kwargs: Any) -> Any:
            if not (principal.roles & allowed_set):
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Role not allowed")
            return await fn(*args, principal=principal, **kwargs)

        return wrapper

    return deco

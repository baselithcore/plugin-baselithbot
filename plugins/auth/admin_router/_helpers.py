"""Shared helpers for admin route handlers."""

from typing import List, Optional, Set

from fastapi import HTTPException, Request, status

from core.auth import AuthRole
from plugins.auth.admin_router._models import UserDetailResponse


def user_to_response(user) -> UserDetailResponse:
    """Convert User model to response."""
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        roles=[r.value for r in user.roles],
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        allowed_tabs=user.allowed_tabs,
        created_at=user.created_at,
        last_login=user.last_login,
        failed_login_attempts=user.failed_login_attempts,
        is_locked=user.is_locked(),
    )


def parse_roles(role_strings: List[str]) -> Set[AuthRole]:
    """Parse role strings to AuthRole set."""
    roles = set()
    for role_str in role_strings:
        try:
            roles.add(AuthRole(role_str.lower()))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role_str}. Valid roles: admin, user, guest",
            )
    return roles if roles else {AuthRole.USER}


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return None

"""
Auth Plugin Admin Router.

Provides admin-only endpoints for user management, sessions, and audit.
"""

from core.observability.logging import get_logger
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field

from core.auth import AuthRole, AuthUser
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import (
    require_admin,
    get_auth_persistence_dep,
    get_audit_logger_dep,
)
from plugins.auth.password import (
    generate_secure_password,
    hash_password,
    validate_password_strength,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.username import validate_username

logger = get_logger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


# =============================================================================
# Request/Response Models
# =============================================================================


class UserDetailResponse(BaseModel):
    """User detail response."""

    id: str
    email: str
    username: Optional[str] = None
    roles: List[str]
    is_active: bool
    mfa_enabled: bool
    allowed_tabs: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    is_locked: bool = False


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: List[UserDetailResponse]
    total: int
    page: int
    limit: int


class CreateUserRequest(BaseModel):
    """Create user request."""

    email: EmailStr
    username: Optional[str] = Field(
        default=None,
        description="Optional username for login (3-50 chars, alphanumeric + ._-)",
    )
    password: Optional[str] = Field(
        default=None,
        description="If not provided, a secure password will be generated",
    )
    roles: List[str] = Field(default=["user"])
    allowed_tabs: Optional[List[str]] = None


class CreateUserResponse(BaseModel):
    """Create user response with optional temporary password."""

    user: UserDetailResponse
    temporary_password: Optional[str] = Field(
        default=None,
        description="Generated password (only shown once)",
    )


class UpdateUserRequest(BaseModel):
    """Update user request (partial)."""

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None
    allowed_tabs: Optional[List[str]] = None


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    new_password: Optional[str] = Field(
        default=None,
        description="If not provided, a secure password will be generated",
    )


class ResetPasswordResponse(BaseModel):
    """Reset password response."""

    message: str
    temporary_password: Optional[str] = None


class SessionInfo(BaseModel):
    """Session information."""

    id: str
    user_id: str
    user_email: str
    created_at: datetime
    expires_at: datetime


class SessionListResponse(BaseModel):
    """Session list response."""

    sessions: List[SessionInfo]
    total: int


class AuditEntryResponse(BaseModel):
    """Audit log entry response."""

    id: str
    action: str
    actor_id: str
    target_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    created_at: datetime


class AuditLogResponse(BaseModel):
    """Audit log response."""

    entries: List[AuditEntryResponse]
    total: int
    page: int
    limit: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# =============================================================================
# Helper Functions
# =============================================================================


def _user_to_response(user) -> UserDetailResponse:
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


def _parse_roles(role_strings: List[str]) -> Set[AuthRole]:
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


def _get_client_ip(request: Request) -> Optional[str]:
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


# =============================================================================
# User Management Endpoints
# =============================================================================


@admin_router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = Query(default=False),
    search: Optional[str] = Query(default=None, max_length=100),
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    List all users with pagination.

    Admin only.
    """
    users, total = persistence.list_users_paginated(
        page=page,
        limit=limit,
        include_inactive=include_inactive,
        search=search,
    )

    return UserListResponse(
        users=[_user_to_response(u) for u in users],
        total=total,
        page=page,
        limit=limit,
    )


@admin_router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Get user details by ID.

    Admin only.
    """
    user = persistence.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _user_to_response(user)


@admin_router.post("/users", response_model=CreateUserResponse, status_code=201)
async def create_user(
    request: Request,
    data: CreateUserRequest,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Create a new user.

    If password is not provided, a secure random password will be generated.
    The temporary password is returned only once and should be communicated
    to the user securely.

    Admin only.
    """

    # Check if email already exists
    existing = persistence.get_user_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Validate username if provided
    if data.username:
        username_errors = validate_username(data.username)
        if username_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(username_errors),
            )
        # Check if username already exists
        existing_username = persistence.get_user_by_username(data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

    # Generate or validate password
    temp_password = None
    if data.password:
        errors = validate_password_strength(data.password)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(errors),
            )
        password = data.password
    else:
        password = generate_secure_password()
        temp_password = password

    # Parse roles
    roles = _parse_roles(data.roles)

    # Create user
    password_hash = hash_password(password)
    user = persistence.create_user(
        email=data.email,
        username=data.username,
        password_hash=password_hash,
        roles=roles,
        allowed_tabs=data.allowed_tabs,
    )

    # Audit log
    audit.log(
        action=AuditAction.USER_CREATED,
        actor_id=admin.user_id,
        target_id=user.id,
        details={
            "email": user.email,
            "username": user.username,
            "roles": [r.value for r in roles],
        },
        ip_address=_get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} created user {user.email}")

    return CreateUserResponse(
        user=_user_to_response(user),
        temporary_password=temp_password,
    )


@admin_router.patch("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    request: Request,
    user_id: str,
    data: UpdateUserRequest,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Update user properties.

    Partial update - only provided fields are modified.
    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    changes: Dict[str, Any] = {}

    # Update email
    if data.email is not None and data.email != user.email:
        existing = persistence.get_user_by_email(data.email)
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use by another user",
            )
        changes["email"] = {"from": user.email, "to": data.email}
        user.email = data.email

    # Update username
    if data.username is not None and data.username != user.username:
        # Validate username format
        username_errors = validate_username(data.username)
        if username_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(username_errors),
            )
        # Check uniqueness
        existing = persistence.get_user_by_username(data.username)
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )
        changes["username"] = {"from": user.username, "to": data.username}
        user.username = data.username

    # Update roles
    if data.roles is not None:
        new_roles = _parse_roles(data.roles)
        old_roles = [r.value for r in user.roles]
        changes["roles"] = {"from": old_roles, "to": data.roles}
        user.roles = new_roles

    # Update active status
    if data.is_active is not None and data.is_active != user.is_active:
        changes["is_active"] = {"from": user.is_active, "to": data.is_active}
        user.is_active = data.is_active
        # Revoke sessions if deactivating
        if not data.is_active:
            persistence.revoke_all_user_tokens(user.id)
            changes["sessions_revoked"] = True

    # Update allowed tabs
    if data.allowed_tabs is not None:
        changes["allowed_tabs"] = {
            "from": user.allowed_tabs,
            "to": data.allowed_tabs,
        }
        user.allowed_tabs = data.allowed_tabs

    # Save changes
    if changes:
        persistence.update_user(user)
        audit.log(
            action=AuditAction.USER_UPDATED,
            actor_id=admin.user_id,
            target_id=user.id,
            details=changes,
            ip_address=_get_client_ip(request),
        )
        logger.info(
            f"Admin {admin.user_id} updated user {user.id}: {list(changes.keys())}"
        )

    return _user_to_response(user)


@admin_router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    request: Request,
    user_id: str,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Deactivate a user (soft delete).

    Sets is_active=False and revokes all sessions.
    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deletion
    if user_id == admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    # Soft delete
    user.is_active = False
    persistence.update_user(user)

    # Revoke all sessions
    revoked = persistence.revoke_all_user_tokens(user_id)

    audit.log(
        action=AuditAction.USER_DELETED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"email": user.email, "sessions_revoked": revoked},
        ip_address=_get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} deactivated user {user.email}")

    return MessageResponse(message=f"User {user.email} has been deactivated")


@admin_router.post(
    "/users/{user_id}/reset-password", response_model=ResetPasswordResponse
)
async def reset_password(
    request: Request,
    user_id: str,
    data: ResetPasswordRequest = ResetPasswordRequest(),
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Reset user password.

    If new_password is not provided, a secure random password will be generated.
    All user sessions are revoked after password reset.

    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate or validate password
    temp_password = None
    if data.new_password:
        errors = validate_password_strength(data.new_password)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(errors),
            )
        password = data.new_password
    else:
        password = generate_secure_password()
        temp_password = password

    # Update password
    user.password_hash = hash_password(password)
    persistence.update_user(user)

    # Revoke all sessions
    revoked = persistence.revoke_all_user_tokens(user_id)

    audit.log(
        action=AuditAction.USER_PASSWORD_RESET,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"sessions_revoked": revoked},
        ip_address=_get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} reset password for user {user.email}")

    return ResetPasswordResponse(
        message="Password has been reset. User must log in again.",
        temporary_password=temp_password,
    )


@admin_router.post("/users/{user_id}/unlock", response_model=MessageResponse)
async def unlock_user(
    request: Request,
    user_id: str,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Unlock a locked user account.

    Clears failed login attempts and lockout timestamp.
    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_locked():
        return MessageResponse(message="User account is not locked")

    persistence.unlock_user(user_id)

    audit.log(
        action=AuditAction.USER_UNLOCKED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"email": user.email},
        ip_address=_get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} unlocked user {user.email}")

    return MessageResponse(message=f"User {user.email} has been unlocked")


@admin_router.post("/users/{user_id}/revoke-sessions", response_model=MessageResponse)
async def revoke_user_sessions(
    request: Request,
    user_id: str,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Revoke all active sessions for a user.

    Forces the user to log in again.
    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    count = persistence.revoke_all_user_tokens(user_id)

    audit.log(
        action=AuditAction.USER_SESSIONS_REVOKED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"email": user.email, "sessions_revoked": count},
        ip_address=_get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} revoked {count} sessions for user {user.email}")

    return MessageResponse(message=f"Revoked {count} active sessions for {user.email}")


@admin_router.delete("/users/{user_id}/mfa", response_model=MessageResponse)
async def disable_user_mfa(
    request: Request,
    user_id: str,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Disable MFA for a user.

    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.mfa_enabled:
        return MessageResponse(message="MFA is not enabled for this user")

    user.mfa_enabled = False
    user.mfa_secret = None
    persistence.update_user(user)

    audit.log(
        action=AuditAction.USER_MFA_DISABLED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"email": user.email},
        ip_address=_get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} disabled MFA for user {user.email}")

    return MessageResponse(message=f"MFA disabled for {user.email}")


# =============================================================================
# Session Management Endpoints
# =============================================================================


@admin_router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = Query(default=None),
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    List active sessions.

    Optionally filter by user_id.
    Admin only.
    """
    sessions = persistence.get_active_sessions(user_id=user_id)

    session_list = []
    for s in sessions:
        session_list.append(
            SessionInfo(
                id=s.id,
                user_id=s.user_id,
                user_email=getattr(s, "user_email", ""),
                created_at=s.created_at,
                expires_at=s.expires_at,
            )
        )

    return SessionListResponse(
        sessions=session_list,
        total=len(session_list),
    )


# =============================================================================
# Audit Log Endpoints
# =============================================================================


@admin_router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    action: Optional[str] = Query(default=None),
    actor_id: Optional[str] = Query(default=None),
    target_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    admin: AuthUser = Depends(require_admin()),
    audit=Depends(get_audit_logger_dep),
):
    """
    Get audit log entries.

    Admin only.
    """
    entries, total = audit.get_entries(
        action=action,
        actor_id=actor_id,
        target_id=target_id,
        page=page,
        limit=limit,
    )

    return AuditLogResponse(
        entries=[
            AuditEntryResponse(
                id=e.id,
                action=e.action,
                actor_id=e.actor_id,
                target_id=e.target_id,
                details=e.details,
                ip_address=e.ip_address,
                created_at=e.created_at,
            )
            for e in entries
        ],
        total=total,
        page=page,
        limit=limit,
    )


# =============================================================================
# Plugin Tabs
# =============================================================================


class PluginTab(BaseModel):
    id: str
    label: str
    plugin: str


@admin_router.get("/plugins/tabs", response_model=List[PluginTab])
async def list_plugin_tabs(admin: AuthUser = Depends(require_admin())):
    """
    List available UI tabs from all plugins.

    Admin only.
    """
    from core.plugins.api import get_controller

    tabs = []
    try:
        controller = get_controller()
        registry = controller.registry

        # Use existing list_plugins method to get metadata
        plugins_meta = registry.list_plugins()

        for meta in plugins_meta:
            plugin_name = meta["name"]
            # Get the actual plugin instance from the registry
            plugin = registry.get(plugin_name)

            if plugin and hasattr(plugin, "get_ui_tabs"):
                # Call get_ui_tabs if it exists (it should, from interface)
                plugin_tabs = plugin.get_ui_tabs()
                for tab in plugin_tabs:
                    tabs.append(
                        PluginTab(id=tab["id"], label=tab["label"], plugin=plugin_name)
                    )

    except Exception as e:
        logger.error(f"Failed to list plugin tabs: {e}")
        # Return empty list on error to not block UI

    return tabs

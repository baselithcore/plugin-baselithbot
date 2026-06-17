"""Admin user-management endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._helpers import (
    get_client_ip,
    parse_roles,
    user_to_response,
)
from plugins.auth.admin_router._models import (
    CreateUserRequest,
    CreateUserResponse,
    MessageResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UpdateUserRequest,
    UserDetailResponse,
    UserListResponse,
)
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_admin,
)
from plugins.auth.password import (
    generate_secure_password,
    hash_password,
    validate_password_strength,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.username import validate_username

logger = get_logger(__name__)

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
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
        users=[user_to_response(u) for u in users],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
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

    return user_to_response(user)


@router.post("/users", response_model=CreateUserResponse, status_code=201)
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
    roles = parse_roles(data.roles)

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
        ip_address=get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} created user {user.email}")

    return CreateUserResponse(
        user=user_to_response(user),
        temporary_password=temp_password,
    )


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
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

    # Last-admin protection: refuse to strip admin or deactivate the only
    # remaining active admin (prevents locking everyone out of the console).
    was_active_admin = user.is_active and "admin" in [r.value for r in user.roles]
    if was_active_admin:
        losing_admin = (data.roles is not None and "admin" not in data.roles) or (
            data.is_active is False
        )
        if losing_admin and persistence.count_active_admins() <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last active admin",
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
        new_roles = parse_roles(data.roles)
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
            ip_address=get_client_ip(request),
        )
        logger.info(
            f"Admin {admin.user_id} updated user {user.id}: {list(changes.keys())}"
        )

    return user_to_response(user)


@router.delete("/users/{user_id}", response_model=MessageResponse)
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

    # Last-admin protection: refuse to deactivate the only remaining admin.
    if (
        user.is_active
        and "admin" in [r.value for r in user.roles]
        and persistence.count_active_admins() <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot deactivate the last active admin",
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
        ip_address=get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} deactivated user {user.email}")

    return MessageResponse(message=f"User {user.email} has been deactivated")


@router.post("/users/{user_id}/reset-password", response_model=ResetPasswordResponse)
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
        ip_address=get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} reset password for user {user.email}")

    return ResetPasswordResponse(
        message="Password has been reset. User must log in again.",
        temporary_password=temp_password,
    )

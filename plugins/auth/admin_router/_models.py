"""Request/response models for the admin router."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


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


class InviteUserRequest(BaseModel):
    """Invite a user by email (they set their own password)."""

    email: EmailStr
    roles: List[str] = Field(default=["user"])


class InvitationResponse(BaseModel):
    """A pending or accepted invitation."""

    id: str
    email: str
    roles: List[str]
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SetStatusRequest(BaseModel):
    """Change a user's lifecycle status."""

    status: str = Field(..., pattern="^(active|suspended|deactivated)$")


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class PluginTab(BaseModel):
    """A UI tab exposed by a plugin."""

    id: str
    label: str
    plugin: str

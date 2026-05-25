"""
Auth Plugin Data Models.

User and token dataclasses for the authentication system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from core.auth.types import AuthRole


@dataclass
class User:
    """User entity for authentication."""

    id: str  # UUID
    email: str  # Unique email (login identifier)
    password_hash: str  # Argon2 hash
    username: Optional[str] = None  # Optional username (alternative login identifier)
    roles: Set[AuthRole] = field(default_factory=lambda: {AuthRole.USER})
    mfa_secret: Optional[str] = None  # TOTP secret (encrypted at rest)
    mfa_enabled: bool = False
    is_active: bool = True
    allowed_tabs: Optional[List[str]] = None  # For GUEST: specific tabs allowed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def has_role(self, role: AuthRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return AuthRole.ADMIN in self.roles

    def is_guest(self) -> bool:
        """Check if user is guest."""
        return AuthRole.GUEST in self.roles

    def can_access_tab(self, tab_id: str) -> bool:
        """Check if user can access a specific tab."""
        # Non-guests can access all tabs
        if not self.is_guest():
            return True
        # Guests: if allowed_tabs is None, allow all (read-only)
        if self.allowed_tabs is None:
            return True
        return tab_id in self.allowed_tabs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "roles": [r.value for r in self.roles],
            "mfa_enabled": self.mfa_enabled,
            "is_active": self.is_active,
            "allowed_tabs": self.allowed_tabs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


@dataclass
class RefreshToken:
    """Refresh token entity for session management."""

    id: str  # UUID
    user_id: str  # Foreign key to User
    token_hash: str  # SHA256 hash of the token
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        if self.revoked_at is not None:
            return False
        return datetime.now(timezone.utc) < self.expires_at


@dataclass
class MFABackupCode:
    """MFA backup code for recovery."""

    id: str  # UUID
    user_id: str  # Foreign key to User
    code_hash: str  # SHA256 hash of the code
    used_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_used(self) -> bool:
        """Check if backup code has been used."""
        return self.used_at is not None


@dataclass
class LoginRequest:
    """Login request payload."""

    identifier: str  # Can be email or username
    password: str


@dataclass
class MFAVerifyRequest:
    """MFA verification request payload."""

    temp_token: str
    code: str


@dataclass
class TokenResponse:
    """Token response payload."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # seconds


@dataclass
class MFARequiredResponse:
    """Response when MFA is required."""

    mfa_required: bool = True
    temp_token: str = ""


@dataclass
class UserInfoResponse:
    """Current user info response."""

    id: str
    email: str
    roles: List[str]
    mfa_enabled: bool
    allowed_tabs: Optional[List[str]] = None

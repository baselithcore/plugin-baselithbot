"""Request/response models for the auth router."""

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request payload."""

    identifier: str = Field(..., description="Email or username")
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """Registration request payload."""

    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8)
    username: Optional[str] = Field(None, description="Optional username")


class MFAVerifyRequest(BaseModel):
    """MFA verification request."""

    temp_token: str
    code: str = Field(..., min_length=6, max_length=8)


class TokenResponse(BaseModel):
    """Successful login response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MFARequiredResponse(BaseModel):
    """Response when MFA verification is needed."""

    mfa_required: bool = True
    temp_token: str


class MFAEnrollmentRequiredResponse(BaseModel):
    """Response when policy mandates MFA but the user has not enrolled yet.

    Carries a freshly-generated (not-yet-active) TOTP secret + QR + backup codes
    plus a short-lived ``enroll_token``; the client completes enrollment via
    ``/mfa/enroll-verify``. No session is issued until that succeeds.
    """

    mfa_enrollment_required: bool = True
    enroll_token: str
    secret: str
    provisioning_uri: str
    qr_code: Optional[str] = None  # Base64 PNG data URI
    backup_codes: list[str]


class EnrollVerifyRequest(BaseModel):
    """Complete forced MFA enrollment: verify the first TOTP code."""

    enroll_token: str
    code: str = Field(..., min_length=6, max_length=8)


class ImpersonatorInfo(BaseModel):
    """The real administrator behind an active impersonation session."""

    id: str
    email: Optional[str] = None
    since: Optional[int] = None  # epoch seconds the impersonation started


class UserInfoResponse(BaseModel):
    """Current user info response."""

    id: str
    email: str
    username: Optional[str] = None
    roles: list[str]
    mfa_enabled: bool
    allowed_tabs: Optional[list[str]] = None
    # Impersonation context (present only when viewing as another user).
    is_impersonating: bool = False
    impersonator: Optional[ImpersonatorInfo] = None


class ImpersonateRequest(BaseModel):
    """Optional justification when an admin starts impersonating a user."""

    reason: Optional[str] = Field(None, max_length=280)


class ImpersonatedUser(BaseModel):
    """Summary of the user now being impersonated."""

    id: str
    email: str
    username: Optional[str] = None
    roles: list[str]


class ImpersonateResponse(BaseModel):
    """Response when impersonation starts: a short-lived access token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    impersonated: ImpersonatedUser


class MFASetupResponse(BaseModel):
    """MFA setup response with provisioning info."""

    secret: str
    provisioning_uri: str
    qr_code: Optional[str] = None  # Base64 encoded PNG
    backup_codes: list[str]


class ForgotPasswordRequest(BaseModel):
    """Request a password-reset email."""

    identifier: str = Field(..., description="Email or username")


class ResetPasswordRequest(BaseModel):
    """Complete a password reset with a one-time token."""

    token: str
    new_password: str = Field(..., min_length=8)


class VerifyEmailRequest(BaseModel):
    """Confirm an email address with a one-time token."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Request a fresh email-verification link."""

    email: str


class AcceptInviteRequest(BaseModel):
    """Accept an invitation and create the account."""

    token: str
    password: str = Field(..., min_length=8)
    username: Optional[str] = None
    full_name: Optional[str] = None


class InviteInfoResponse(BaseModel):
    """Public details of a pending invitation (for the accept screen)."""

    email: str
    roles: list[str]


class AccountResponse(BaseModel):
    """Rich self-service account summary for the My Account surface."""

    id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    roles: list[str]
    mfa_enabled: bool
    email_verified: bool
    status: str
    passkey_count: int
    last_login: Optional[str] = None
    last_login_ip: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    """Self-service profile update."""

    full_name: Optional[str] = Field(None, max_length=160)
    username: Optional[str] = Field(None, max_length=50)


class ChangePasswordRequest(BaseModel):
    """Self-service password change (requires the current password)."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class SelfMfaDisableRequest(BaseModel):
    """Self-service MFA disable, confirmed with a current TOTP/backup code."""

    code: str = Field(..., min_length=6, max_length=10)


class SessionInfo(BaseModel):
    """A single active session/device."""

    id: str
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    current: bool = False


class ActivityEntry(BaseModel):
    """A login / security activity record."""

    event: str
    method: str
    success: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    risk_score: int = 0
    created_at: Optional[str] = None


class ApiKeyCreateRequest(BaseModel):
    """Request to mint a personal access token."""

    name: str = Field(..., min_length=1, max_length=120)
    scopes: Optional[list[str]] = None
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650)


class ApiKeyInfo(BaseModel):
    """API key metadata (never includes the secret)."""

    id: str
    name: str
    prefix: str
    scopes: list[str] = []
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    revoked_at: Optional[str] = None
    created_at: Optional[str] = None


class ApiKeyCreated(BaseModel):
    """Response to key creation: the raw key is shown exactly once."""

    key: str
    info: ApiKeyInfo


class SsoProviderUpsert(BaseModel):
    """Create/update an SSO identity provider (admin)."""

    name: str = Field(..., min_length=1, max_length=120)
    protocol: str = Field(..., pattern="^(oidc|saml)$")
    enabled: bool = True
    auto_provision: bool = True
    config: dict = Field(default_factory=dict)
    secret: Optional[str] = Field(
        None, description="Client secret (OIDC) / SP private key (SAML)"
    )
    default_roles: list[str] = Field(default_factory=lambda: ["user"])


class SsoProviderOut(BaseModel):
    """SSO provider as returned to the admin UI (never exposes the secret)."""

    id: str
    slug: str
    name: str
    protocol: str
    enabled: bool
    auto_provision: bool
    config: dict = {}
    default_roles: list[str] = []
    has_secret: bool = False


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class CSRFTokenResponse(BaseModel):
    """CSRF token response."""

    csrf_token: str

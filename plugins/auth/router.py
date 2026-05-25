"""
Auth Plugin FastAPI Router.

Provides authentication endpoints: login, logout, refresh, MFA.
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from plugins.auth.rate_limiting import RateLimit as RateLimiter
from pydantic import BaseModel, Field

from core.auth import AuthRole, AuthUser, AuthManager
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    get_current_active_user,
    require_admin,
    get_auth_config_dep,
    get_auth_persistence_dep,
    get_auth_manager_dep,
)
from plugins.auth.mfa import (
    generate_backup_codes,
    generate_secret,
    get_provisioning_uri,
    get_qr_code_base64,
    verify_totp,
)
from plugins.auth.password import verify_password
from plugins.auth.persistence import AuthPersistence
from plugins.auth.security import (
    mfa_token_store,
    sanitize_log_input,
    generate_secure_token,
    add_security_headers,
)
from plugins.auth.csrf import get_csrf_protection

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Request/Response Models
# =============================================================================


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


class UserInfoResponse(BaseModel):
    """Current user info response."""

    id: str
    email: str
    username: Optional[str] = None
    roles: list[str]
    mfa_enabled: bool
    allowed_tabs: Optional[list[str]] = None


class MFASetupResponse(BaseModel):
    """MFA setup response with provisioning info."""

    secret: str
    provisioning_uri: str
    qr_code: Optional[str] = None  # Base64 encoded PNG
    backup_codes: list[str]


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class CSRFTokenResponse(BaseModel):
    """CSRF token response."""

    csrf_token: str


# =============================================================================
# CSRF Token Endpoint
# =============================================================================


@router.get("/csrf-token", response_model=CSRFTokenResponse)
async def get_csrf_token(response: Response):
    """
    Get CSRF token for state-changing operations.

    The token is set as a cookie and also returned in response.
    Frontend should include this token in X-CSRF-Token header for POST/PUT/DELETE requests.
    """
    csrf = get_csrf_protection()
    token = csrf.set_csrf_cookie(response)
    return CSRFTokenResponse(csrf_token=token)


# =============================================================================
# Login / Logout Endpoints
# =============================================================================


@router.post(
    "/login",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    response_model=TokenResponse | MFARequiredResponse,
    responses={
        401: {"description": "Invalid credentials"},
        423: {"description": "Account locked"},
        429: {"description": "Too many requests"},
    },
)
async def login(
    login_request: LoginRequest,
    request: Request,
    response: Response,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
):
    """
    Authenticate with email OR username and password.

    If MFA is enabled for the user, returns a temporary token
    that must be used with /mfa/verify endpoint.
    """

    # Sanitize identifier for logging
    safe_identifier = sanitize_log_input(login_request.identifier)
    logger.info(f"Login attempt for: {safe_identifier}")

    try:
        # Find user by identifier (username OR email) - use constant-time behavior to prevent user enumeration
        user = persistence.get_user_by_identifier(login_request.identifier)
        if not user:
            # Perform dummy password verification to prevent timing attacks
            verify_password(
                "dummy_password",
                "$argon2id$v=19$m=65536,t=3,p=4$MOkQilQKYf3eBjMOaF+L5g$Wce9XPOJlvwf+WxJeAZvgOlfJ0TUWU0SRuGztiiC0E0",
            )
            logger.warning(f"Login failed: User not found for {safe_identifier}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        logger.debug(f"User found: {user.id}")

        # Check if account is locked
        if user.is_locked():
            logger.warning(f"Login attempt for locked account: {safe_identifier}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked. Try again later.",
            )

        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled",
            )

        # Verify password
        if not verify_password(login_request.password, user.password_hash):
            attempts = persistence.record_login_failure(user.id)
            remaining = config.max_login_attempts - attempts
            logger.warning(
                f"Failed login for {safe_identifier}. Remaining attempts: {remaining}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        logger.debug("Password verification successful")

        # Check if MFA is required
        if user.mfa_enabled and user.mfa_secret:
            # Generate temporary token for MFA flow using secure store
            temp_token = generate_secure_token("mfa")
            mfa_token_store.store(
                temp_token,
                {"user_id": user.id},
                ttl_seconds=300,  # 5 minutes
            )
            logger.info(f"MFA challenge required for user {user.id}")
            return MFARequiredResponse(temp_token=temp_token)

        # No MFA required - issue tokens
        logger.info(f"Login successful (no MFA) for user {user.id}")
        add_security_headers(response)

        return await _issue_tokens(
            user.id, user.roles, response, persistence, auth_manager, config
        )

    except HTTPException:
        # Re-raise HTTP exceptions to let FastAPI handle them
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during login for {safe_identifier}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )


@router.post(
    "/register",
    dependencies=[Depends(RateLimiter(times=3, seconds=60))],
    response_model=UserInfoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    register_request: RegisterRequest,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    config: AuthConfig = Depends(get_auth_config_dep),
):
    """
    Public registration endpoint.

    Creates a new user with 'user' role.
    """
    # Check if registration is enabled in config (if such flag exists, otherwise default to enabled)
    # For now, following QUICK_START.md which expects this to work.

    # Check if email already exists
    if persistence.get_user_by_email(register_request.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Validate password strength
    from plugins.auth.password import validate_password_strength_async, hash_password

    errors = await validate_password_strength_async(
        register_request.password, check_breaches=config.check_pwned_passwords
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors),
        )

    # Hash password
    password_hash = hash_password(register_request.password)

    # Create user
    try:
        user = persistence.create_user(
            email=register_request.email,
            username=register_request.username,
            password_hash=password_hash,
            roles={AuthRole.USER},
        )
        logger.info(f"New user registered: {user.email}")
        return UserInfoResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            roles=[r.value for r in user.roles],
            mfa_enabled=user.mfa_enabled,
            allowed_tabs=user.allowed_tabs,
        )
    except Exception as e:
        logger.error(f"Registration failed for {register_request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during registration",
        )


@router.post(
    "/mfa/verify",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
    response_model=TokenResponse,
    responses={429: {"description": "Too many requests"}},
)
async def verify_mfa(
    mfa_request: MFAVerifyRequest,
    request: Request,
    response: Response,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
):
    """
    Complete MFA verification after initial login.

    Accepts either a TOTP code or a backup code.
    """

    # Validate temp token using secure store
    token_data = mfa_token_store.get(mfa_request.temp_token)
    if not token_data:
        logger.warning("MFA verify failed: Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired temporary token",
        )

    user = persistence.get_user_by_id(token_data["user_id"])
    if not user or not user.mfa_secret:
        mfa_token_store.delete(mfa_request.temp_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user or MFA not configured",
        )

    # Try TOTP verification first
    code = mfa_request.code.replace("-", "").replace(" ", "")
    if len(code) == 6 and verify_totp(user.mfa_secret, code):
        # Valid TOTP code
        mfa_token_store.delete(mfa_request.temp_token)
        logger.info(f"MFA TOTP verification successful for user {user.id}")
        add_security_headers(response)
        config = await get_auth_config_dep()
        return await _issue_tokens(
            user.id, user.roles, response, persistence, auth_manager, config
        )

    # Try backup code using secure comparison
    if _verify_backup_code(mfa_request.code, user.id, persistence):
        # Valid backup code
        mfa_token_store.delete(mfa_request.temp_token)
        remaining = persistence.get_unused_backup_codes_count(user.id)
        logger.info(f"User used backup code. {remaining} remaining.")
        logger.info(f"MFA backup code verification successful for user {user.id}")
        add_security_headers(response)
        config = await get_auth_config_dep()
        return await _issue_tokens(
            user.id, user.roles, response, persistence, auth_manager, config
        )

    logger.warning(f"MFA invalid code for user {user.id}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid MFA code",
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Logout and invalidate refresh token.
    """
    try:
        # Get token from cookie using configured name
        refresh_token = request.cookies.get(config.cookie_name)

        if refresh_token:
            try:
                persistence.revoke_refresh_token(refresh_token)
                logger.info("Refresh token revoked (logout)")
            except Exception as e:
                logger.error(f"Error revoking refresh token during logout: {e}")
                # Continue to clear cookie even if DB fails

        # Clear cookie - ensure parameters match set_cookie for reliable deletion
        response.delete_cookie(
            key=config.cookie_name,
            path="/api",
            secure=config.cookie_secure,
            httponly=config.cookie_httponly,
            samesite=config.cookie_samesite,
        )

        return MessageResponse(message="Logged out successfully")
    except Exception as e:
        logger.error(f"Unexpected error during logout: {e}", exc_info=True)
        # Even on error, try to tell client to clear cookie
        try:
            response.delete_cookie(key="refresh_token", path="/api")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing logout",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
):
    """
    Refresh access token using refresh token cookie.
    """
    # Get token from cookie using configured name instead of static alias
    refresh_token = request.cookies.get(config.cookie_name)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    user_id = persistence.validate_refresh_token(refresh_token)
    if not user_id:
        logger.warning("Token refresh failed: Invalid/expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = persistence.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Issue new tokens (rotate refresh token for security)
    logger.info(f"Refreshed tokens for user {user.id}")
    config = await get_auth_config_dep()
    return await _issue_tokens(
        user.id, user.roles, response, persistence, auth_manager, config
    )


@router.post("/revoke", response_model=MessageResponse)
async def revoke_token(
    request: Request,
    token: Optional[str] = None,
    token_type_hint: Optional[str] = None,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    config: AuthConfig = Depends(get_auth_config_dep),
):
    """
    Revoke a token (RFC 7009 compliant).

    Accepts token in request body or from cookie.
    Token type hint can be 'refresh_token' or 'access_token'.

    This endpoint allows users to revoke their own tokens.
    Admin users can revoke tokens for any user.
    """

    # Get token from body or cookie
    if not token:
        token = request.cookies.get(config.cookie_name)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No token provided",
        )

    # Validate token belongs to requesting user (unless admin)
    token_user_id = persistence.validate_refresh_token(token)

    if token_user_id:
        # Check authorization
        if token_user_id != user.user_id and not user.has_role(AuthRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot revoke another user's token",
            )

        # Revoke the token
        revoked = persistence.revoke_refresh_token(token)
        if revoked:
            logger.info(f"Token revoked for user {token_user_id} by {user.user_id}")
            return MessageResponse(message="Token revoked successfully")

    # Token not found or already revoked - return success anyway (RFC 7009)
    logger.debug(f"Revoke request for invalid/expired token by {user.user_id}")
    return MessageResponse(message="Token revoked successfully")


# =============================================================================
# User Info
# =============================================================================


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Get current authenticated user info.
    """
    db_user = persistence.get_user_by_id(user.user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserInfoResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        roles=[r.value for r in db_user.roles],
        mfa_enabled=db_user.mfa_enabled,
        allowed_tabs=db_user.allowed_tabs,
    )


# =============================================================================
# MFA Management
# =============================================================================


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Initialize MFA setup for current user.

    Returns secret, QR code, and backup codes.
    User must complete setup by verifying a code.
    """
    db_user = persistence.get_user_by_id(user.user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate new secret
    secret = generate_secret()
    provisioning_uri = get_provisioning_uri(db_user.email, secret)

    # Generate QR code
    try:
        qr_code = get_qr_code_base64(db_user.email, secret)
    except ImportError:
        qr_code = None

    # Generate backup codes
    plain_codes, hashed_codes = generate_backup_codes(10)

    # Store secret (not yet enabled) and backup codes
    db_user.mfa_secret = secret
    persistence.update_user(db_user)
    persistence.store_backup_codes(db_user.id, hashed_codes)

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_code=qr_code,
        backup_codes=plain_codes,
    )


@router.post("/mfa/enable", response_model=MessageResponse)
async def enable_mfa(
    code: str,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Enable MFA after verifying setup code.
    """
    db_user = persistence.get_user_by_id(user.user_id)

    if not db_user or not db_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not set up. Call /mfa/setup first.",
        )

    if not verify_totp(db_user.mfa_secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    db_user.mfa_enabled = True
    persistence.update_user(db_user)

    logger.info(f"MFA enabled for user {db_user.email}")
    return MessageResponse(message="MFA enabled successfully")


@router.post("/mfa/disable", response_model=MessageResponse)
async def disable_mfa(
    user: AuthUser = Depends(require_admin()),
    target_user_id: Optional[str] = None,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Disable MFA for a user (admin only).

    If target_user_id is not provided, disables for current user.
    """
    user_id = target_user_id or user.user_id
    db_user = persistence.get_user_by_id(user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db_user.mfa_enabled = False
    db_user.mfa_secret = None
    persistence.update_user(db_user)

    logger.info(f"MFA disabled for user {db_user.email} by admin {user.user_id}")
    return MessageResponse(message="MFA disabled successfully")


# =============================================================================
# Helper Functions
# =============================================================================


def _verify_backup_code(code: str, user_id: str, persistence) -> bool:
    """
    Verify backup code using constant-time comparison.

    Iterates through all unused codes to prevent timing attacks.
    """
    import hashlib

    # Normalize code
    normalized = code.replace("-", "").replace(" ", "").upper()
    if len(normalized) == 8:
        formatted = f"{normalized[:4]}-{normalized[4:]}"
    else:
        formatted = code.upper()

    code_hash = hashlib.sha256(formatted.encode()).hexdigest()

    # Use persistence method which does the comparison
    return persistence.use_backup_code(user_id, code_hash)


async def _issue_tokens(
    user_id: str,
    roles: set,
    response: Response,
    persistence: AuthPersistence,
    auth_manager: AuthManager,
    config: AuthConfig,
) -> TokenResponse:
    """Issue access and refresh tokens."""

    # Record successful login
    persistence.record_login_success(user_id)

    # SECURITY: Revoke all previous tokens to prevent session fixation
    # This ensures old sessions cannot be reused after successful login
    revoked_count = persistence.revoke_all_user_tokens(user_id)
    if revoked_count > 0:
        logger.info(f"Revoked {revoked_count} previous tokens for user {user_id}")

    # Create access token
    access_token = await auth_manager.create_token(user_id, roles)

    # Create refresh token using secure generation
    refresh_token = generate_secure_token(length=32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=config.refresh_lifetime)
    persistence.store_refresh_token(user_id, refresh_token, expires_at)

    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key=config.cookie_name,
        value=refresh_token,
        httponly=config.cookie_httponly,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        max_age=config.refresh_lifetime,
        path="/api",  # Allow cookie for all API endpoints
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=config.session_lifetime,
    )

"""Login, registration, session token, and MFA-challenge endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from core.auth import AuthManager, AuthRole, AuthUser
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.csrf import get_csrf_protection
from plugins.auth.dependencies import (
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
    get_current_active_user,
)
from plugins.auth.password import verify_password
from plugins.auth.persistence import AuthPersistence
from plugins.auth.rate_limiting import RateLimit as RateLimiter
from plugins.auth.router._helpers import (
    client_ip,
    issue_tokens,
    log_login_failure,
    log_login_success,
)
from plugins.auth.router._mfa_enroll_routes import build_mfa_enrollment_challenge
from plugins.auth.router._models import (
    CSRFTokenResponse,
    LoginRequest,
    MessageResponse,
    MFAEnrollmentRequiredResponse,
    MFARequiredResponse,
    RegisterRequest,
    TokenResponse,
    UserInfoResponse,
)
from plugins.auth.security import (
    add_security_headers,
    generate_secure_token,
    mfa_token_store,
    sanitize_log_input,
)

logger = get_logger(__name__)

router = APIRouter()


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


@router.post(
    "/login",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    response_model=TokenResponse | MFARequiredResponse | MFAEnrollmentRequiredResponse,
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
            log_login_failure(request, persistence, None, "user_not_found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        logger.debug(f"User found: {user.id}")

        # Check if account is locked
        if user.is_locked():
            logger.warning(f"Login attempt for locked account: {safe_identifier}")
            log_login_failure(request, persistence, user.id, "account_locked")
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
            log_login_failure(request, persistence, user.id, "bad_password")
            # Record the lockout in the NIS2 incident-handling trail when this
            # failure crossed the lockout threshold. Opt-in + best-effort.
            if attempts >= config.max_login_attempts:
                from plugins.auth.security_incidents import report_account_lockout

                await report_account_lockout(
                    user.id, attempts, source_ip=client_ip(request)
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        logger.debug("Password verification successful")

        # Transparent hash upgrade: if the stored hash predates the current
        # Argon2 parameters, re-hash the just-verified password and persist it.
        from plugins.auth.password import hash_password, needs_rehash

        if needs_rehash(user.password_hash):
            try:
                persistence.update_password_hash(
                    user.id, hash_password(login_request.password)
                )
                logger.info(f"Upgraded password hash on login for user {user.id}")
            except Exception as exc:  # noqa: BLE001 - never block login on rehash
                logger.warning(f"Password rehash-on-login skipped: {exc}")

        # Enforce email verification when the deployment requires it: an
        # unverified (e.g. self-registered) account must not obtain a session.
        if config.email_verification_required and not user.email_verified:
            logger.warning(f"Login blocked: unverified email for {safe_identifier}")
            log_login_failure(request, persistence, user.id, "email_unverified")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email address not verified. Check your inbox for the link.",
            )

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
            persistence.record_login_event(user.id, "mfa_challenge", method="mfa")
            return MFARequiredResponse(temp_token=temp_token)

        # Policy may mandate MFA for this user (global / group / per-user) even
        # though they have not enrolled. Force enrollment before any session is
        # issued — no tokens until the second factor is proven.
        if persistence.is_mfa_required(user.id):
            logger.info(f"MFA enrollment required by policy for user {user.id}")
            persistence.record_login_event(
                user.id, "mfa_enrollment_required", method="mfa"
            )
            return build_mfa_enrollment_challenge(user)

        # No MFA required - assess risk, record success, issue tokens
        logger.info(f"Login successful (no MFA) for user {user.id}")
        log_login_success(request, persistence, user.id, "password")
        add_security_headers(response)

        return await issue_tokens(
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
    # Check if email already exists
    if persistence.get_user_by_email(register_request.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Validate password strength
    from plugins.auth.password import hash_password, validate_password_strength_async

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
    return await issue_tokens(
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

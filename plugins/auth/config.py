"""
Auth Plugin Configuration.

Pydantic Settings for authentication parameters.
"""

from core.observability.logging import get_logger
from typing import Optional, List

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from core.config.env import PROJECT_ENV_FILE

logger = get_logger(__name__)


class AuthConfig(BaseSettings):
    """Authentication configuration."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Core ===
    auth_required: bool = Field(default=False, alias="AUTH_REQUIRED")
    secret_key: Optional[str] = Field(default=None, alias="SECRET_KEY")

    # === Bootstrap admin (seeded on startup if no admin exists yet) ===
    bootstrap_admin_email: Optional[str] = Field(
        default=None,
        alias="AUTH_BOOTSTRAP_ADMIN_EMAIL",
        description="Email of the admin user auto-created when no admin exists",
    )
    bootstrap_admin_password: Optional[SecretStr] = Field(
        default=None,
        alias="AUTH_BOOTSTRAP_ADMIN_PASSWORD",
        description="Password for the bootstrap admin user",
    )
    bootstrap_admin_username: Optional[str] = Field(
        default="admin",
        alias="AUTH_BOOTSTRAP_ADMIN_USERNAME",
        description="Username for the bootstrap admin user",
    )

    # === Token Lifetimes ===
    session_lifetime: int = Field(
        default=900,  # 15 minutes
        alias="AUTH_SESSION_LIFETIME",
        ge=60,
        description="Access token lifetime in seconds",
    )
    refresh_lifetime: int = Field(
        default=604800,  # 7 days
        alias="AUTH_REFRESH_LIFETIME",
        ge=3600,
        description="Refresh token lifetime in seconds",
    )

    # === MFA ===
    mfa_enabled: bool = Field(
        default=True,
        alias="AUTH_MFA_ENABLED",
        description="Enable MFA requirement for users",
    )
    mfa_issuer: str = Field(
        default="Baselith-Core",
        alias="AUTH_MFA_ISSUER",
        description="Issuer name displayed in authenticator apps",
    )

    # === Password Policy ===
    password_min_length: int = Field(
        default=12,
        alias="AUTH_PASSWORD_MIN_LENGTH",
        ge=8,
        description="Minimum password length",
    )
    check_pwned_passwords: bool = Field(
        default=True,
        alias="AUTH_CHECK_PWNED_PASSWORDS",
        description="Check passwords against HaveIBeenPwned breach database",
    )

    # === Security ===
    max_login_attempts: int = Field(
        default=5,
        alias="AUTH_MAX_LOGIN_ATTEMPTS",
        ge=1,
        description="Max failed attempts before lockout",
    )
    lockout_duration_minutes: int = Field(
        default=15,
        alias="AUTH_LOCKOUT_DURATION_MINUTES",
        ge=1,
        description="Account lockout duration in minutes",
    )

    # === Cookies ===
    cookie_secure: bool = Field(
        default=True,
        alias="AUTH_COOKIE_SECURE",
        description="Set Secure flag on cookies (requires HTTPS)",
    )
    cookie_samesite: str = Field(
        default="Lax",
        alias="AUTH_COOKIE_SAMESITE",
        description="SameSite policy for cookies",
    )
    cookie_httponly: bool = Field(
        default=True,
        alias="AUTH_COOKIE_HTTPONLY",
        description="Set HttpOnly flag on cookies",
    )
    cookie_name: str = Field(
        default="refresh_token",
        alias="AUTH_COOKIE_NAME",
        description="Name of the refresh token cookie",
    )

    # === Public Paths ===
    public_paths: List[str] = Field(
        default=[
            "/api/auth/login",
            "/api/auth/logout",
            "/api/auth/refresh",
            "/api/auth/mfa/verify",
            "/api/auth/forgot-password",
            "/api/auth/reset-password",
            "/api/auth/verify-email",
            "/api/auth/resend-verification",
            "/api/auth/invitations/accept",
            "/api/auth/webauthn/authenticate",
            "/api/auth/sso",
            "/health",
            "/docs",
            "/openapi.json",
        ],
        alias="AUTH_PUBLIC_PATHS",
        description="Paths that don't require authentication",
    )

    # === Account Recovery ===
    account_recovery_enabled: bool = Field(
        default=False,
        alias="AUTH_ACCOUNT_RECOVERY_ENABLED",
        description="Enable account recovery (requires SMTP configuration)",
    )

    # === WebAuthn ===
    webauthn_enabled: bool = Field(
        default=False,
        alias="AUTH_WEBAUTHN_ENABLED",
        description="Enable WebAuthn/Passkey authentication",
    )
    webauthn_rp_id: str = Field(
        default="localhost",
        alias="AUTH_WEBAUTHN_RP_ID",
        description="WebAuthn Relying Party ID (usually domain)",
    )
    webauthn_rp_name: str = Field(
        default="Baselith-Core",
        alias="AUTH_WEBAUTHN_RP_NAME",
        description="WebAuthn Relying Party name",
    )
    webauthn_origin: str = Field(
        default="http://localhost:8000",
        alias="AUTH_WEBAUTHN_ORIGIN",
        description="WebAuthn origin URL",
    )

    # === Reverse-proxy trust ===
    # Client IP (used for audit/login-history) is read from X-Forwarded-For /
    # X-Real-IP ONLY when the direct peer is a trusted proxy. Empty = never
    # trust forwarded headers (use the socket peer). "*" trusts all peers — set
    # only when an upstream edge strips/validates the header.
    trusted_proxies: List[str] = Field(
        default=[],
        alias="AUTH_TRUSTED_PROXIES",
        description="Peer IPs allowed to set X-Forwarded-For/X-Real-IP ('*' = all)",
    )

    # === Public base URL (used to build links in emails: reset, invite, verify) ===
    app_base_url: str = Field(
        default="http://localhost:8000",
        alias="AUTH_APP_BASE_URL",
        description="Public base URL of the app, used to build email links",
    )

    # === Transactional email (SMTP) ===
    smtp_host: Optional[str] = Field(
        default=None,
        alias="AUTH_SMTP_HOST",
        description="SMTP server host. When unset, emails are logged (dev mode).",
    )
    smtp_port: int = Field(default=587, alias="AUTH_SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, alias="AUTH_SMTP_USERNAME")
    smtp_password: Optional[SecretStr] = Field(default=None, alias="AUTH_SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="AUTH_SMTP_USE_TLS")
    smtp_from: str = Field(
        default="no-reply@baselith.local",
        alias="AUTH_SMTP_FROM",
        description="From address for transactional emails",
    )
    email_from_name: str = Field(default="Baselith", alias="AUTH_EMAIL_FROM_NAME")

    # === Self-service & lifecycle ===
    self_service_enabled: bool = Field(
        default=True,
        alias="AUTH_SELF_SERVICE_ENABLED",
        description="Enable the self-service 'My Account' surface for end users",
    )
    email_verification_required: bool = Field(
        default=False,
        alias="AUTH_EMAIL_VERIFICATION_REQUIRED",
        description="Require verified email before a new user can log in",
    )
    password_max_age_days: int = Field(
        default=0,
        alias="AUTH_PASSWORD_MAX_AGE_DAYS",
        ge=0,
        description="Force password rotation after N days (0 = never)",
    )

    # === API keys / Personal Access Tokens ===
    api_keys_enabled: bool = Field(
        default=True,
        alias="AUTH_API_KEYS_ENABLED",
        description="Allow issuing personal access tokens / service API keys",
    )
    api_key_max_lifetime_days: int = Field(
        default=365,
        alias="AUTH_API_KEY_MAX_LIFETIME_DAYS",
        ge=0,
        description="Maximum API-key lifetime in days (0 = no expiry allowed)",
    )

    # === SSO (OIDC / SAML) federation ===
    sso_enabled: bool = Field(
        default=False,
        alias="AUTH_SSO_ENABLED",
        description="Enable SSO federation (OIDC / SAML identity providers)",
    )
    sso_allow_signup: bool = Field(
        default=True,
        alias="AUTH_SSO_ALLOW_SIGNUP",
        description="Auto-provision (JIT) local accounts for new SSO identities",
    )

    # =========================================================================
    # Multi-Tenancy Configuration
    # =========================================================================

    tenant_id: Optional[str] = Field(
        default=None,
        alias="AUTH_TENANT_ID",
        description="Tenant ID for multi-tenancy isolation. If None, uses default tenant.",
    )
    isolation_mode: str = Field(
        default="shared",
        alias="AUTH_ISOLATION_MODE",
        description="Isolation mode: 'shared' (shared resources), 'dedicated' (isolated resources), or 'hybrid'",
    )
    namespace: Optional[str] = Field(
        default=None,
        alias="AUTH_NAMESPACE",
        description="Namespace for resource isolation (e.g., database schema prefix)",
    )
    enable_strict_isolation: bool = Field(
        default=False,
        alias="AUTH_STRICT_ISOLATION",
        description="Enable strict tenant isolation (raises error if tenant context is missing)",
    )


# Global instance (DEPRECATED: Use ServiceRegistry instead)
# This is maintained for backward compatibility only
_auth_config: Optional[AuthConfig] = None


def get_auth_config() -> AuthConfig:
    """Get or create the global auth configuration instance.

    DEPRECATED: This function uses global state pattern and is maintained
    only for backward compatibility. New code should use ServiceRegistry.get(AuthConfig)
    or the get_auth_config_dep() FastAPI dependency instead.
    """
    global _auth_config
    if _auth_config is None:
        _auth_config = AuthConfig()
        logger.info(
            f"Initialized AuthConfig (auth_required={_auth_config.auth_required}, "
            f"mfa_enabled={_auth_config.mfa_enabled}, "
            f"tenant_id={_auth_config.tenant_id}, "
            f"isolation_mode={_auth_config.isolation_mode})"
        )
    return _auth_config

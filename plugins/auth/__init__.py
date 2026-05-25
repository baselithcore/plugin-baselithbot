"""
Auth Plugin - Professional Authentication System.

Provides email/password login, MFA (TOTP), and role-based access control.
"""

from plugins.auth.config import AuthConfig, get_auth_config
from plugins.auth.models import User, RefreshToken
from plugins.auth.password import hash_password, verify_password
from plugins.auth.mfa import generate_secret, verify_totp, get_provisioning_uri

__all__ = [
    "AuthConfig",
    "get_auth_config",
    "User",
    "RefreshToken",
    "hash_password",
    "verify_password",
    "generate_secret",
    "verify_totp",
    "get_provisioning_uri",
]

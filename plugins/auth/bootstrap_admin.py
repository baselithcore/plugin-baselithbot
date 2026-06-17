"""Idempotent bootstrap of the initial admin user.

Solves the chicken-and-egg problem: the admin console requires an admin user,
but a fresh database has none and ``/register`` only grants the USER role.

When ``AUTH_BOOTSTRAP_ADMIN_EMAIL`` / ``AUTH_BOOTSTRAP_ADMIN_PASSWORD`` are set
and that email does not yet exist, an admin account is created on startup.
"""

from __future__ import annotations

from core.auth.types import AuthRole
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.password import hash_password
from plugins.auth.persistence import AuthPersistence

logger = get_logger(__name__)


def bootstrap_admin(config: AuthConfig, persistence: AuthPersistence) -> None:
    """Create the configured bootstrap admin if it does not already exist.

    Never raises — a bootstrap failure must not block plugin initialisation.
    """
    email = config.bootstrap_admin_email
    secret = config.bootstrap_admin_password
    if not email or not secret:
        return
    password = secret.get_secret_value()
    if not password:
        return

    try:
        if persistence.get_user_by_email(email):
            return  # already provisioned

        username = config.bootstrap_admin_username or None
        if username and persistence.get_user_by_username(username):
            username = None  # avoid unique collision with an existing username

        persistence.create_user(
            email=email,
            password_hash=hash_password(password),
            username=username,
            roles={AuthRole.ADMIN},
        )
        logger.info("Bootstrap admin user created: %s", email)
    except Exception as exc:  # noqa: BLE001
        logger.error("Bootstrap admin creation failed: %s", exc)


__all__ = ["bootstrap_admin"]

"""First-run setup service: provision the initial admin user.

A fresh installation has no privileged account. Rather than forcing operators
to seed one via environment variables (the headless path, see
``plugins.auth.bootstrap_admin``), the UI exposes a one-time setup wizard backed
by these helpers.

**Fail-closed invariant:** :func:`create_initial_admin` refuses to run once any
user exists. The public ``/auth/setup/initialize`` endpoint is therefore only
usable on a genuinely un-provisioned system; the instant any account exists it
raises :class:`SetupAlreadyCompleted`. Keying on "no users" (not "no admin")
keeps the public endpoint from ever being a privilege-escalation backdoor on an
install that already has accounts — there, an admin is created/promoted through
the authenticated admin console instead.
"""

from __future__ import annotations

from core.auth.types import AuthRole
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.models import User
from plugins.auth.password import hash_password, validate_password_strength_async
from plugins.auth.persistence import AuthPersistence
from plugins.auth.username import validate_username

logger = get_logger(__name__)

#: Roles granted to the very first account created through the wizard.
INITIAL_ADMIN_ROLES = {AuthRole.ADMIN}


class SetupError(Exception):
    """Base class for setup failures."""


class SetupAlreadyCompleted(SetupError):
    """Raised when setup is attempted but the system already has users."""


class SetupValidationError(SetupError):
    """Raised when the submitted credentials fail validation."""


def is_setup_needed(persistence: AuthPersistence) -> bool:
    """Whether the system still needs its initial admin.

    ``True`` only on a genuinely un-provisioned system — an **empty user table**.
    Keying on "no users" rather than "no admin" is deliberate: the
    ``/setup/initialize`` endpoint is public, so it must stay closed the moment
    *any* account exists.
    """
    try:
        return persistence.count_users() == 0
    except Exception as exc:  # noqa: BLE001 — never block the login screen
        logger.error("Setup-status check failed: %s", exc)
        return False


async def create_initial_admin(
    persistence: AuthPersistence,
    config: AuthConfig,
    *,
    email: str,
    password: str,
    username: str | None = None,
) -> User:
    """Create the first admin. Fail-closed if any user already exists.

    Raises:
        SetupAlreadyCompleted: the system already has at least one user.
        SetupValidationError: the email/username/password are invalid or taken.
    """
    # Fail-closed gate — re-checked here (not just at the route) so the service
    # is safe to call from anywhere. The public endpoint creates a privileged
    # account, so it is refused the instant the system has any user at all.
    if persistence.count_users() > 0:
        raise SetupAlreadyCompleted("Setup has already been completed")

    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise SetupValidationError("A valid email address is required")
    if persistence.get_user_by_email(email):
        raise SetupValidationError("A user with this email already exists")

    normalized_username = (username or "").strip() or None
    if normalized_username:
        username_errors = validate_username(normalized_username)
        if username_errors:
            raise SetupValidationError("; ".join(username_errors))
        if persistence.get_user_by_username(normalized_username):
            raise SetupValidationError("Username already taken")

    password_errors = await validate_password_strength_async(
        password, check_breaches=config.check_pwned_passwords
    )
    if password_errors:
        raise SetupValidationError("; ".join(password_errors))

    user = persistence.create_user(
        email=email,
        username=normalized_username,
        password_hash=hash_password(password),
        roles=set(INITIAL_ADMIN_ROLES),
    )
    logger.info("Initial admin provisioned via setup wizard: %s", email)
    return user


__all__ = [
    "INITIAL_ADMIN_ROLES",
    "SetupAlreadyCompleted",
    "SetupError",
    "SetupValidationError",
    "create_initial_admin",
    "is_setup_needed",
]

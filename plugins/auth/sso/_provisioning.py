"""Just-in-time provisioning + identity linking for federated SSO logins."""

import secrets
from typing import Any, Dict, Optional

from core.auth import AuthRole
from core.observability.logging import get_logger
from plugins.auth.password import hash_password

logger = get_logger(__name__)


class ProvisioningError(Exception):
    """Raised when an SSO identity cannot be mapped to a local account."""


def _roles_from(values) -> set:
    roles = set()
    for r in values or []:
        try:
            roles.add(AuthRole(r))
        except ValueError:
            continue
    return roles or {AuthRole.USER}


def provision_sso_user(
    persistence,
    provider: Dict[str, Any],
    subject: str,
    email: Optional[str],
    name: Optional[str],
    allow_signup: bool,
):
    """Resolve an SSO identity to a local user, provisioning if permitted.

    Order: existing link → match by email → JIT create. Returns the local user
    (a :class:`plugins.auth.models.User`).
    """
    provider_id = str(provider["id"])

    # 1) Already linked.
    identity = persistence.get_sso_identity(provider_id, subject)
    if identity:
        user = persistence.get_user_by_id(str(identity["user_id"]))
        if user and user.is_active:
            persistence.link_sso_identity(provider_id, user.id, subject, email)
            return user

    # 2) Match an existing local account by email.
    if email:
        existing = persistence.get_user_by_email(email)
        if existing:
            persistence.link_sso_identity(provider_id, existing.id, subject, email)
            logger.info("Linked SSO identity to existing user %s", existing.id)
            return existing

    # 3) Just-in-time provisioning.
    if not (provider.get("auto_provision", True) and allow_signup):
        raise ProvisioningError(
            "No local account for this identity and signup is disabled"
        )
    if not email:
        raise ProvisioningError("IdP did not provide an email; cannot provision")

    user = persistence.create_user(
        email=email,
        username=None,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        roles=_roles_from(provider.get("default_roles")),
    )
    persistence.set_email_verified(user.id, True)
    if name:
        persistence.update_profile(user.id, name, None)
    persistence.link_sso_identity(provider_id, user.id, subject, email)
    logger.info(
        "JIT-provisioned user %s via SSO provider %s", user.id, provider["slug"]
    )
    return user

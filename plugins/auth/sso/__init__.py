"""SSO federation (OIDC + SAML 2.0) for the auth plugin.

The public surface is intentionally small: load a provider (with its secret
decrypted), drive the OIDC or SAML flow, then provision/link the local user.
"""

from typing import Any, Dict, Optional

from plugins.auth.sso._crypto import decrypt_secret, encrypt_secret
from plugins.auth.sso._oidc import OidcClient, OidcError, extract_identity
from plugins.auth.sso._provisioning import ProvisioningError, provision_sso_user
from plugins.auth.sso._saml import (
    SAML_AVAILABLE,
    extract_saml_identity,
    login_redirect,
    metadata_xml,
    process_acs,
)


def load_provider(persistence, slug: str) -> Optional[Dict[str, Any]]:
    """Fetch a provider and decrypt its secret into protocol-specific fields.

    OIDC: ``client_secret``. SAML: ``sp_private_key``.
    """
    row = persistence.get_sso_provider(slug)
    if not row:
        return None
    secret = decrypt_secret(row.get("secret_enc"))
    if row["protocol"] == "oidc":
        row["client_secret"] = secret or ""
    else:
        row["sp_private_key"] = secret or ""
    return row


__all__ = [
    "OidcClient",
    "OidcError",
    "extract_identity",
    "extract_saml_identity",
    "login_redirect",
    "metadata_xml",
    "process_acs",
    "provision_sso_user",
    "ProvisioningError",
    "SAML_AVAILABLE",
    "encrypt_secret",
    "decrypt_secret",
    "load_provider",
]

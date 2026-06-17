"""Encryption-at-rest for SSO provider secrets (client secrets, SP keys).

Reuses the core :class:`FieldEncryptor` (AES-256-GCM) keyed from the auth
secret. When no secret is configured (dev), values are stored as-is and a
warning is logged — production deployments must set ``SECRET_KEY``.
"""

from typing import Optional

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig

logger = get_logger(__name__)

_encryptor = None
_loaded = False


def _get_encryptor():
    """Lazily build a FieldEncryptor from the auth secret key."""
    global _encryptor, _loaded
    if _loaded:
        return _encryptor
    _loaded = True
    try:
        config = ServiceRegistry.get(AuthConfig)
        secret = config.secret_key
    except Exception:
        secret = None
    if not secret:
        logger.warning(
            "No SECRET_KEY configured; SSO secrets stored without encryption. "
            "Set SECRET_KEY in production."
        )
        _encryptor = None
        return None
    try:
        from core.security.encryption import FieldEncryptor

        _encryptor = FieldEncryptor.from_keys({"auth": secret}, active_key_id="auth")
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to init SSO encryptor: %s", exc)
        _encryptor = None
    return _encryptor


def encrypt_secret(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt a provider secret for storage (no-op when empty)."""
    if not plaintext:
        return None
    enc = _get_encryptor()
    if enc is None:
        return plaintext
    return enc.encrypt(plaintext)


def decrypt_secret(token: Optional[str]) -> Optional[str]:
    """Decrypt a stored provider secret (tolerates plaintext legacy values)."""
    if not token:
        return None
    enc = _get_encryptor()
    if enc is None:
        return token
    try:
        return enc.decrypt(token)
    except Exception:
        # Value may predate encryption being enabled.
        return token

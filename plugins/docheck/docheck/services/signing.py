"""Ed25519 report signing."""

import hashlib
import json
from typing import Any

from nacl.signing import VerifyKey

from .audit import _signing_key  # reuse master signing key


def sign_report(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).digest()
    sig = _signing_key.sign(digest).signature
    return f"ed25519:{sig.hex()}"


def verify_report(payload: dict[str, Any], signature: str, pubkey_hex: str) -> bool:
    if not signature.startswith("ed25519:"):
        return False
    sig_bytes = bytes.fromhex(signature.removeprefix("ed25519:"))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).digest()
    vk = VerifyKey(bytes.fromhex(pubkey_hex))
    try:
        vk.verify(digest, sig_bytes)
        return True
    except Exception:
        return False


def public_key_hex() -> str:
    return _signing_key.verify_key.encode().hex()


def sign_bytes(data: bytes) -> str:
    """Sign arbitrary canonical bytes with the master Ed25519 key."""
    digest = hashlib.sha256(data).digest()
    sig = _signing_key.sign(digest).signature
    return f"ed25519:{sig.hex()}"

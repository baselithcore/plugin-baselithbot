"""
MFA (Multi-Factor Authentication) Module.

Implements TOTP (Time-based One-Time Password) for MFA.
Compatible with Google Authenticator, Authy, and similar apps.
"""

import hashlib
from core.observability.logging import get_logger
import secrets
from typing import List, Tuple

try:
    import pyotp
except ImportError:
    raise ImportError("pyotp is required for MFA. Install with: pip install pyotp")

try:
    import qrcode
    import qrcode.image.svg
    from io import BytesIO
    import base64

    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

from core.di.container import ServiceRegistry
from plugins.auth.config import AuthConfig

logger = get_logger(__name__)


def generate_secret() -> str:
    """
    Generate a new TOTP secret.

    Returns:
        Base32-encoded secret string
    """
    return pyotp.random_base32()


def get_provisioning_uri(email: str, secret: str) -> str:
    """
    Generate the provisioning URI for authenticator apps.

    Args:
        email: User's email address
        secret: TOTP secret

    Returns:
        otpauth:// URI for QR code generation
    """
    config = ServiceRegistry.get(AuthConfig)
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=config.mfa_issuer)


def get_qr_code_base64(email: str, secret: str) -> str:
    """
    Generate a QR code image as base64 string.

    Args:
        email: User's email address
        secret: TOTP secret

    Returns:
        Base64-encoded PNG image (data URI format)

    Raises:
        ImportError: If qrcode library is not installed
    """
    if not QR_AVAILABLE:
        raise ImportError(
            "qrcode is required for QR generation. "
            "Install with: pip install qrcode[pil]"
        )

    uri = get_provisioning_uri(email, secret)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a TOTP code.

    Args:
        secret: TOTP secret
        code: 6-digit code from authenticator

    Returns:
        True if code is valid, False otherwise
    """
    try:
        totp = pyotp.TOTP(secret)
        # valid_window=1 allows for slight time drift (±30 seconds)
        return totp.verify(code, valid_window=1)
    except Exception as e:
        logger.warning(f"TOTP verification error: {e}")
        return False


def generate_backup_codes(count: int = 10) -> Tuple[List[str], List[str]]:
    """
    Generate backup codes for MFA recovery.

    Args:
        count: Number of backup codes to generate

    Returns:
        Tuple of (plain_codes, hashed_codes)
        - plain_codes: To show to the user (once!)
        - hashed_codes: To store in database
    """
    plain_codes = []
    hashed_codes = []

    for _ in range(count):
        # Generate 8-character alphanumeric code (grouped for readability)
        code = secrets.token_hex(4).upper()
        formatted_code = f"{code[:4]}-{code[4:]}"
        plain_codes.append(formatted_code)

        # Hash for storage
        hashed = hashlib.sha256(formatted_code.encode()).hexdigest()
        hashed_codes.append(hashed)

    return plain_codes, hashed_codes


def verify_backup_code(code: str, stored_hash: str) -> bool:
    """
    Verify a backup code against its stored hash.

    Args:
        code: User-provided backup code
        stored_hash: SHA256 hash from database

    Returns:
        True if code matches, False otherwise
    """
    # Normalize code (remove dashes, uppercase)
    normalized = code.replace("-", "").upper()
    # Reformat to match stored format
    formatted = f"{normalized[:4]}-{normalized[4:]}" if len(normalized) == 8 else code

    code_hash = hashlib.sha256(formatted.encode()).hexdigest()
    return secrets.compare_digest(code_hash, stored_hash)

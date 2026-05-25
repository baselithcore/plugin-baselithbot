"""
Password Hashing Module.

Uses Argon2id for secure password hashing.
"""

from core.observability.logging import get_logger
import re
import secrets
import string
from typing import List

try:
    from argon2 import PasswordHasher, Type
    from argon2.exceptions import VerifyMismatchError, InvalidHashError
except ImportError:
    raise ImportError(
        "argon2-cffi is required for password hashing. "
        "Install with: pip install argon2-cffi"
    )

from core.di.container import ServiceRegistry
from plugins.auth.config import AuthConfig
from plugins.auth.pwned_passwords import get_pwned_checker

logger = get_logger(__name__)

# Argon2id hasher with secure defaults
# - time_cost: iterations (higher = slower but more secure)
# - memory_cost: memory in KiB
# - parallelism: threads
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,  # Argon2id (recommended)
)


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.

    Args:
        password: Plain text password

    Returns:
        Argon2id hash string
    """
    return _hasher.hash(password)


def verify_password(password: str, hash: str) -> bool:
    """
    Verify a password against an Argon2 hash.

    Args:
        password: Plain text password to verify
        hash: Stored Argon2 hash

    Returns:
        True if password matches, False otherwise
    """
    try:
        _hasher.verify(hash, password)
        return True
    except VerifyMismatchError:
        return False
    except InvalidHashError:
        logger.warning("Invalid password hash format encountered")
        return False


def needs_rehash(hash: str) -> bool:
    """
    Check if a hash needs to be upgraded to current parameters.

    Args:
        hash: Stored Argon2 hash

    Returns:
        True if hash should be rehashed with current parameters
    """
    try:
        return _hasher.check_needs_rehash(hash)
    except InvalidHashError:
        return True


def validate_password_strength(password: str) -> List[str]:
    """
    Validate password strength against security policy.

    Args:
        password: Password to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    config = ServiceRegistry.get(AuthConfig)
    errors: List[str] = []

    # Minimum length
    if len(password) < config.password_min_length:
        errors.append(
            f"Password must be at least {config.password_min_length} characters"
        )

    # Require at least one uppercase
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    # Require at least one lowercase
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    # Require at least one digit
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    # Require at least one special character
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")

    return errors


async def validate_password_strength_async(
    password: str, check_breaches: bool = True
) -> List[str]:
    """
    Validate password strength with optional breach checking.

    Args:
        password: Password to validate
        check_breaches: Check against HaveIBeenPwned database

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = validate_password_strength(password)

    # Check for compromised passwords (NIST SP 800-63B requirement)
    if check_breaches and not errors:
        config = ServiceRegistry.get(AuthConfig)
        if config.check_pwned_passwords:
            checker = get_pwned_checker(enabled=True)
            is_pwned, count = await checker.is_pwned(password)
            if is_pwned:
                errors.append(
                    f"Password has been exposed in {count} data breaches. "
                    "Please choose a different password."
                )

    return errors


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password.

    The generated password is guaranteed to meet all strength requirements:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        length: Password length (minimum 12, default 16)

    Returns:
        Secure random password string
    """
    if length < 12:
        length = 12

    # Character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"

    # Ensure at least one of each required type
    password_chars = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special),
    ]

    # Fill remaining length with random characters from all sets
    all_chars = lowercase + uppercase + digits + special
    remaining_length = length - len(password_chars)
    password_chars.extend(secrets.choice(all_chars) for _ in range(remaining_length))

    # Shuffle to avoid predictable positions
    password_list = list(password_chars)
    secrets.SystemRandom().shuffle(password_list)

    return "".join(password_list)

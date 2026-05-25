"""
Username validation and sanitization.

Modern best practices for username handling:
- Allow alphanumeric + limited special chars (._-)
- Prevent username enumeration via timing attacks
- Case-insensitive uniqueness
- Length limits (3-50 chars)
- No offensive/reserved words
"""

import re
from typing import List, Optional

# Reserved usernames (system accounts, common names)
RESERVED_USERNAMES = {
    "admin",
    "administrator",
    "root",
    "system",
    "moderator",
    "mod",
    "support",
    "help",
    "api",
    "www",
    "mail",
    "ftp",
    "ssh",
    "webmaster",
    "hostmaster",
    "postmaster",
    "abuse",
    "noreply",
    "no-reply",
    "security",
    "info",
    "contact",
    "guest",
    "anonymous",
    "null",
    "undefined",
    "me",
    "self",
}

# Username validation regex
# Rules:
# - 3-50 characters
# - Must start with alphanumeric
# - Can contain: letters, numbers, underscore, dash, dot
# - No consecutive special chars
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{2,49}$")
CONSECUTIVE_SPECIAL = re.compile(r"[._-]{2,}")
LEADING_SPECIAL = re.compile(r"^[._-]")
TRAILING_SPECIAL = re.compile(r"[._-]$")


def validate_username(username: Optional[str]) -> List[str]:
    """
    Validate username format and rules.

    Args:
        username: Username to validate (or None)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Username is optional
    if username is None or username == "":
        return errors

    # Remove whitespace
    username = username.strip()

    # Length check
    if len(username) < 3:
        errors.append("Username must be at least 3 characters")
        return errors  # No point checking further

    if len(username) > 50:
        errors.append("Username must not exceed 50 characters")

    # Character validation
    if not USERNAME_REGEX.match(username):
        errors.append(
            "Username must start with a letter or number and contain only "
            "letters, numbers, dots, underscores, or dashes"
        )

    # No consecutive special characters
    if CONSECUTIVE_SPECIAL.search(username):
        errors.append(
            "Username cannot contain consecutive special characters (., _, -)"
        )

    # No leading special characters
    if LEADING_SPECIAL.match(username):
        errors.append("Username cannot start with a special character")

    # No trailing special characters
    if TRAILING_SPECIAL.search(username):
        errors.append("Username cannot end with a special character")

    # Reserved names check (case-insensitive)
    if username.lower() in RESERVED_USERNAMES:
        errors.append("This username is reserved and cannot be used")

    # Prevent common abuse patterns
    if username.lower().startswith("admin") or username.lower().startswith("mod"):
        if len(username) < 8:  # Allow "administrator123" but not "admin1"
            errors.append("Username appears to be a reserved system name")

    # Prevent confusables (optional - can be extended)
    if ".." in username or "__" in username or "--" in username:
        errors.append("Username cannot contain repeated special characters")

    return errors


def sanitize_username(username: Optional[str]) -> Optional[str]:
    """
    Sanitize username input.

    Removes whitespace and converts to lowercase for consistency.

    Args:
        username: Raw username input

    Returns:
        Sanitized username or None
    """
    if not username:
        return None

    # Strip whitespace
    username = username.strip()

    if not username:
        return None

    # Lowercase for case-insensitive comparison
    # Note: Store in DB as-is (preserve case), but compare case-insensitively
    return username


def normalize_username(username: Optional[str]) -> Optional[str]:
    """
    Normalize username for case-insensitive lookups.

    Args:
        username: Username to normalize

    Returns:
        Lowercase username for comparison
    """
    if not username:
        return None
    return username.lower().strip()


def is_valid_username(username: Optional[str]) -> bool:
    """
    Quick check if username is valid.

    Args:
        username: Username to check

    Returns:
        True if valid, False otherwise
    """
    return len(validate_username(username)) == 0

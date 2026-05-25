"""
Compromised Password Detection using HaveIBeenPwned API.

Implements k-anonymity model to check passwords against breach databases
without revealing the actual password.

Reference: https://haveibeenpwned.com/API/v3#PwnedPasswords
NIST SP 800-63B Section 5.1.1.2
"""

import hashlib
from core.observability.logging import get_logger
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = get_logger(__name__)


class PwnedPasswordChecker:
    """
    Check if passwords have been compromised in data breaches.

    Uses the k-anonymity model:
    1. Hash password with SHA-1
    2. Send first 5 characters to API
    3. Check if suffix exists in response
    4. Never reveals full password hash
    """

    def __init__(
        self,
        api_url: str = "https://api.pwnedpasswords.com/range",
        timeout: float = 5.0,
        enabled: bool = True,
    ) -> None:
        """
        Initialize the checker.

        Args:
            api_url: HIBP API endpoint
            timeout: Request timeout in seconds
            enabled: Enable/disable checks (for testing/offline)
        """
        self.api_url = api_url
        self.timeout = timeout
        self.enabled = enabled

        if not httpx:
            logger.warning(
                "httpx not installed. Pwned password checking disabled. "
                "Install with: pip install httpx"
            )
            self.enabled = False

    async def is_pwned(self, password: str) -> tuple[bool, Optional[int]]:
        """
        Check if password appears in breach database.

        Args:
            password: Plain text password to check

        Returns:
            Tuple of (is_pwned, prevalence_count)
            - is_pwned: True if password found in breaches
            - prevalence_count: Number of times seen (None if not pwned or error)
        """
        if not self.enabled or not httpx:
            return False, None

        try:
            # Hash password with SHA-1 (HIBP requirement)
            sha1_hash = (
                hashlib.sha1(password.encode("utf-8"), usedforsecurity=False)
                .hexdigest()
                .upper()
            )
            prefix, suffix = sha1_hash[:5], sha1_hash[5:]

            # Query API with first 5 characters (k-anonymity)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_url}/{prefix}",
                    headers={"User-Agent": "Baselith-Core-System-Auth-Plugin"},
                )
                response.raise_for_status()

            # Check if suffix exists in response
            for line in response.text.splitlines():
                hash_suffix, count = line.split(":")
                if hash_suffix == suffix:
                    prevalence = int(count)
                    logger.warning(
                        f"Password found in {prevalence} breaches "
                        f"(hash prefix: {prefix})"
                    )
                    return True, prevalence

            # Not found in breaches
            return False, None

        except httpx.TimeoutException:
            logger.error("HIBP API timeout - allowing password (fail-open)")
            return False, None
        except httpx.HTTPError as e:
            logger.error(f"HIBP API error: {e} - allowing password (fail-open)")
            return False, None
        except Exception as e:
            logger.error(
                f"Unexpected error checking pwned password: {e} - allowing password"
            )
            return False, None

    async def check_and_log(self, password: str, user_context: str = "") -> bool:
        """
        Check password and log result.

        Args:
            password: Password to check
            user_context: Optional context for logging (e.g., email)

        Returns:
            True if password is safe (not pwned), False if compromised
        """
        is_pwned, count = await self.is_pwned(password)

        if is_pwned:
            context_msg = f" for {user_context}" if user_context else ""
            logger.warning(
                f"SECURITY: Compromised password detected{context_msg} "
                f"(seen {count} times in breaches)"
            )
            return False

        return True


# Global instance
_pwned_checker: Optional[PwnedPasswordChecker] = None


def get_pwned_checker(enabled: bool = True) -> PwnedPasswordChecker:
    """Get or create global pwned password checker."""
    global _pwned_checker
    if _pwned_checker is None:
        _pwned_checker = PwnedPasswordChecker(enabled=enabled)
    return _pwned_checker

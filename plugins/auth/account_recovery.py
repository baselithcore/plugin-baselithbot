"""
Account Recovery Module.

Provides secure account recovery mechanisms:
- Password reset via email
- Account unlock
- Emergency MFA bypass with backup codes
- Account recovery for locked/compromised accounts

Security considerations:
- Time-limited recovery tokens (1 hour)
- Single-use tokens
- Rate limiting on recovery requests
- Audit logging
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from plugins.auth.security import generate_secure_token
from core.di.container import ServiceRegistry
from plugins.auth.config import AuthConfig

logger = get_logger(__name__)


class RecoveryTokenStore:
    """
    Store for password reset and account recovery tokens.

    In production, use Redis with TTL for automatic expiration.
    """

    def __init__(self) -> None:
        """Initialize token store."""
        self._tokens: dict[str, dict] = {}

    def create_password_reset_token(
        self, user_id: str, email: str, ttl_minutes: int = 60
    ) -> str:
        """
        Create a password reset token.

        Args:
            user_id: User ID
            email: User email
            ttl_minutes: Token validity in minutes

        Returns:
            Reset token
        """
        token = generate_secure_token("reset", length=32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        self._tokens[token] = {
            "type": "password_reset",
            "user_id": user_id,
            "email": email,
            "expires_at": expires_at,
            "used": False,
        }

        logger.info(f"Created password reset token for user {user_id}")
        return token

    def create_account_unlock_token(self, user_id: str, ttl_minutes: int = 60) -> str:
        """
        Create an account unlock token.

        Args:
            user_id: User ID
            ttl_minutes: Token validity in minutes

        Returns:
            Unlock token
        """
        token = generate_secure_token("unlock", length=32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        self._tokens[token] = {
            "type": "account_unlock",
            "user_id": user_id,
            "expires_at": expires_at,
            "used": False,
        }

        logger.info(f"Created account unlock token for user {user_id}")
        return token

    def validate_token(self, token: str, expected_type: str) -> Optional[dict]:
        """
        Validate and consume a recovery token.

        Args:
            token: Recovery token
            expected_type: Expected token type ("password_reset" or "account_unlock")

        Returns:
            Token data if valid, None otherwise
        """
        token_data = self._tokens.get(token)

        if not token_data:
            logger.warning("Token validation failed: Token not found")
            return None

        # Check type
        if token_data["type"] != expected_type:
            logger.warning(
                f"Token validation failed: Wrong type (expected {expected_type}, "
                f"got {token_data['type']})"
            )
            return None

        # Check expiration
        if datetime.now(timezone.utc) > token_data["expires_at"]:
            logger.warning("Token validation failed: Token expired")
            del self._tokens[token]
            return None

        # Check if already used
        if token_data["used"]:
            logger.warning("Token validation failed: Token already used")
            return None

        # Mark as used
        token_data["used"] = True

        return token_data

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a recovery token.

        Args:
            token: Token to revoke

        Returns:
            True if token was revoked, False if not found
        """
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all tokens for a user.

        Args:
            user_id: User ID

        Returns:
            Number of tokens revoked
        """
        tokens_to_revoke = [
            token
            for token, data in self._tokens.items()
            if data.get("user_id") == user_id
        ]

        for token in tokens_to_revoke:
            del self._tokens[token]

        if tokens_to_revoke:
            logger.info(
                f"Revoked {len(tokens_to_revoke)} recovery tokens for user {user_id}"
            )

        return len(tokens_to_revoke)

    def cleanup_expired(self) -> int:
        """
        Clean up expired tokens.

        Returns:
            Number of tokens removed
        """
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token
            for token, data in self._tokens.items()
            if data.get("expires_at", now) < now
        ]

        for token in expired_tokens:
            del self._tokens[token]

        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired recovery tokens")

        return len(expired_tokens)


class AccountRecoveryManager:
    """
    Manage account recovery operations.

    Coordinates password resets, account unlocks, and emergency access.
    """

    def __init__(self) -> None:
        """Initialize recovery manager."""
        self.token_store = RecoveryTokenStore()

    def initiate_password_reset(self, email: str, user_id: str) -> tuple[str, str]:
        """
        Initiate password reset process.

        Args:
            email: User email
            user_id: User ID

        Returns:
            Tuple of (token, reset_link)

        Raises:
            RuntimeError: If account recovery is disabled
        """
        config = ServiceRegistry.get(AuthConfig)
        if not config.account_recovery_enabled:
            logger.warning(
                f"Password reset attempted for {email} but account recovery is disabled"
            )
            raise RuntimeError(
                "Account recovery is currently disabled. "
                "Please contact your system administrator."
            )

        # Generate token
        token = self.token_store.create_password_reset_token(user_id, email)

        # In production, send email with this link
        # For now, just return the token
        reset_link = f"/reset-password?token={token}"

        logger.info(f"Password reset initiated for {email}")

        return token, reset_link

    def complete_password_reset(
        self, token: str, new_password_hash: str, persistence
    ) -> bool:
        """
        Complete password reset.

        Args:
            token: Reset token
            new_password_hash: New password hash
            persistence: Auth persistence instance

        Returns:
            True if successful, False otherwise
        """
        # Validate token
        token_data = self.token_store.validate_token(token, "password_reset")

        if not token_data:
            return False

        user_id = token_data["user_id"]

        # Get user
        user = persistence.get_user_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found during password reset")
            return False

        # Update password
        user.password_hash = new_password_hash
        user.failed_login_attempts = 0
        user.locked_until = None

        persistence.update_user(user)

        # Revoke all refresh tokens for security
        persistence.revoke_all_user_tokens(user_id)

        logger.info(f"Password reset completed for user {user_id}")

        return True

    def initiate_account_unlock(self, user_id: str) -> tuple[str, str]:
        """
        Initiate account unlock process.

        Args:
            user_id: User ID

        Returns:
            Tuple of (token, unlock_link)

        Raises:
            RuntimeError: If account recovery is disabled
        """
        config = ServiceRegistry.get(AuthConfig)
        if not config.account_recovery_enabled:
            logger.warning(
                f"Account unlock attempted for user {user_id} but account recovery is disabled"
            )
            raise RuntimeError(
                "Account recovery is currently disabled. "
                "Please contact your system administrator."
            )

        # Generate token
        token = self.token_store.create_account_unlock_token(user_id)

        # In production, send email with this link
        unlock_link = f"/unlock-account?token={token}"

        logger.info(f"Account unlock initiated for user {user_id}")

        return token, unlock_link

    def complete_account_unlock(self, token: str, persistence) -> bool:
        """
        Complete account unlock.

        Args:
            token: Unlock token
            persistence: Auth persistence instance

        Returns:
            True if successful, False otherwise
        """
        # Validate token
        token_data = self.token_store.validate_token(token, "account_unlock")

        if not token_data:
            return False

        user_id = token_data["user_id"]

        # Get user
        user = persistence.get_user_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found during account unlock")
            return False

        # Unlock account
        user.locked_until = None
        user.failed_login_attempts = 0

        persistence.update_user(user)

        logger.info(f"Account unlocked for user {user_id}")

        return True


# Global instance
_recovery_manager: Optional[AccountRecoveryManager] = None


def get_recovery_manager() -> AccountRecoveryManager:
    """Get or create global recovery manager instance."""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = AccountRecoveryManager()
    return _recovery_manager

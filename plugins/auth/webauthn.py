"""
WebAuthn / Passkey Authentication.

Implements FIDO2 / WebAuthn for passwordless authentication.
Supports:
- Platform authenticators (Touch ID, Face ID, Windows Hello)
- Security keys (YubiKey, etc.)
- Passkey sync across devices

Reference: W3C WebAuthn Level 3
"""

import json
from core.observability.logging import get_logger
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = get_logger(__name__)

# Try to import webauthn library
try:
    from webauthn import (
        generate_registration_options,
        verify_registration_response,
        generate_authentication_options,
        verify_authentication_response,
        options_to_json,
    )
    from webauthn.helpers import (
        parse_registration_credential_json,
        parse_authentication_credential_json,
    )
    from webauthn.helpers.structs import (
        PublicKeyCredentialDescriptor,
        AuthenticatorSelectionCriteria,
        UserVerificationRequirement,
        ResidentKeyRequirement,
    )

    WEBAUTHN_AVAILABLE = True
except ImportError:
    WEBAUTHN_AVAILABLE = False
    logger.warning(
        "py_webauthn not installed. WebAuthn support disabled. "
        "Install with: pip install webauthn"
    )


@dataclass
class WebAuthnCredential:
    """Stored WebAuthn credential."""

    id: str  # UUID
    user_id: str
    credential_id: bytes  # Raw credential ID
    public_key: bytes  # COSE public key
    sign_count: int
    transports: Optional[List[str]] = None
    aaguid: Optional[bytes] = None
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    name: Optional[str] = None  # User-friendly name (e.g., "iPhone 15 Pro")


class WebAuthnManager:
    """
    Manage WebAuthn registration and authentication.

    Handles:
    - Registration of new authenticators
    - Authentication with registered authenticators
    - Credential storage and retrieval
    """

    def __init__(
        self,
        rp_id: str,
        rp_name: str,
        origin: str,
        require_resident_key: bool = True,
        require_user_verification: bool = True,
    ) -> None:
        """
        Initialize WebAuthn manager.

        Args:
            rp_id: Relying Party ID (usually domain, e.g., "example.com")
            rp_name: Relying Party name (displayed to user)
            origin: Origin URL (e.g., "https://example.com")
            require_resident_key: Require discoverable credentials (passkeys)
            require_user_verification: Require user verification (PIN/biometric)
        """
        if not WEBAUTHN_AVAILABLE:
            raise ImportError(
                "WebAuthn support requires py_webauthn. "
                "Install with: pip install webauthn"
            )

        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin
        self.require_resident_key = require_resident_key
        self.require_user_verification = require_user_verification

        # Cross-worker challenge store (Postgres + in-memory fast path) with a
        # server-side TTL. A per-process dict here silently broke passkeys under
        # WEB_CONCURRENCY>1 and let abandoned challenges linger.
        from plugins.auth.webauthn_challenges import get_webauthn_challenge_store

        self._challenges = get_webauthn_challenge_store()

    def generate_registration_options(
        self,
        user_id: str,
        username: str,
        display_name: str,
        existing_credentials: Optional[List[WebAuthnCredential]] = None,
    ) -> Dict[str, Any]:
        """
        Generate registration options for new credential.

        Args:
            user_id: Unique user ID
            username: Username (email)
            display_name: Display name
            existing_credentials: List of user's existing credentials (to exclude)

        Returns:
            Registration options dict (to send to client)
        """
        # Generate challenge
        challenge = secrets.token_bytes(32)

        # Store challenge in the shared, TTL-bounded store (keyed by user).
        self._challenges.put(user_id, challenge)

        # Exclude existing credentials
        exclude_credentials = []
        if existing_credentials:
            exclude_credentials = [
                PublicKeyCredentialDescriptor(id=cred.credential_id)
                for cred in existing_credentials
            ]

        # Generate options
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=user_id.encode(),
            user_name=username,
            user_display_name=display_name,
            challenge=challenge,
            exclude_credentials=exclude_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED
                if self.require_resident_key
                else ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED
                if self.require_user_verification
                else UserVerificationRequirement.PREFERRED,
            ),
            timeout=60000,  # 60 seconds
        )

        return json.loads(options_to_json(options))

    def verify_registration(
        self,
        user_id: str,
        credential_json: Dict[str, Any],
    ) -> WebAuthnCredential:
        """
        Verify registration response and create credential.

        Args:
            user_id: User ID
            credential_json: Registration response from client

        Returns:
            Verified WebAuthnCredential

        Raises:
            ValueError: If verification fails
        """
        # Pop the challenge before verifying (single-use; also removes it on a
        # failed/abandoned attempt so it cannot be retried).
        expected_challenge = self._challenges.take(user_id)
        if not expected_challenge:
            raise ValueError("Challenge not found or expired")

        # Parse credential
        credential = parse_registration_credential_json(credential_json)

        # Verify registration
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_origin=self.origin,
            expected_rp_id=self.rp_id,
            require_user_verification=self.require_user_verification,
        )

        # Create credential object
        return WebAuthnCredential(
            id=secrets.token_urlsafe(16),
            user_id=user_id,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            transports=credential.response.transports,
            aaguid=verification.aaguid,
            created_at=datetime.now(timezone.utc),
        )

    def generate_authentication_options(
        self,
        user_credentials: Optional[List[WebAuthnCredential]] = None,
    ) -> Dict[str, Any]:
        """
        Generate authentication options.

        Args:
            user_credentials: List of user's credentials (if known)
                            None for discoverable credential flow

        Returns:
            Authentication options dict (to send to client)
        """
        # Generate challenge
        challenge = secrets.token_bytes(32)

        # Store under a unique, TTL-bounded id returned to the client.
        challenge_id = secrets.token_urlsafe(16)
        self._challenges.put(challenge_id, challenge)

        # Allow credentials
        allow_credentials = []
        if user_credentials:
            allow_credentials = [
                PublicKeyCredentialDescriptor(
                    id=cred.credential_id,
                    transports=cred.transports,
                )
                for cred in user_credentials
            ]

        # Generate options
        options = generate_authentication_options(
            rp_id=self.rp_id,
            challenge=challenge,
            allow_credentials=allow_credentials if allow_credentials else None,
            user_verification=UserVerificationRequirement.REQUIRED
            if self.require_user_verification
            else UserVerificationRequirement.PREFERRED,
            timeout=60000,
        )

        options_dict = json.loads(options_to_json(options))
        options_dict["challenge_id"] = challenge_id  # Return challenge ID

        return options_dict

    def verify_authentication(
        self,
        credential_json: Dict[str, Any],
        challenge_id: str,
        stored_credential: WebAuthnCredential,
    ) -> WebAuthnCredential:
        """
        Verify authentication response.

        Args:
            credential_json: Authentication response from client
            challenge_id: Challenge ID returned from generate_authentication_options
            stored_credential: Stored credential for the user

        Returns:
            Updated credential with new sign count

        Raises:
            ValueError: If verification fails
        """
        # Pop the challenge before verifying (single-use, removed on failure too).
        expected_challenge = self._challenges.take(challenge_id)
        if not expected_challenge:
            raise ValueError("Challenge not found or expired")

        # Parse credential
        credential = parse_authentication_credential_json(credential_json)

        # Verify authentication
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_origin=self.origin,
            expected_rp_id=self.rp_id,
            credential_public_key=stored_credential.public_key,
            credential_current_sign_count=stored_credential.sign_count,
            require_user_verification=self.require_user_verification,
        )

        # Update credential
        stored_credential.sign_count = verification.new_sign_count
        stored_credential.last_used = datetime.now(timezone.utc)

        return stored_credential


# Global instance
_webauthn_manager: Optional[WebAuthnManager] = None


def get_webauthn_manager(
    rp_id: Optional[str] = None,
    rp_name: Optional[str] = None,
    origin: Optional[str] = None,
) -> WebAuthnManager:
    """
    Get or create global WebAuthn manager.

    Args:
        rp_id: Override RP ID from config
        rp_name: Override RP name from config
        origin: Override origin from config
    """
    global _webauthn_manager

    if _webauthn_manager is None:
        # Try to get from config
        try:
            from core.di.container import ServiceRegistry
            from plugins.auth.config import AuthConfig

            config = ServiceRegistry.get(AuthConfig)
            rp_id = rp_id or getattr(config, "webauthn_rp_id", "localhost")
            rp_name = rp_name or getattr(config, "webauthn_rp_name", "Baselith-Core")
            origin = origin or getattr(
                config, "webauthn_origin", "http://localhost:8000"
            )
        except Exception as e:
            logger.warning(f"Could not load WebAuthn config: {e}")
            rp_id = rp_id or "localhost"
            rp_name = rp_name or "Baselith-Core"
            origin = origin or "http://localhost:8000"

        _webauthn_manager = WebAuthnManager(
            rp_id=rp_id,
            rp_name=rp_name,
            origin=origin,
        )

    return _webauthn_manager


def is_webauthn_available() -> bool:
    """Check if WebAuthn support is available."""
    return WEBAUTHN_AVAILABLE

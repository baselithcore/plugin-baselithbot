"""GDPR data-subject provider for the auth plugin (right to access + erasure).

Registers the identity store with the central :mod:`core.privacy` DSR service so
a subject-access or erasure request issued through the framework also covers the
personal data the auth plugin holds (profile + login history). The provider
deliberately implements **only** ``export`` and ``erase`` — it does *not* expose
``purge_expired``, so the time-based retention sweep never auto-deletes a user
account; erasure of identity data is always an explicit, per-subject act.

Subject identity: the DSR ``subject_id`` is the auth ``user_id`` (the tenant is
user-derived by default — see :mod:`plugins.auth.tenancy`). Erasure deletes the
``auth_users`` row; every child table (`auth_login_history`,
`auth_refresh_tokens`, MFA/WebAuthn/API-key/SSO/role rows, …) is removed via the
``ON DELETE CASCADE`` foreign keys declared in ``schema.sql``, so a single delete
performs a complete erasure.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from pydantic import SecretStr

from core.observability.logging import get_logger
from plugins.auth.persistence import AuthPersistence, get_auth_persistence

logger = get_logger(__name__)

# Credential / second-factor material is never part of a subject-access export.
_SECRET_FIELDS = frozenset({"password_hash", "mfa_secret"})

# Cap the exported login trail so a long-lived account cannot return an unbounded
# payload; the most recent events are the relevant ones for a SAR.
_HISTORY_LIMIT = 500


def _json_safe(value: Any) -> Any:
    """Coerce a value to a JSON-serialisable form for export."""
    if isinstance(value, SecretStr):
        return "[redacted]"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (set, frozenset)):
        return sorted(_json_safe(v) for v in value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class AuthDataProvider:
    """Export and erase the auth-held personal data for a single subject."""

    name = "auth"

    def __init__(self, persistence: AuthPersistence | None = None) -> None:
        # Resolved lazily so the shared singleton DB persistence is reused.
        self._persistence = persistence

    def _store(self) -> AuthPersistence:
        if self._persistence is None:
            self._persistence = get_auth_persistence()
        return self._persistence

    async def export(self, subject_id: str) -> Dict[str, Any]:
        """Return the subject's auth profile and recent login history.

        Returns an empty dict when the subject is unknown. Credentials and the
        TOTP secret are excluded; the login trail (the subject's own events) is
        included as it is personal data the subject is entitled to access.
        """
        return await asyncio.to_thread(self._export_sync, subject_id)

    def _export_sync(self, subject_id: str) -> Dict[str, Any]:
        store = self._store()
        user = store.get_user_by_id(subject_id)
        if user is None:
            return {}
        profile = {
            key: _json_safe(val)
            for key, val in vars(user).items()
            if key not in _SECRET_FIELDS
        }
        export: Dict[str, Any] = {"profile": profile}
        try:
            export["login_history"] = _json_safe(
                store.get_login_history(subject_id, limit=_HISTORY_LIMIT)
            )
        except Exception as exc:  # noqa: BLE001 — partial export beats none
            logger.warning("auth DSR login-history export failed: %s", exc)
            export["login_history"] = {"error": "export_failed"}
        return export

    async def erase(self, subject_id: str) -> int:
        """Erase the subject from the identity store (right to erasure).

        Deletes the ``auth_users`` row; all child rows cascade. Returns ``1`` if a
        user was removed, ``0`` if the subject was already absent.
        """
        return await asyncio.to_thread(self._erase_sync, subject_id)

    def _erase_sync(self, subject_id: str) -> int:
        store = self._store()
        deleted = store.delete_user(subject_id)
        return 1 if deleted else 0


__all__ = ["AuthDataProvider"]

"""Tests for the auth GDPR data-subject provider (export + erasure)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from core.auth.types import AuthRole
from plugins.auth.privacy_provider import AuthDataProvider


class _FakePersistence:
    """Minimal stand-in for AuthPersistence covering the provider's calls."""

    def __init__(self, user: Optional[Any], history: List[Dict[str, Any]]) -> None:
        self._user = user
        self._history = history
        self.deleted: List[str] = []

    def get_user_by_id(self, user_id: str) -> Optional[Any]:
        return self._user if (self._user and self._user.id == user_id) else None

    def get_login_history(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        return list(self._history)

    def delete_user(self, user_id: str) -> bool:
        if self._user and self._user.id == user_id:
            self.deleted.append(user_id)
            return True
        return False


def _fake_user(user_id: str = "u-1") -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email="jane@example.com",
        username="jane",
        password_hash="$argon2id$secret-hash",
        mfa_secret="TOTPSECRET",
        roles={AuthRole.USER},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )


async def test_export_excludes_secrets_and_serialises() -> None:
    user = _fake_user()
    history = [{"event": "login", "ip_address": "1.2.3.4", "success": True}]
    provider = AuthDataProvider(persistence=_FakePersistence(user, history))

    export = await provider.export("u-1")

    profile = export["profile"]
    # Credentials / second-factor secret must never be exported.
    assert "password_hash" not in profile
    assert "mfa_secret" not in profile
    # Personal data is present and JSON-safe.
    assert profile["email"] == "jane@example.com"
    assert profile["roles"] == ["user"]  # set[AuthRole] -> sorted values
    assert profile["created_at"] == "2026-01-01T00:00:00+00:00"  # datetime -> iso
    assert export["login_history"] == history


async def test_export_unknown_subject_is_empty() -> None:
    provider = AuthDataProvider(persistence=_FakePersistence(_fake_user(), []))
    assert await provider.export("does-not-exist") == {}


async def test_erase_deletes_user_and_counts() -> None:
    fake = _FakePersistence(_fake_user("u-9"), [])
    provider = AuthDataProvider(persistence=fake)

    removed = await provider.erase("u-9")

    assert removed == 1
    assert fake.deleted == ["u-9"]


async def test_erase_absent_subject_returns_zero() -> None:
    provider = AuthDataProvider(persistence=_FakePersistence(_fake_user("u-9"), []))
    assert await provider.erase("u-other") == 0


def test_provider_name_is_stable() -> None:
    # Registry keys by name; it must stay "auth".
    assert AuthDataProvider.name == "auth"


def test_provider_has_no_retention_purge() -> None:
    # Must NOT participate in time-based retention sweeps (no account auto-delete).
    assert not hasattr(AuthDataProvider, "purge_expired")

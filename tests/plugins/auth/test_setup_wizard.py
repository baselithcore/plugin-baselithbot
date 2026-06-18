"""Unit tests for the first-run setup wizard service (initial admin).

Pure logic — no database. A small fake persistence stands in for the real
``AuthPersistence`` so the fail-closed setup invariant can be exercised in
isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import pytest

from core.auth import AuthRole
from core.di.container import ServiceRegistry
from plugins.auth.config import AuthConfig
from plugins.auth.setup_service import (
    INITIAL_ADMIN_ROLES,
    SetupAlreadyCompleted,
    SetupValidationError,
    create_initial_admin,
    is_setup_needed,
)


@dataclass
class FakeUser:
    id: str
    email: str = "u@example.com"
    username: Optional[str] = None
    is_active: bool = True
    roles: Set[AuthRole] = field(default_factory=lambda: {AuthRole.USER})


class FakePersistence:
    def __init__(self, users: int = 0) -> None:
        self._users = users
        self.by_email: Dict[str, FakeUser] = {}
        self.by_username: Dict[str, FakeUser] = {}
        self.created: List[FakeUser] = []

    def count_users(self) -> int:
        return self._users

    def get_user_by_email(self, email: str) -> Optional[FakeUser]:
        return self.by_email.get(email)

    def get_user_by_username(self, username: str) -> Optional[FakeUser]:
        return self.by_username.get(username)

    def create_user(self, *, email, username=None, roles=None, **_):
        user = FakeUser(id="new", email=email, username=username, roles=set(roles or set()))
        self.created.append(user)
        self._users += 1
        return user


def _config(check_pwned: bool = False) -> AuthConfig:
    cfg = AuthConfig()
    cfg.check_pwned_passwords = check_pwned
    return cfg


# --- setup detection --------------------------------------------------------


def test_setup_needed_only_on_empty_db():
    assert is_setup_needed(FakePersistence(users=0)) is True


def test_setup_not_needed_when_any_user_exists():
    assert is_setup_needed(FakePersistence(users=1)) is False


# --- initial admin creation -------------------------------------------------


async def test_create_initial_admin_success():
    persistence = FakePersistence(users=0)
    ServiceRegistry.register(AuthConfig, _config())  # password validator reads it from DI
    user = await create_initial_admin(
        persistence,
        _config(),
        email="Root@Example.com",
        password="Sup3r-Str0ng-Pw!9",
        username="superadmin",
    )
    assert user.roles == set(INITIAL_ADMIN_ROLES)
    assert AuthRole.ADMIN in user.roles
    assert not hasattr(AuthRole, "SUPERUSER")  # superuser tier removed
    assert user.email == "root@example.com"  # normalized lower-case
    assert user.username == "superadmin"


async def test_create_initial_admin_fail_closed_when_populated():
    persistence = FakePersistence(users=1)
    with pytest.raises(SetupAlreadyCompleted):
        await create_initial_admin(
            persistence, _config(), email="x@y.io", password="Sup3r-Str0ng-Pw!9"
        )


async def test_create_initial_admin_rejects_bad_email():
    persistence = FakePersistence(users=0)
    ServiceRegistry.register(AuthConfig, _config())
    with pytest.raises(SetupValidationError):
        await create_initial_admin(
            persistence, _config(), email="not-an-email", password="Sup3r-Str0ng-Pw!9"
        )

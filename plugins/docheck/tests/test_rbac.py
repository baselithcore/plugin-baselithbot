"""RBAC permission enforcement tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from docheck.api.deps import require
from docheck.core.security import Principal
from docheck.db.models import Base, Permission, Role, User, UserRole


@pytest.fixture
async def session() -> AsyncSession:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(eng, expire_on_commit=False)() as s:
        s.add(Role(id="reader", label="Reader"))
        s.add(Role(id="admin", label="Admin"))
        s.add(User(id="u1", email="r@example.com", display_name="r"))
        s.add(User(id="u2", email="a@example.com", display_name="a"))
        s.add(UserRole(user_id="u1", role_id="reader"))
        s.add(UserRole(user_id="u2", role_id="admin"))
        s.add(Permission(role_id="reader", resource="document", action="read"))
        s.add(Permission(role_id="admin", resource="document", action="read"))
        s.add(Permission(role_id="admin", resource="document", action="write"))
        await s.commit()
        yield s


async def _check(db: AsyncSession, principal: Principal, resource: str, action: str) -> bool:
    from fastapi import HTTPException

    dep = require(resource, action)
    try:
        await dep(principal=principal, db=db)
        return True
    except HTTPException:
        return False


async def test_reader_can_read_document(session: AsyncSession) -> None:
    p = Principal(user_id="u1", email="r@example.com", roles=frozenset({"reader"}))
    assert await _check(session, p, "document", "read") is True


async def test_reader_cannot_write_document(session: AsyncSession) -> None:
    p = Principal(user_id="u1", email="r@example.com", roles=frozenset({"reader"}))
    assert await _check(session, p, "document", "write") is False


async def test_admin_can_write(session: AsyncSession) -> None:
    p = Principal(user_id="u2", email="a@example.com", roles=frozenset({"admin"}))
    assert await _check(session, p, "document", "write") is True


async def test_no_roles_denies_all(session: AsyncSession) -> None:
    p = Principal(user_id="u3", email="x@example.com", roles=frozenset())
    assert await _check(session, p, "document", "read") is False

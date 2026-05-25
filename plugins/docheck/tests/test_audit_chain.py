"""Audit hash chain integrity tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from docheck.db.models import Base
from docheck.services.audit import append_audit, verify_chain


@pytest.fixture
async def session() -> AsyncSession:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(eng, expire_on_commit=False)() as s:
        yield s


async def test_chain_appends_and_verifies(session: AsyncSession) -> None:
    await append_audit(session, action="login", user_id="u1", resource=None, payload={"ip": "127.0.0.1"})
    await append_audit(session, action="upload", user_id="u1", resource="document:doc-abc", payload={"size": 1024})
    await append_audit(session, action="analyze", user_id="u1", resource="document:doc-abc", payload={"score": 78})

    ok, broken = await verify_chain(session)
    assert ok is True
    assert broken is None

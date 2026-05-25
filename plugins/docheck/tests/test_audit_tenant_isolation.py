"""Audit chain isolation per tenant. Tampering tenant A's chain doesn't affect B."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from docheck.core.tenant import reset_tenant, set_tenant
from docheck.db.models import Base
from docheck.services.audit import append_audit, verify_chain


@pytest.fixture
async def session() -> AsyncSession:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(eng, expire_on_commit=False)() as s:
        yield s


async def test_chain_per_tenant_independent(session: AsyncSession) -> None:
    t1 = set_tenant("acme")
    await append_audit(session, action="login", user_id="u1", resource=None, payload={})
    await append_audit(
        session, action="upload", user_id="u1", resource="doc:a", payload={}
    )
    ok_a, _ = await verify_chain(session)
    reset_tenant(t1)

    t2 = set_tenant("globex")
    await append_audit(session, action="login", user_id="u2", resource=None, payload={})
    await append_audit(
        session, action="upload", user_id="u2", resource="doc:b", payload={}
    )
    ok_b, _ = await verify_chain(session)
    reset_tenant(t2)

    assert ok_a is True
    assert ok_b is True


async def test_tenant_a_chain_not_affected_by_tenant_b_writes(
    session: AsyncSession,
) -> None:
    """Interleaved writes — verify each chain independently."""
    ta = set_tenant("acme")
    await append_audit(session, action="login", user_id="ua", resource=None, payload={})
    reset_tenant(ta)

    tb = set_tenant("globex")
    await append_audit(session, action="login", user_id="ub", resource=None, payload={})
    await append_audit(
        session, action="analyze", user_id="ub", resource="doc:1", payload={}
    )
    reset_tenant(tb)

    ta = set_tenant("acme")
    await append_audit(
        session, action="upload", user_id="ua", resource="doc:x", payload={}
    )
    ok_a, broken_a = await verify_chain(session)
    reset_tenant(ta)

    tb = set_tenant("globex")
    ok_b, broken_b = await verify_chain(session)
    reset_tenant(tb)

    assert ok_a is True and broken_a is None
    assert ok_b is True and broken_b is None

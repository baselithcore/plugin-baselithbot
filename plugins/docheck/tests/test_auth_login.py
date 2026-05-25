"""Auth login flow integration tests."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from docheck.core.security import hash_password
from docheck.db.models import Base, Permission, Role, User, UserRole


@pytest.fixture
async def app_with_user(monkeypatch, tmp_path):
    db_path = tmp_path / "auth.db"
    monkeypatch.setenv("DOCHECK_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCHECK_STORAGE_ROOT", str(tmp_path))

    # Force reload settings/engine to honor monkeypatched env
    import importlib

    from docheck.core import config as cfg_mod

    importlib.reload(cfg_mod)
    from docheck.db import session as sess_mod

    importlib.reload(sess_mod)

    eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(eng, expire_on_commit=False)() as db:
        db.add(Role(id="admin", label="Admin"))
        db.add(Permission(role_id="admin", resource="document", action="read"))
        uid = f"u-{uuid.uuid4().hex[:8]}"
        db.add(
            User(
                id=uid,
                email="admin@test.local",
                display_name="admin",
                pw_hash=hash_password("S3curePassw0rd!"),
            )
        )
        db.add(UserRole(user_id=uid, role_id="admin"))
        await db.commit()

    from docheck.main import app

    return app, uid


async def test_login_success_and_me(app_with_user) -> None:
    app, uid = app_with_user
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.local",
                "password": "S3curePassw0rd!",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == uid
        assert "admin" in data["roles"]
        token = data["token"]

        me = await c.get("/api/v1/auth/me", headers={"X-User-Id": token})
        assert me.status_code == 200
        assert me.json()["email"] == "admin@test.local"


async def test_login_wrong_password_rejects(app_with_user) -> None:
    app, _ = app_with_user
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.local",
                "password": "wrong",
            },
        )
        assert res.status_code == 401


async def test_me_without_header_rejects(app_with_user) -> None:
    app, _ = app_with_user
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.get("/api/v1/auth/me")
        assert res.status_code == 401

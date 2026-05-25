"""System endpoints + change-password integration tests."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from docheck.core.security import hash_password
from docheck.db.models import Base, Permission, Role, User, UserRole


@pytest.fixture
async def app_with_admin(monkeypatch, tmp_path):
    db_path = tmp_path / "system.db"
    monkeypatch.setenv("DOCHECK_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCHECK_STORAGE_ROOT", str(tmp_path))

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
        for resource, action in [
            ("system", "read"),
            ("system", "admin"),
            ("audit", "read"),
            ("document", "read"),
        ]:
            db.add(Permission(role_id="admin", resource=resource, action=action))
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


async def test_runtime_info(app_with_admin) -> None:
    app, uid = app_with_admin
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.get("/api/v1/system/runtime", headers={"X-User-Id": uid})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["app_name"]
        assert data["llm_primary_model"]
        assert data["embedding_model"]
        assert isinstance(data["multitenant_enabled"], bool)
        assert data["retention_default_days"] >= 1


async def test_storage_stats(app_with_admin) -> None:
    app, uid = app_with_admin
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.get("/api/v1/system/storage", headers={"X-User-Id": uid})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["users"] >= 1
        assert "db_path" in data
        assert data["db_size_bytes"] >= 0


async def test_retention_get_set(app_with_admin) -> None:
    app, uid = app_with_admin
    h = {"X-User-Id": uid, "Content-Type": "application/json"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r1 = await c.get("/api/v1/system/retention", headers=h)
        assert r1.status_code == 200
        assert r1.json()["source"] == "config"

        r2 = await c.put("/api/v1/system/retention", json={"days": 90}, headers=h)
        assert r2.status_code == 200, r2.text
        assert r2.json() == {"days": 90, "source": "override"}

        r3 = await c.get("/api/v1/system/retention", headers=h)
        assert r3.json() == {"days": 90, "source": "override"}


async def test_retention_validation(app_with_admin) -> None:
    app, uid = app_with_admin
    h = {"X-User-Id": uid, "Content-Type": "application/json"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.put("/api/v1/system/retention", json={"days": 0}, headers=h)
        assert r.status_code == 422


async def test_cache_state_and_reset(app_with_admin) -> None:
    app, uid = app_with_admin
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r1 = await c.get("/api/v1/system/cache", headers={"X-User-Id": uid})
        assert r1.status_code == 200
        assert "metrics" in r1.json()

        r2 = await c.post("/api/v1/system/cache/reset", headers={"X-User-Id": uid})
        assert r2.status_code == 200
        assert r2.json()["ok"] is True


async def test_change_password_flow(app_with_admin) -> None:
    app, uid = app_with_admin
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        # wrong current
        bad = await c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "nope", "new_password": "NewPassw0rd!"},
            headers={"X-User-Id": uid},
        )
        assert bad.status_code == 401

        # too short
        short = await c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "S3curePassw0rd!", "new_password": "short"},
            headers={"X-User-Id": uid},
        )
        assert short.status_code == 422

        # success
        ok = await c.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "S3curePassw0rd!",
                "new_password": "NewPassw0rd!",
            },
            headers={"X-User-Id": uid},
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["ok"] is True

        # login with new password
        login = await c.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.local", "password": "NewPassw0rd!"},
        )
        assert login.status_code == 200

        # old password fails
        old = await c.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.local", "password": "S3curePassw0rd!"},
        )
        assert old.status_code == 401


async def test_system_requires_permission(monkeypatch, tmp_path) -> None:
    """User without `system:read` gets 403."""
    db_path = tmp_path / "rbac.db"
    monkeypatch.setenv("DOCHECK_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCHECK_STORAGE_ROOT", str(tmp_path))

    import importlib

    from docheck.core import config as cfg_mod

    importlib.reload(cfg_mod)
    from docheck.db import session as sess_mod

    importlib.reload(sess_mod)

    eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(eng, expire_on_commit=False)() as db:
        db.add(Role(id="reader", label="Reader"))
        # no system permission
        uid = f"u-{uuid.uuid4().hex[:8]}"
        db.add(
            User(
                id=uid,
                email="r@test.local",
                display_name="r",
                pw_hash=hash_password("xxxxxxxx"),
            )
        )
        db.add(UserRole(user_id=uid, role_id="reader"))
        await db.commit()

    from docheck.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.get("/api/v1/system/runtime", headers={"X-User-Id": uid})
        assert res.status_code == 403

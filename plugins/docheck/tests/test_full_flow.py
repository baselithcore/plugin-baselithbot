"""End-to-end integration: login → upload → analyze → audit chain intact."""

import io
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from docheck.core.security import hash_password
from docheck.db.models import Base, Permission, Role, User, UserRole


@pytest.fixture
async def app_with_admin(tmp_path, monkeypatch):
    db_path = tmp_path / "flow.db"
    monkeypatch.setenv("DOCHECK_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCHECK_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("DOCHECK_AUDIT_SIGNING_KEY_PATH", str(tmp_path / "audit.key"))

    import importlib

    from docheck.core import config

    importlib.reload(config)
    from docheck.db import session as sess_mod

    importlib.reload(sess_mod)

    eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(eng, expire_on_commit=False)() as db:
        db.add(Role(id="admin", label="Admin"))
        for action in ("read", "write"):
            db.add(Permission(role_id="admin", resource="document", action=action))
        db.add(Permission(role_id="admin", resource="audit", action="read"))
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


async def test_login_upload_analyze_audit(app_with_admin) -> None:
    app, _uid = app_with_admin

    canned_legal = {"findings": []}
    canned_synth = {"score": 100, "summary": "ok", "by_severity": {}, "top_risks": []}
    canned_struct = {"structure": []}
    canned_pii = {"verified": [], "rejected": []}

    def llm_router(*, system: str, **_):
        s = system.lower()
        if "structure extractor" in s:
            return canned_struct
        if "legal compliance" in s:
            return canned_legal
        if "pii verification" in s:
            return canned_pii
        if "report synthesizer" in s:
            return canned_synth
        return {}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        login = await c.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.local",
                "password": "S3curePassw0rd!",
            },
        )
        assert login.status_code == 200
        token = login.json()["token"]
        headers = {"X-User-Id": token}

        files = {
            "file": ("test.md", io.BytesIO(b"# Sample\nContenuto."), "text/markdown")
        }
        up = await c.post("/api/v1/documents", headers=headers, files=files)
        assert up.status_code == 200
        doc_id = up.json()["id"]

        with patch("docheck.services.llm.chat_json", side_effect=llm_router):
            an = await c.post(
                f"/api/v1/documents/{doc_id}/analyze",
                headers={**headers, "Content-Type": "application/json"},
                json={"policies": ["IT_GDPR_2026"]},
            )
        assert an.status_code == 200
        report = an.json()
        assert report["doc_id"] == doc_id
        assert report["signature"].startswith("ed25519:")

        verify = await c.get("/api/v1/audit/verify", headers=headers)
        assert verify.status_code == 200
        chain = verify.json()
        assert chain["ok"] is True
        assert chain["total_entries"] >= 3  # login + upload + analyze

"""End-to-end test del router embed (mig 017).

Coperture:

- Admin CRUD via JWT bearer (create / list / patch / delete / rotate).
- Public ``/api/embed/config`` happy + origin guard (missing/wrong/disabled).
- CORS preflight su ``/api/embed/*`` ritorna ACAO=*. Preflight su altri
  path mantiene il comportamento del CORSMiddleware statico
  (no cross-pollination).
- Token rotation invalida il vecchio plaintext.

Pattern Postgres-live (skip module-wide se DB irraggiungibile).
"""

from __future__ import annotations

import os
import secrets

import pytest


def _build_pg_url() -> str:
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return explicit
    user = os.getenv("POSTGRES_USER", "llm_wiki")
    password = os.getenv("POSTGRES_PASSWORD", "llm_wiki_dev")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "llm_wiki")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


_pg_url = _build_pg_url()


def _pg_reachable() -> bool:
    try:
        import psycopg

        with psycopg.connect(_pg_url, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_reachable(),
    reason="Postgres non raggiungibile — `docker compose up -d postgres` per abilitare",
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    monkeypatch.setenv("SECRET_KEY", "test-secret-key-min-32-bytes-long-yes")
    monkeypatch.setenv("POSTGRES_ENABLED", "true")

    import llm_wiki.config as cfg

    importlib.reload(cfg)


@pytest.fixture
def admin_setup():
    """Crea tenant + admin con ruolo ``superuser`` (permessi pieni).
    Ritorna ``{user, tenant_id, bearer}`` e ripulisce a fine test."""
    from llm_wiki.auth.tokens import issue_access_token
    from llm_wiki.db.roles import assign_role_to_user, list_roles
    from llm_wiki.db.tenants import create_tenant_with_owner, delete_tenant
    from llm_wiki.db.users import hash_password

    suffix = secrets.token_hex(4)
    res = create_tenant_with_owner(
        tenant_name=f"Embed E2E {suffix}",
        tenant_slug=f"e2e-{suffix}",
        user_email=f"e2e-{suffix}@local.test",
        user_password_hash=hash_password("Test-Pass-123!"),
        user_display_name="E2E Admin",
        plan="free",
        role="admin",
    )
    user = res["user"]
    tid = user["tenant_id"]

    su = next((r for r in list_roles() if r["slug"] == "superuser"), None)
    assert su is not None, "ruolo system 'superuser' non seedato"
    assign_role_to_user(user["id"], su["id"], granted_by=user["id"])

    bearer, _ = issue_access_token(user_id=user["id"], tenant_id=tid, role="admin")
    yield {"user": user, "tenant_id": tid, "bearer": bearer}

    try:
        delete_tenant(tid)
    except Exception:
        pass


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    import main

    return TestClient(main.app)


def _create_embed(client, bearer: str, **overrides) -> dict:
    body = {
        "slug": f"e2e-{secrets.token_hex(3)}",
        "name": "E2E Widget",
        "origin_allowlist": ["https://e2e.test"],
    }
    body.update(overrides)
    r = client.post(
        "/api/admin/embeds",
        headers={"Authorization": f"Bearer {bearer}"},
        json=body,
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- Admin CRUD -----------------------------------------------------------


def test_admin_create_returns_token_plaintext(admin_setup, client) -> None:
    created = _create_embed(client, admin_setup["bearer"])
    assert created["embed_token"].startswith("emb_")
    assert "token_hash" not in created
    assert created["origin_allowlist"] == ["https://e2e.test"]


def test_admin_list_filtered_to_tenant(admin_setup, client) -> None:
    _create_embed(client, admin_setup["bearer"])
    r = client.get(
        "/api/admin/embeds",
        headers={"Authorization": f"Bearer {admin_setup['bearer']}"},
    )
    assert r.status_code == 200
    rows = r.json()
    assert all(row["tenant_id"] == admin_setup["tenant_id"] for row in rows)


def test_admin_patch_and_disable(admin_setup, client) -> None:
    created = _create_embed(client, admin_setup["bearer"])
    r = client.patch(
        f"/api/admin/embeds/{created['id']}",
        headers={"Authorization": f"Bearer {admin_setup['bearer']}"},
        json={"welcome_message": "Aggiornato", "is_enabled": False},
    )
    assert r.status_code == 200
    assert r.json()["welcome_message"] == "Aggiornato"
    assert r.json()["is_enabled"] is False


def test_admin_delete(admin_setup, client) -> None:
    created = _create_embed(client, admin_setup["bearer"])
    r = client.delete(
        f"/api/admin/embeds/{created['id']}",
        headers={"Authorization": f"Bearer {admin_setup['bearer']}"},
    )
    assert r.status_code == 200
    assert r.json()["removed"] is True


# --- Public config + origin guard ----------------------------------------


def test_public_config_happy_path(admin_setup, client) -> None:
    created = _create_embed(client, admin_setup["bearer"])
    r = client.post(
        "/api/embed/config",
        headers={"Origin": "https://e2e.test"},
        json={"embed_token": created["embed_token"]},
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["embed_id"] == created["id"]
    assert payload["name"] == created["name"]


def test_public_config_missing_origin_401(admin_setup, client) -> None:
    created = _create_embed(client, admin_setup["bearer"])
    r = client.post("/api/embed/config", json={"embed_token": created["embed_token"]})
    assert r.status_code == 401


def test_public_config_wrong_origin_401(admin_setup, client) -> None:
    created = _create_embed(client, admin_setup["bearer"])
    r = client.post(
        "/api/embed/config",
        headers={"Origin": "https://evil.test"},
        json={"embed_token": created["embed_token"]},
    )
    assert r.status_code == 401


def test_public_config_disabled_embed_401(admin_setup, client) -> None:
    created = _create_embed(client, admin_setup["bearer"])
    client.patch(
        f"/api/admin/embeds/{created['id']}",
        headers={"Authorization": f"Bearer {admin_setup['bearer']}"},
        json={"is_enabled": False},
    )
    r = client.post(
        "/api/embed/config",
        headers={"Origin": "https://e2e.test"},
        json={"embed_token": created["embed_token"]},
    )
    assert r.status_code == 401


# --- Token rotation -------------------------------------------------------


def test_rotate_invalidates_old_token(admin_setup, client) -> None:
    created = _create_embed(client, admin_setup["bearer"])
    old = created["embed_token"]
    r = client.post(
        f"/api/admin/embeds/{created['id']}/rotate-token",
        headers={"Authorization": f"Bearer {admin_setup['bearer']}"},
    )
    assert r.status_code == 200
    new = r.json()["embed_token"]
    assert new != old

    # Old token rejected.
    r = client.post(
        "/api/embed/config",
        headers={"Origin": "https://e2e.test"},
        json={"embed_token": old},
    )
    assert r.status_code == 401

    # New token accepted.
    r = client.post(
        "/api/embed/config",
        headers={"Origin": "https://e2e.test"},
        json={"embed_token": new},
    )
    assert r.status_code == 200


# --- CORS preflight -------------------------------------------------------


def test_cors_preflight_embed_path_returns_204_acao_star(admin_setup, client) -> None:
    r = client.options(
        "/api/embed/chat",
        headers={
            "Origin": "https://acme.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 204
    assert r.headers.get("access-control-allow-origin") == "*"
    methods = r.headers.get("access-control-allow-methods", "")
    assert "POST" in methods
    assert "OPTIONS" in methods


def test_cors_preflight_non_embed_path_unaffected(admin_setup, client) -> None:
    """Sanity: lo static CORSMiddleware deve continuare a gestire i path
    non-embed (es. ``/api/wiki``). EmbedCORS NON deve catturare preflight
    fuori dal prefisso."""
    r = client.options(
        "/api/wiki",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Static CORSMiddleware permette localhost:5173 → preflight 200 con ACAO echo.
    assert r.headers.get("access-control-allow-origin") in (
        "http://localhost:5173",
        "*",
    )


# --- Admin gating ---------------------------------------------------------


def test_admin_without_bearer_blocked(client) -> None:
    """``_AdminGateMiddleware`` rifiuta richieste non-loopback senza
    bearer prima ancora di arrivare al ``require_permission`` (403).
    Con bearer valido la chain prosegue normalmente — vedi
    :func:`test_admin_create_returns_token_plaintext`. Senza bearer
    valido (Bearer assente) e con TestClient (non-loopback) il gate
    chiude con 403, per design defense-in-depth."""
    r = client.get("/api/admin/embeds")
    assert r.status_code in (401, 403)


def test_admin_with_invalid_bearer_blocked(client) -> None:
    r = client.get(
        "/api/admin/embeds",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert r.status_code in (401, 403)

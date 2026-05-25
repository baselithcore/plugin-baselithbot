"""Integration test embeds (mig 017) con Postgres live.

Skip module-wide se Postgres non raggiungibile (stesso pattern di
:mod:`tests.test_groups_db` / :mod:`tests.test_rbac_db`).

Coverage
========

- ``create_embed`` ritorna plaintext UNA volta + record senza hash.
- ``verify_token`` cattura match esatto / origin in allowlist.
- ``verify_token`` reject: token errato, origin mancante, allowlist vuota.
- ``rotate_token`` invalida il vecchio plaintext.
- ``update_embed`` PATCH parziale (theme/welcome/allowlist).
- ``delete_embed`` cross-tenant guard.
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


def _make_tenant() -> dict:
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import hash_password

    suffix = secrets.token_hex(6)
    result = create_tenant_with_owner(
        tenant_name=f"Embed Test {suffix}",
        tenant_slug=f"emb-{suffix}",
        user_email=f"emb-{suffix}@local.test",
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
        user_display_name="Embed Test User",
        plan="free",
        role="user",
    )
    return {"user": result["user"], "tenant_id": result["user"]["tenant_id"]}


@pytest.fixture
def tenant_a():
    from llm_wiki.db.tenants import delete_tenant

    data = _make_tenant()
    yield data
    try:
        delete_tenant(data["tenant_id"])
    except Exception:
        pass


@pytest.fixture
def tenant_b():
    from llm_wiki.db.tenants import delete_tenant

    data = _make_tenant()
    yield data
    try:
        delete_tenant(data["tenant_id"])
    except Exception:
        pass


# --- CRUD -----------------------------------------------------------------


def test_create_returns_plaintext_once(tenant_a: dict) -> None:
    from llm_wiki.db.embeds import create_embed

    record, plaintext = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme widget",
        origin_allowlist=["https://acme.test"],
        welcome_message="Ciao!",
    )
    assert plaintext.startswith("emb_")
    assert len(plaintext) == 4 + 64
    assert record["slug"] == "acme"
    assert record["origin_allowlist"] == ["https://acme.test"]
    assert "token_hash" not in record


def test_list_get_update(tenant_a: dict) -> None:
    from llm_wiki.db.embeds import create_embed, get_embed_by_id, list_embeds, update_embed

    record, _ = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme widget",
        origin_allowlist=["https://acme.test"],
    )
    rows = list_embeds(tenant_a["tenant_id"])
    assert any(r["id"] == record["id"] for r in rows)

    fetched = get_embed_by_id(record["id"], tenant_a["tenant_id"])
    assert fetched is not None
    assert fetched["slug"] == "acme"

    updated = update_embed(
        record["id"],
        tenant_a["tenant_id"],
        welcome_message="Aggiornato",
        theme={"primary": "#ff0000"},
    )
    assert updated is not None
    assert updated["welcome_message"] == "Aggiornato"
    assert updated["theme"]["primary"] == "#ff0000"


# --- verify_token --------------------------------------------------------


def test_verify_token_happy_path(tenant_a: dict) -> None:
    from llm_wiki.db.embeds import create_embed, verify_token

    _, plaintext = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme",
        origin_allowlist=["https://acme.test", "https://staging.acme.test"],
    )

    result = verify_token(plaintext, origin="https://acme.test")
    assert result is not None
    assert result["slug"] == "acme"

    result = verify_token(plaintext, origin="https://staging.acme.test")
    assert result is not None


def test_verify_token_rejects_wrong_origin(tenant_a: dict) -> None:
    from llm_wiki.db.embeds import create_embed, verify_token

    _, plaintext = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme",
        origin_allowlist=["https://acme.test"],
    )
    assert verify_token(plaintext, origin="https://evil.test") is None


def test_verify_token_rejects_missing_origin(tenant_a: dict) -> None:
    from llm_wiki.db.embeds import create_embed, verify_token

    _, plaintext = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme",
        origin_allowlist=["https://acme.test"],
    )
    assert verify_token(plaintext, origin=None) is None
    assert verify_token(plaintext, origin="") is None


def test_verify_token_rejects_empty_allowlist(tenant_a: dict) -> None:
    """Allowlist vuota = deny-by-default. Admin DEVE configurare i siti
    autorizzati esplicitamente."""
    from llm_wiki.db.embeds import create_embed, verify_token

    _, plaintext = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme",
        origin_allowlist=[],
    )
    assert verify_token(plaintext, origin="https://acme.test") is None


def test_verify_token_rejects_disabled(tenant_a: dict) -> None:
    from llm_wiki.db.embeds import create_embed, update_embed, verify_token

    record, plaintext = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme",
        origin_allowlist=["https://acme.test"],
    )
    update_embed(record["id"], tenant_a["tenant_id"], is_enabled=False)
    assert verify_token(plaintext, origin="https://acme.test") is None


def test_verify_token_invalid_plaintext(tenant_a: dict) -> None:
    from llm_wiki.db.embeds import verify_token

    assert verify_token("not-a-token", origin="https://x.test") is None
    assert verify_token("emb_deadbeef", origin="https://x.test") is None
    assert verify_token("", origin="https://x.test") is None


# --- rotate ---------------------------------------------------------------


def test_rotate_token_invalidates_old(tenant_a: dict) -> None:
    from llm_wiki.db.embeds import create_embed, rotate_token, verify_token

    record, old = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme",
        origin_allowlist=["https://acme.test"],
    )
    rotated = rotate_token(record["id"], tenant_a["tenant_id"])
    assert rotated is not None
    _, new = rotated
    assert new != old
    assert verify_token(old, origin="https://acme.test") is None
    assert verify_token(new, origin="https://acme.test") is not None


# --- cross-tenant guard ---------------------------------------------------


def test_get_embed_cross_tenant_returns_none(tenant_a: dict, tenant_b: dict) -> None:
    from llm_wiki.db.embeds import create_embed, get_embed_by_id

    record, _ = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme",
        origin_allowlist=["https://acme.test"],
    )
    # tenant_b non vede embed di tenant_a.
    assert get_embed_by_id(record["id"], tenant_b["tenant_id"]) is None
    # Stesso lookup col tenant giusto funziona.
    assert get_embed_by_id(record["id"], tenant_a["tenant_id"]) is not None


def test_delete_embed_cross_tenant_no_op(tenant_a: dict, tenant_b: dict) -> None:
    from llm_wiki.db.embeds import create_embed, delete_embed, get_embed_by_id

    record, _ = create_embed(
        tenant_id=tenant_a["tenant_id"],
        slug="acme",
        name="Acme",
        origin_allowlist=["https://acme.test"],
    )
    # Tentativo cross-tenant: il DELETE non rimuove nulla.
    assert delete_embed(record["id"], tenant_b["tenant_id"]) is False
    assert get_embed_by_id(record["id"], tenant_a["tenant_id"]) is not None

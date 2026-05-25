"""Integration tests auth — richiedono Postgres live.

Skip automatico se ``DATABASE_URL`` (o ``POSTGRES_HOST``) non risolve a
un'istanza raggiungibile, così la suite full su sviluppatore senza
docker non rompe — basta avere ``docker compose up -d postgres`` per
abilitarli.

Coverage
========

- ``create_tenant_with_owner`` atomica + UNIQUE 1:1
- email duplicata → IntegrityError → tenant non creato
- ``hash_password``+``verify_password`` round-trip via DB
- ``issue_refresh_token`` + ``rotate_refresh_token`` rotation chain
- replay detection: revoca FAMILY su double-use
- ``revoke_all_for_user`` logout-everywhere
- ``count_users`` first-boot detect
- TenantContext GUC + RLS basic isolation (con ruolo superuser bypass
  abbiamo solo lo smoke; RLS hard testato in CI con ruolo app_runtime)

Setup
=====

Prima di runnare:

    docker compose up -d postgres
    alembic upgrade head
    pytest tests/test_auth_db.py -v
"""

from __future__ import annotations

import os
import secrets
import uuid

import pytest


# Skip module-wide se Postgres non disponibile. Tenta SEMPRE il default
# locale (postgres su 5433 da docker-compose) anche senza env var
# esplicite — così basta avere il container up per abilitare i test.
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
def _setup_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """SECRET_KEY + reload config/tokens per test che firmano JWT."""
    import importlib

    monkeypatch.setenv("SECRET_KEY", "test-secret-key-min-32-bytes-long-yes")
    monkeypatch.setenv("POSTGRES_ENABLED", "true")

    import llm_wiki.config as cfg

    importlib.reload(cfg)


@pytest.fixture
def fresh_email() -> str:
    """Email unica per test (parallel-safe)."""
    return f"test-{secrets.token_hex(8)}@local.test"


@pytest.fixture
def fresh_slug() -> str:
    return f"t-{secrets.token_hex(6)}"


@pytest.fixture
def cleanup_users() -> list[str]:
    """Tracker user_id da cancellare a fine test (CASCADE pulisce tenant + tokens)."""
    created: list[str] = []
    yield created
    # Teardown: drop tutti i tenant (CASCADE → users + refresh_tokens + ...).
    if not created:
        return
    from llm_wiki.db.tenants import delete_tenant
    from llm_wiki.db.users import get_user_by_id

    for uid in created:
        u = get_user_by_id(uid)
        if u and u.get("tenant_id"):
            try:
                delete_tenant(u["tenant_id"])
            except Exception:
                pass


# --- tenant + user creation ------------------------------------------------


def test_create_tenant_with_owner_atomic(
    fresh_email: str, fresh_slug: str, cleanup_users: list[str]
) -> None:
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import hash_password

    result = create_tenant_with_owner(
        tenant_name="Test Workspace",
        tenant_slug=fresh_slug,
        user_email=fresh_email,
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
        user_display_name="Test User",
        plan="free",
        role="user",
    )
    cleanup_users.append(result["user"]["id"])

    assert result["tenant"]["slug"] == fresh_slug
    assert result["user"]["email"] == fresh_email
    assert result["user"]["role"] == "user"
    assert result["user"]["tenant_id"] == result["tenant"]["id"]


def test_duplicate_email_rolls_back_tenant(fresh_email: str, cleanup_users: list[str]) -> None:
    """Crea due volte la stessa email → seconda call solleva, NESSUN
    tenant orfano."""
    import psycopg

    from llm_wiki.db.tenants import create_tenant_with_owner, get_tenant_by_slug
    from llm_wiki.db.users import hash_password

    pw = hash_password("S3cur3-Test-Pass!")
    first = create_tenant_with_owner(
        tenant_name="A",
        tenant_slug=f"a-{secrets.token_hex(4)}",
        user_email=fresh_email,
        user_password_hash=pw,
    )
    cleanup_users.append(first["user"]["id"])

    dup_slug = f"b-{secrets.token_hex(4)}"
    with pytest.raises(psycopg.errors.UniqueViolation):
        create_tenant_with_owner(
            tenant_name="B",
            tenant_slug=dup_slug,
            user_email=fresh_email,  # stessa email → conflict su users.email UNIQUE
            user_password_hash=pw,
        )
    # Verifica: NESSUN tenant `dup_slug` creato (rollback funziona).
    assert get_tenant_by_slug(dup_slug) is None


def test_get_user_by_email_strips_password(fresh_email: str, cleanup_users: list[str]) -> None:
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import get_user_by_email, hash_password

    res = create_tenant_with_owner(
        tenant_name="X",
        tenant_slug=f"x-{secrets.token_hex(4)}",
        user_email=fresh_email,
        user_password_hash=hash_password("pass-12345-678"),
    )
    cleanup_users.append(res["user"]["id"])

    user = get_user_by_email(fresh_email)
    assert user is not None
    assert "password_hash" not in user
    assert user["email"] == fresh_email


def test_get_user_with_credentials_includes_hash(
    fresh_email: str, cleanup_users: list[str]
) -> None:
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import (
        get_user_by_email_with_credentials,
        hash_password,
        verify_password,
    )

    res = create_tenant_with_owner(
        tenant_name="X",
        tenant_slug=f"x-{secrets.token_hex(4)}",
        user_email=fresh_email,
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
    )
    cleanup_users.append(res["user"]["id"])

    full = get_user_by_email_with_credentials(fresh_email)
    assert full is not None
    assert "password_hash" in full
    assert verify_password(full["password_hash"], "S3cur3-Test-Pass!")
    assert not verify_password(full["password_hash"], "wrong")


# --- refresh token rotation + replay --------------------------------------


def test_refresh_token_rotation_chain(fresh_email: str, cleanup_users: list[str]) -> None:
    """Issue → rotate → vecchio replay revoca family."""
    from llm_wiki.auth.tokens import (
        TokenError,
        issue_refresh_token,
        rotate_refresh_token,
    )
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import hash_password

    res = create_tenant_with_owner(
        tenant_name="R",
        tenant_slug=f"r-{secrets.token_hex(4)}",
        user_email=fresh_email,
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
    )
    cleanup_users.append(res["user"]["id"])
    user_id = res["user"]["id"]
    tenant_id = res["tenant"]["id"]

    token1, _exp, family1 = issue_refresh_token(user_id=user_id, tenant_id=tenant_id)
    out1 = rotate_refresh_token(token1)
    assert out1["user_id"] == user_id
    assert out1["tenant_id"] == tenant_id
    token2 = out1["refresh_token"]

    # Rotation chain: token2 valido, token1 revocato.
    with pytest.raises(TokenError, match="replay"):
        rotate_refresh_token(token1)

    # Family revocata → token2 ora non più rotabile.
    with pytest.raises(TokenError):
        rotate_refresh_token(token2)


def test_revoke_all_for_user(fresh_email: str, cleanup_users: list[str]) -> None:
    from llm_wiki.auth.tokens import (
        TokenError,
        issue_refresh_token,
        revoke_all_for_user,
        rotate_refresh_token,
    )
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import hash_password

    res = create_tenant_with_owner(
        tenant_name="R",
        tenant_slug=f"r-{secrets.token_hex(4)}",
        user_email=fresh_email,
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
    )
    cleanup_users.append(res["user"]["id"])
    user_id = res["user"]["id"]
    tenant_id = res["tenant"]["id"]

    # 3 sessioni concorrenti (3 device).
    tokens = [issue_refresh_token(user_id=user_id, tenant_id=tenant_id)[0] for _ in range(3)]
    n = revoke_all_for_user(user_id)
    assert n == 3

    for t in tokens:
        with pytest.raises(TokenError):
            rotate_refresh_token(t)


def test_unknown_token_raises(cleanup_users: list[str]) -> None:
    from llm_wiki.auth.tokens import TokenError, rotate_refresh_token

    with pytest.raises(TokenError, match="non riconosciuto"):
        rotate_refresh_token("garbage-not-a-real-token-" + secrets.token_urlsafe(8))


# --- count_users (bootstrap detect) ---------------------------------------


def test_count_users_returns_int(cleanup_users: list[str]) -> None:
    """Bootstrap admin lifespan usa questa per first-boot detect."""
    from llm_wiki.db.users import count_users

    n = count_users()
    assert isinstance(n, int)
    assert n >= 0


# --- conversation CRUD con tenant context ----------------------------------


def test_conversation_crud_with_tenant_context(fresh_email: str, cleanup_users: list[str]) -> None:
    """End-to-end: setup tenant → contextvar → create/list/append/delete."""
    from llm_wiki.auth.tenant_context import (
        TenantInfo,
        reset_tenant,
        set_current_tenant,
    )
    from llm_wiki.db.conversations import (
        append_message,
        create_conversation,
        delete_messages_from,
        latest_turns,
        list_conversations,
        list_messages,
    )
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import hash_password

    res = create_tenant_with_owner(
        tenant_name="C",
        tenant_slug=f"c-{secrets.token_hex(4)}",
        user_email=fresh_email,
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
    )
    cleanup_users.append(res["user"]["id"])
    user_id = res["user"]["id"]
    tenant_id = res["tenant"]["id"]

    token = set_current_tenant(TenantInfo(tenant_id=tenant_id))
    try:
        conv = create_conversation(user_id=user_id, title="Test")
        assert conv["title"] == "Test"

        # Append turni
        m1 = append_message(conversation_id=conv["id"], role="user", content="Ciao")
        m2 = append_message(
            conversation_id=conv["id"],
            role="assistant",
            content="Salve!",
            sources=[{"document_id": "x", "title": "X"}],
        )
        assert m1["role"] == "user"
        assert m2["sources"] is not None

        # List
        msgs = list_messages(conversation_id=conv["id"])
        assert len(msgs) == 2

        # latest_turns ordina cronologicamente crescente
        recent = latest_turns(conversation_id=conv["id"], max_turns=4)
        assert [r["role"] for r in recent] == ["user", "assistant"]

        # User vede la propria conv via list
        my_convs = list_conversations(user_id=user_id)
        assert any(c["id"] == conv["id"] for c in my_convs)

        # Truncate da m2 (cancella solo l'assistant)
        n = delete_messages_from(conversation_id=conv["id"], from_message_id=m2["id"])
        assert n == 1
        assert len(list_messages(conversation_id=conv["id"])) == 1
    finally:
        reset_tenant(token)


def test_conversation_isolation_across_tenants(
    cleanup_users: list[str],
) -> None:
    """Smoke: tenant A non vede conv di tenant B (anche senza RLS hard,
    `list_conversations(user_id=)` filtra per user_id; il check tenant
    è nel `_ensure_owner` HTTP — qui DB-level lo deferiamo a integration
    test col ruolo `app_runtime` quando l'enforcement RLS è on)."""
    from llm_wiki.auth.tenant_context import (
        TenantInfo,
        reset_tenant,
        set_current_tenant,
    )
    from llm_wiki.db.conversations import create_conversation, list_conversations
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import hash_password

    pw = hash_password("S3cur3-Test-Pass!")
    a = create_tenant_with_owner(
        tenant_name="A",
        tenant_slug=f"a-{secrets.token_hex(4)}",
        user_email=f"a-{secrets.token_hex(4)}@local.test",
        user_password_hash=pw,
    )
    b = create_tenant_with_owner(
        tenant_name="B",
        tenant_slug=f"b-{secrets.token_hex(4)}",
        user_email=f"b-{secrets.token_hex(4)}@local.test",
        user_password_hash=pw,
    )
    cleanup_users.extend([a["user"]["id"], b["user"]["id"]])

    # Tenant A crea conv
    tok_a = set_current_tenant(TenantInfo(tenant_id=a["tenant"]["id"]))
    try:
        ca = create_conversation(user_id=a["user"]["id"], title="A's")
    finally:
        reset_tenant(tok_a)

    # Tenant B lista: NON vede la conv di A (filtro user_id).
    tok_b = set_current_tenant(TenantInfo(tenant_id=b["tenant"]["id"]))
    try:
        b_convs = list_conversations(user_id=b["user"]["id"])
        assert all(c["id"] != ca["id"] for c in b_convs)
    finally:
        reset_tenant(tok_b)


# --- audit log smoke ------------------------------------------------------


def test_audit_event_write_and_persist(
    cleanup_users: list[str],
) -> None:
    """write_event non solleva, scrive riga, query la trova."""
    from llm_wiki.auth.audit import write_event
    from llm_wiki.db.connection import get_connection

    kind = f"test.smoke.{uuid.uuid4()}"
    write_event(kind, payload={"foo": "bar"}, ip_address="127.0.0.1")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload, ip_address FROM audit_events "
                "WHERE kind = %s ORDER BY created_at DESC LIMIT 1",
                (kind,),
            )
            row = cur.fetchone()
        conn.rollback()

    assert row is not None
    payload, ip = row
    assert payload == {"foo": "bar"}
    # `INET` torna come str/IPv*Address; basta `str(ip)` per match.
    assert str(ip) == "127.0.0.1"

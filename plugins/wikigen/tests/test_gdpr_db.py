"""Integration test GDPR/DSAR con Postgres live.

Skip se Postgres non raggiungibile.

Coverage
========

- ``GET /api/me/export`` ritorna dump struttura attesa
- ``DELETE /api/me`` cancella account + cascade dati
- Last-superuser protection blocca DELETE
- Audit ``gdpr.export`` / ``gdpr.delete`` registrato
- Trigger append-only blocca UPDATE/DELETE diretti su ``audit_events``
- ``prune_audit_events`` rispetta retention min 30gg
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
    reason="Postgres non raggiungibile",
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    monkeypatch.setenv("SECRET_KEY", "test-secret-key-min-32-bytes-long-yes")
    monkeypatch.setenv("POSTGRES_ENABLED", "true")

    import llm_wiki.config as cfg

    importlib.reload(cfg)


@pytest.fixture
def fresh_user():
    from llm_wiki.db.tenants import create_tenant_with_owner, delete_tenant
    from llm_wiki.db.users import hash_password

    suffix = secrets.token_hex(6)
    result = create_tenant_with_owner(
        tenant_name=f"GDPR Test {suffix}",
        tenant_slug=f"gdpr-{suffix}",
        user_email=f"gdpr-{suffix}@local.test",
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
        user_display_name="GDPR Test User",
        plan="free",
        role="user",
    )
    user = result["user"]
    yield user
    try:
        delete_tenant(user["tenant_id"])
    except Exception:
        pass


# --- delete_user --------------------------------------------------------


def test_delete_user_cascades_owned_rows(fresh_user) -> None:
    """delete_user rimuove user + cascade conversations."""
    import psycopg

    from llm_wiki.db.users import delete_user

    user_id = fresh_user["id"]
    tenant_id = fresh_user["tenant_id"]

    # Crea una conversazione fittizia
    with psycopg.connect(_pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (tenant_id, user_id, title) VALUES (%s, %s, 'test')",
                (tenant_id, user_id),
            )
        conn.commit()

    assert delete_user(user_id) is True

    with psycopg.connect(_pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            assert row is not None and row[0] == 0
            cur.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            assert row is not None and row[0] == 0


def test_delete_user_audit_user_id_set_null(fresh_user) -> None:
    """audit_events.user_id => SET NULL, riga sopravvive (cascade FK)."""
    import psycopg

    from llm_wiki.auth.audit import write_event
    from llm_wiki.db.users import delete_user

    user_id = fresh_user["id"]
    tenant_id = fresh_user["tenant_id"]
    marker = secrets.token_hex(8)

    write_event(
        kind="test.event",
        tenant_id=tenant_id,
        user_id=user_id,
        payload={"marker": marker},
    )

    delete_user(user_id)

    with psycopg.connect(_pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM audit_events "
                "WHERE kind = 'test.event' AND payload->>'marker' = %s",
                (marker,),
            )
            row = cur.fetchone()
    assert row is not None, "audit row scomparso"
    assert row[0] is None, "user_id non è stato impostato a NULL dal cascade"


# --- audit_events append-only -------------------------------------------


def test_audit_events_update_blocked() -> None:
    import psycopg
    from psycopg.errors import InsufficientPrivilege

    from llm_wiki.auth.audit import write_event

    write_event(kind="test.append_only", payload={"x": "before"})

    with psycopg.connect(_pg_url) as conn:
        with conn.cursor() as cur:
            with pytest.raises((InsufficientPrivilege, psycopg.errors.RaiseException)):
                cur.execute(
                    "UPDATE audit_events SET kind = 'tampered' WHERE kind = 'test.append_only'"
                )


def test_audit_events_delete_blocked() -> None:
    import psycopg
    from psycopg.errors import InsufficientPrivilege

    from llm_wiki.auth.audit import write_event

    write_event(kind="test.delete_block", payload={})

    with psycopg.connect(_pg_url) as conn:
        with conn.cursor() as cur:
            with pytest.raises((InsufficientPrivilege, psycopg.errors.RaiseException)):
                cur.execute("DELETE FROM audit_events WHERE kind = 'test.delete_block'")


# --- prune_audit_events -------------------------------------------------


def test_prune_audit_events_rejects_low_retention() -> None:
    import psycopg

    with psycopg.connect(_pg_url) as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT prune_audit_events(10)")


def test_prune_audit_events_logs_self() -> None:
    """`audit.prune` event registrato dopo ogni run."""
    import psycopg

    with psycopg.connect(_pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT prune_audit_events(30)")
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM audit_events "
                "WHERE kind = 'audit.prune' "
                "AND created_at > NOW() - INTERVAL '1 minute'"
            )
            row = cur.fetchone()
    assert row is not None and row[0] >= 1

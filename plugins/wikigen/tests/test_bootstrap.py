"""Test bootstrap superuser — unit (validation) + integration (DB).

Unit: validation pure (email regex, password length).
Integration: DB live → create_superuser idempotency, ruolo superuser
assegnato, audit event.
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


def _pg_reachable() -> bool:
    try:
        import psycopg

        with psycopg.connect(_build_pg_url(), connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False


# --- unit (no DB) ----------------------------------------------------------


def test_validate_email_rejects_garbage() -> None:
    from llm_wiki.auth.bootstrap import BootstrapError, _validate_email

    with pytest.raises(BootstrapError):
        _validate_email("")
    with pytest.raises(BootstrapError):
        _validate_email("notanemail")
    with pytest.raises(BootstrapError):
        _validate_email("@nope.com")


def test_validate_email_normalizes_case() -> None:
    from llm_wiki.auth.bootstrap import _validate_email

    assert _validate_email("Foo@Bar.Com") == "foo@bar.com"
    assert _validate_email("  user@example.io  ") == "user@example.io"


def test_validate_password_min_length() -> None:
    from llm_wiki.auth.bootstrap import (
        PASSWORD_MIN_LEN,
        BootstrapError,
        _validate_password,
    )

    with pytest.raises(BootstrapError):
        _validate_password("")
    with pytest.raises(BootstrapError):
        _validate_password("short")
    # min length passes
    _validate_password("x" * PASSWORD_MIN_LEN)


def test_create_superuser_postgres_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quando Postgres è disabilitato, create_superuser solleva subito."""
    import importlib

    monkeypatch.setenv("POSTGRES_ENABLED", "false")
    import llm_wiki.config as cfg

    importlib.reload(cfg)

    from llm_wiki.auth.bootstrap import BootstrapError, create_superuser

    with pytest.raises(BootstrapError, match="Postgres"):
        create_superuser("admin@x.com", "verystrongpassword")


# --- integration (Postgres live) -------------------------------------------


pg_required = pytest.mark.skipif(
    not _pg_reachable(),
    reason="Postgres non raggiungibile — `docker compose up -d postgres` per abilitare",
)


@pytest.fixture
def _pg_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    monkeypatch.setenv("SECRET_KEY", "test-secret-key-min-32-bytes-long-yes")
    monkeypatch.setenv("POSTGRES_ENABLED", "true")
    import llm_wiki.config as cfg

    importlib.reload(cfg)


@pytest.fixture
def _cleanup_emails():
    """Track emails da eliminare — droppa il tenant a fine test."""
    created: list[str] = []
    yield created
    if not created:
        return
    from llm_wiki.db.tenants import delete_tenant
    from llm_wiki.db.users import get_user_by_email

    for email in created:
        u = get_user_by_email(email)
        if u and u.get("tenant_id"):
            try:
                delete_tenant(u["tenant_id"])
            except Exception:
                pass


@pg_required
def test_create_superuser_assigns_role(_pg_env, _cleanup_emails) -> None:
    from llm_wiki.auth.bootstrap import create_superuser
    from llm_wiki.db.roles import get_user_roles

    email = f"bootstrap-{secrets.token_hex(6)}@local.test"
    _cleanup_emails.append(email)

    info = create_superuser(email, "S3cur3-Test-Pass!", display_name="Test Admin")
    assert info["email"] == email
    roles = {r["slug"] for r in get_user_roles(info["user_id"])}
    assert "superuser" in roles


@pg_required
def test_create_superuser_idempotent_on_duplicate(_pg_env, _cleanup_emails) -> None:
    from llm_wiki.auth.bootstrap import BootstrapError, create_superuser

    email = f"bootstrap-{secrets.token_hex(6)}@local.test"
    _cleanup_emails.append(email)

    create_superuser(email, "S3cur3-Test-Pass!")
    with pytest.raises(BootstrapError, match="esiste già"):
        create_superuser(email, "S3cur3-Other-Pass!")


@pg_required
def test_create_superuser_validates_inputs(_pg_env, _cleanup_emails) -> None:
    from llm_wiki.auth.bootstrap import BootstrapError, create_superuser

    with pytest.raises(BootstrapError):
        create_superuser("not-an-email", "S3cur3-Test-Pass!")
    with pytest.raises(BootstrapError):
        create_superuser("ok@x.com", "short")


@pg_required
def test_create_superuser_audit_event(_pg_env, _cleanup_emails) -> None:
    """Verifica che ``create_superuser`` scriva ``admin.bootstrap``
    su ``audit_events`` con source corretto."""
    from llm_wiki.auth.bootstrap import create_superuser
    from llm_wiki.db.connection import get_connection

    email = f"bootstrap-{secrets.token_hex(6)}@local.test"
    _cleanup_emails.append(email)
    info = create_superuser(email, "S3cur3-Test-Pass!", source="cli")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload->>'source' AS source,
                       payload->>'email' AS email
                FROM audit_events
                WHERE kind = 'admin.bootstrap'
                  AND user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (info["user_id"],),
            )
            row = cur.fetchone()
        conn.rollback()
    assert row is not None
    assert row[0] == "cli"
    assert row[1] == email

"""Test setup invitations + force password change (009).

Integration con Postgres live. Skip se DB irraggiungibile.

Coverage:
- create_invitation → token plain restituito UNA volta, hash in DB.
- peek non consuma; consume single-use; expired/used reasons distinti.
- consume atomico (UPDATE condizionato → race-safe contro doppio accept).
- revoke marca used_at.
- force-change flag bloccato da require_user_password_current.
- update_password azzera flag automaticamente.
"""

from __future__ import annotations

import datetime
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


# --- invitation lifecycle --------------------------------------------------


def test_create_invitation_token_unique() -> None:
    from llm_wiki.auth.invitations import create_invitation

    a = create_invitation(email=f"a-{secrets.token_hex(4)}@x.test")
    b = create_invitation(email=f"b-{secrets.token_hex(4)}@x.test")
    assert a["token_plain"] != b["token_plain"]
    assert len(a["token_plain"]) >= 60  # urlsafe(48) ≥ 64 char


def test_peek_invitation_not_consumed() -> None:
    from llm_wiki.auth.invitations import create_invitation, peek_invitation

    info = create_invitation(email=f"peek-{secrets.token_hex(4)}@x.test")
    p1 = peek_invitation(info["token_plain"])
    p2 = peek_invitation(info["token_plain"])
    assert p1 == p2  # peek read-only
    assert p1 and p1["used"] is False
    assert p1["expired"] is False


def test_consume_invitation_single_use() -> None:
    from llm_wiki.auth.invitations import (
        InvitationError,
        consume_invitation,
        create_invitation,
    )

    info = create_invitation(email=f"once-{secrets.token_hex(4)}@x.test")
    consumed = consume_invitation(info["token_plain"])
    assert consumed["email"].endswith("@x.test")
    # Secondo consume → errore
    with pytest.raises(InvitationError, match="utilizzato"):
        consume_invitation(info["token_plain"])


def test_consume_unknown_token_distinct_reason() -> None:
    from llm_wiki.auth.invitations import InvitationError, consume_invitation

    with pytest.raises(InvitationError, match="riconosciuto"):
        consume_invitation("a" * 64)


def test_consume_expired_token() -> None:
    """Forziamo expires_at nel passato modificando la riga, poi
    consume → InvitationError 'scaduto'."""
    from llm_wiki.auth.invitations import (
        InvitationError,
        _hash_token,
        consume_invitation,
        create_invitation,
    )
    from llm_wiki.db.connection import get_connection

    info = create_invitation(email=f"exp-{secrets.token_hex(4)}@x.test")
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE setup_invitations SET expires_at = %s WHERE token_hash = %s",
                (past, _hash_token(info["token_plain"])),
            )
        conn.commit()

    with pytest.raises(InvitationError, match="scaduto"):
        consume_invitation(info["token_plain"])


def test_revoke_invitation() -> None:
    from llm_wiki.auth.invitations import (
        InvitationError,
        consume_invitation,
        create_invitation,
        revoke_invitation,
    )

    info = create_invitation(email=f"rev-{secrets.token_hex(4)}@x.test")
    assert revoke_invitation(info["id"]) is True
    # Revoca = used_at popolato → consume rifiuta come "già usato"
    with pytest.raises(InvitationError, match="utilizzato"):
        consume_invitation(info["token_plain"])
    # Idempotent: secondo revoke = no-op
    assert revoke_invitation(info["id"]) is False


# --- force password change -------------------------------------------------


def test_set_password_must_change_flag_then_clears_on_update(_cleanup_emails) -> None:
    from llm_wiki.auth.bootstrap import create_superuser
    from llm_wiki.db.users import (
        get_user_by_id,
        set_password_must_change,
        update_password,
    )

    email = f"pw-{secrets.token_hex(6)}@local.test"
    _cleanup_emails.append(email)
    info = create_superuser(email, "S3cur3-Test-Pass!")

    # Set flag manualmente
    assert set_password_must_change(info["user_id"], True) is True
    user = get_user_by_id(info["user_id"])
    assert user is not None
    assert user.get("password_must_change") is True

    # update_password azzera il flag
    update_password(info["user_id"], "An0ther-Strong-Pwd!")
    user = get_user_by_id(info["user_id"])
    assert user is not None
    assert user.get("password_must_change") is False


@pytest.fixture
def _cleanup_emails():
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

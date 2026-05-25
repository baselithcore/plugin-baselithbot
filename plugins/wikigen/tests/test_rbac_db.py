"""Integration test RBAC con Postgres live (Fase 7).

Skip module-wide se Postgres non raggiungibile — stesso pattern di
:mod:`tests.test_auth_db`.

Setup
=====

::

    docker compose up -d postgres
    alembic upgrade head
    pytest tests/test_rbac_db.py -v

Coverage
========

- Seed system roles presenti (admin/editor/viewer).
- ``assign_role_to_user`` + ``get_user_permissions`` aggregano i permessi.
- ``revoke_role_from_user`` rimuove il ruolo.
- ``user_domain_grants`` popolano ``get_user_domain_grants``.
- Backfill da ``users.role`` ha generato ``user_roles``.
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
def fresh_user():
    """Crea tenant + user e restituisce dict user. Cleanup via CASCADE."""
    from llm_wiki.db.tenants import create_tenant_with_owner, delete_tenant
    from llm_wiki.db.users import hash_password

    suffix = secrets.token_hex(6)
    result = create_tenant_with_owner(
        tenant_name=f"RBAC Test {suffix}",
        tenant_slug=f"rbac-{suffix}",
        user_email=f"rbac-{suffix}@local.test",
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
        user_display_name="RBAC Test User",
        plan="free",
        role="user",
    )
    user = result["user"]
    yield user
    try:
        delete_tenant(user["tenant_id"])
    except Exception:
        pass


# --- seed ------------------------------------------------------------------


def test_seed_system_roles_present() -> None:
    from llm_wiki.db.roles import list_roles

    rows = list_roles()
    slugs = {r["slug"] for r in rows if r["is_system"]}
    assert {"superuser", "admin", "moderator", "user"} <= slugs


def test_seed_role_permissions_superuser_full() -> None:
    """superuser deve coprire l'intero catalogo permessi."""
    from llm_wiki.auth.permissions import ALL_PERMISSIONS
    from llm_wiki.db.roles import get_role_permissions, list_roles

    su = next(r for r in list_roles() if r["slug"] == "superuser" and r["is_system"])
    perms = set(get_role_permissions(su["id"]))
    assert perms == set(ALL_PERMISSIONS)


def test_seed_role_permissions_user_subset() -> None:
    """``user`` ha permessi di sola lettura/uso, niente write/admin."""
    from llm_wiki.db.roles import get_role_permissions, list_roles

    end_user = next(r for r in list_roles() if r["slug"] == "user" and r["is_system"])
    perms = set(get_role_permissions(end_user["id"]))
    assert "wiki.read" in perms
    assert "chat.use" in perms
    assert "wiki.write" not in perms
    assert "ingest.run" not in perms
    assert not any(p.startswith("admin.") for p in perms)
    assert not any(p.startswith("rbac.assign.") for p in perms)


def test_seed_role_admin_assign_scope() -> None:
    """admin può nominare moderator+user, NON admin né superuser."""
    from llm_wiki.db.roles import get_role_permissions, list_roles

    admin = next(r for r in list_roles() if r["slug"] == "admin" and r["is_system"])
    perms = set(get_role_permissions(admin["id"]))
    assert "rbac.assign.moderator" in perms
    assert "rbac.assign.user" in perms
    assert "rbac.assign.admin" not in perms
    assert "rbac.assign.superuser" not in perms


def test_seed_role_moderator_assign_scope() -> None:
    """moderator può nominare solo user."""
    from llm_wiki.db.roles import get_role_permissions, list_roles

    mod = next(r for r in list_roles() if r["slug"] == "moderator" and r["is_system"])
    perms = set(get_role_permissions(mod["id"]))
    assert "rbac.assign.user" in perms
    assert "rbac.assign.moderator" not in perms
    assert "rbac.assign.admin" not in perms
    # Moderation perms presenti
    assert "wiki.write" in perms
    assert "feedback.delete" in perms


# --- assign/revoke ---------------------------------------------------------


def test_assign_role_aggregates_permissions(fresh_user: dict) -> None:
    from llm_wiki.db.roles import (
        assign_role_to_user,
        get_user_permissions,
        list_roles,
    )

    admin = next(r for r in list_roles() if r["slug"] == "admin" and r["is_system"])
    inserted = assign_role_to_user(fresh_user["id"], admin["id"])
    assert inserted is True

    perms = set(get_user_permissions(fresh_user["id"]))
    assert "wiki.write" in perms
    assert "ingest.run" in perms
    assert "rbac.assign.moderator" in perms
    # Idempotent: secondo assign non duplica
    again = assign_role_to_user(fresh_user["id"], admin["id"])
    assert again is False


def test_revoke_role_removes_permissions(fresh_user: dict) -> None:
    from llm_wiki.db.roles import (
        assign_role_to_user,
        get_user_permissions,
        list_roles,
        revoke_role_from_user,
    )

    admin = next(r for r in list_roles() if r["slug"] == "admin" and r["is_system"])
    assign_role_to_user(fresh_user["id"], admin["id"])
    assert "wiki.write" in get_user_permissions(fresh_user["id"])

    removed = revoke_role_from_user(fresh_user["id"], admin["id"])
    assert removed is True
    assert "wiki.write" not in get_user_permissions(fresh_user["id"])


def test_multiple_roles_union_perms(fresh_user: dict) -> None:
    """Due ruoli → unione dei permessi (no duplicati grazie a SELECT DISTINCT)."""
    from llm_wiki.db.roles import (
        assign_role_to_user,
        get_user_permissions,
        list_roles,
    )

    roles = list_roles()
    end_user = next(r for r in roles if r["slug"] == "user" and r["is_system"])
    admin = next(r for r in roles if r["slug"] == "admin" and r["is_system"])
    assign_role_to_user(fresh_user["id"], end_user["id"])
    assign_role_to_user(fresh_user["id"], admin["id"])

    perms = get_user_permissions(fresh_user["id"])
    assert len(perms) == len(set(perms)), "permessi duplicati nell'aggregazione"
    assert "wiki.read" in perms  # user
    assert "wiki.write" in perms  # admin


# --- domain grants ---------------------------------------------------------


def test_domain_grants_lifecycle(fresh_user: dict) -> None:
    from llm_wiki.db.roles import (
        get_user_domain_grants,
        grant_domain_access,
        revoke_domain_access,
    )

    assert get_user_domain_grants(fresh_user["id"]) == []
    assert grant_domain_access(fresh_user["id"], "insurance") is True
    assert grant_domain_access(fresh_user["id"], "legal") is True
    grants = get_user_domain_grants(fresh_user["id"])
    assert set(grants) == {"insurance", "legal"}
    # Upsert: stesso domain con role_id diverso non duplica
    grant_domain_access(fresh_user["id"], "insurance")
    assert len(get_user_domain_grants(fresh_user["id"])) == 2
    # Revoca
    assert revoke_domain_access(fresh_user["id"], "insurance") is True
    assert get_user_domain_grants(fresh_user["id"]) == ["legal"]


# --- backfill --------------------------------------------------------------


def test_revoke_last_superuser_atomic_guard(fresh_user: dict) -> None:
    """``revoke_role_from_user`` con ``protect_last_superuser=True``
    deve sollevare :class:`LastSuperuserError` se la revoca
    lascerebbe il sistema senza superuser.

    Setup: ``fresh_user`` è l'unico superuser nel DB di test (assumiamo
    che il bootstrap admin del lifespan non gira durante i test).
    Se altri superuser esistono dal seed/bootstrap, il test rimuove
    il ruolo dal fresh_user senza errore — comportamento accettabile
    (guard si attiva solo all'ultimo).
    """
    from llm_wiki.db.roles import (
        LastSuperuserError,
        assign_role_to_user,
        list_roles,
        revoke_role_from_user,
    )

    su_role = next(
        r for r in list_roles() if r["slug"] == "superuser" and r["is_system"]
    )
    assign_role_to_user(fresh_user["id"], su_role["id"])

    # Conta gli altri superuser. Se questo è l'unico → expect raise.
    others = sum(1 for u_id in _all_superuser_user_ids() if u_id != fresh_user["id"])
    if others == 0:
        with pytest.raises(LastSuperuserError):
            revoke_role_from_user(fresh_user["id"], su_role["id"])
        # Verify NOT removed
        from llm_wiki.db.roles import get_user_roles

        slugs = {r["slug"] for r in get_user_roles(fresh_user["id"])}
        assert "superuser" in slugs
    else:
        # Bootstrap admin presente → revoca passa
        removed = revoke_role_from_user(fresh_user["id"], su_role["id"])
        assert removed is True


def _all_superuser_user_ids() -> list[str]:
    from llm_wiki.db.connection import get_connection

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ur.user_id::text
                    FROM user_roles ur
                    JOIN roles r ON r.id = ur.role_id
                    WHERE r.slug = 'superuser' AND r.is_system = TRUE
                    """
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.rollback()


def test_per_domain_perms_grant_role_overrides(fresh_user: dict) -> None:
    """Utente globale `user` + grant `legal` con role `moderator` →
    in dominio `legal` ottiene anche wiki.write/feedback.delete; in
    dominio `insurance` solo i perms `user`.
    """
    from llm_wiki.db.roles import (
        assign_role_to_user,
        get_user_permissions,
        grant_domain_access,
        list_roles,
    )

    roles = list_roles()
    user_role = next(r for r in roles if r["slug"] == "user" and r["is_system"])
    moderator_role = next(
        r for r in roles if r["slug"] == "moderator" and r["is_system"]
    )

    # Global: user
    assign_role_to_user(fresh_user["id"], user_role["id"])
    # Domain `legal`: moderator (override)
    grant_domain_access(fresh_user["id"], "legal", role_id=moderator_role["id"])
    # Domain `insurance`: nessun role override (solo accesso)
    grant_domain_access(fresh_user["id"], "insurance")

    perms_legal = set(get_user_permissions(fresh_user["id"], domain_slug="legal"))
    perms_insurance = set(
        get_user_permissions(fresh_user["id"], domain_slug="insurance")
    )
    perms_global = set(get_user_permissions(fresh_user["id"]))

    # Legal: union global(user) + moderator
    assert "wiki.write" in perms_legal
    assert "feedback.delete" in perms_legal
    assert "rbac.assign.user" in perms_legal

    # Insurance: solo global user
    assert "wiki.read" in perms_insurance
    assert "wiki.write" not in perms_insurance
    assert "feedback.delete" not in perms_insurance

    # Global call (no domain): solo user_roles
    assert "wiki.read" in perms_global
    assert "wiki.write" not in perms_global


def test_per_domain_perms_no_global_role(fresh_user: dict) -> None:
    """Utente senza global role ma con grant dominio + role → ottiene
    perms del role solo per quel dominio. Tutti gli altri domini = 0."""
    from llm_wiki.db.roles import (
        get_user_permissions,
        grant_domain_access,
        list_roles,
    )

    admin_role = next(
        r for r in list_roles() if r["slug"] == "admin" and r["is_system"]
    )
    grant_domain_access(fresh_user["id"], "medical", role_id=admin_role["id"])

    perms_medical = set(get_user_permissions(fresh_user["id"], domain_slug="medical"))
    perms_other = set(get_user_permissions(fresh_user["id"], domain_slug="legal"))
    perms_global = set(get_user_permissions(fresh_user["id"]))

    assert "wiki.write" in perms_medical
    assert "ingest.run" in perms_medical
    assert perms_other == set()
    assert perms_global == set()


def test_backfill_user_has_no_admin_role(fresh_user: dict) -> None:
    """``fresh_user`` (creato dopo le migrations) non riceve ruoli
    automaticamente. Conferma che il backfill 007/008 non promuove
    utenti normali a superuser/admin."""
    from llm_wiki.db.roles import get_user_roles

    user_roles = get_user_roles(fresh_user["id"])
    slugs = {r["slug"] for r in user_roles}
    assert "superuser" not in slugs
    assert "admin" not in slugs

"""Integration test gruppi (mig 015) con Postgres live.

Skip module-wide se Postgres non raggiungibile — stesso pattern di
:mod:`tests.test_rbac_db`.

Coverage
========

- ``create_group`` / ``update_group`` / ``delete_group`` lifecycle.
- Slug duplicato per tenant → IntegrityError → 409 lato API.
- ``add_member`` rifiuta cross-tenant via :class:`CrossTenantError`.
- ``add_members_bulk`` raccoglie ``added`` + ``skipped`` senza abortire.
- ``assign_role`` ruolo globale ok, ruolo tenant-scoped diverso → reject.
- ``get_user_permissions`` aggrega ruoli del gruppo (UNION con user_roles).
- ``delete_group`` rifiuta ``is_system=True``.
- ``get_user_groups`` ritorna membership per ``/api/auth/me``.
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


def _make_tenant_user(suffix: str | None = None) -> dict:
    """Crea tenant + owner, ritorna ``{"user": ..., "tenant_id": ...}``.

    Caller responsabile del cleanup via ``delete_tenant``.
    """
    from llm_wiki.db.tenants import create_tenant_with_owner
    from llm_wiki.db.users import hash_password

    suffix = suffix or secrets.token_hex(6)
    result = create_tenant_with_owner(
        tenant_name=f"Group Test {suffix}",
        tenant_slug=f"grp-{suffix}",
        user_email=f"grp-{suffix}@local.test",
        user_password_hash=hash_password("S3cur3-Test-Pass!"),
        user_display_name="Group Test User",
        plan="free",
        role="user",
    )
    return {"user": result["user"], "tenant_id": result["user"]["tenant_id"]}


@pytest.fixture
def tenant_a():
    from llm_wiki.db.tenants import delete_tenant

    data = _make_tenant_user()
    yield data
    try:
        delete_tenant(data["tenant_id"])
    except Exception:
        pass


@pytest.fixture
def tenant_b():
    from llm_wiki.db.tenants import delete_tenant

    data = _make_tenant_user()
    yield data
    try:
        delete_tenant(data["tenant_id"])
    except Exception:
        pass


# --- CRUD ----------------------------------------------------------------


def test_create_list_get_group(tenant_a: dict) -> None:
    from llm_wiki.db.groups import create_group, get_group_by_id, list_groups

    created = create_group(
        tenant_id=tenant_a["tenant_id"],
        slug="engineering",
        name="Engineering",
        description="Tutti gli ingegneri.",
    )
    assert created["slug"] == "engineering"
    assert created["member_count"] == 0
    assert created["role_count"] == 0
    assert created["is_system"] is False

    rows = list_groups(tenant_a["tenant_id"])
    assert any(g["slug"] == "engineering" for g in rows)

    fetched = get_group_by_id(created["id"])
    assert fetched is not None
    assert fetched["name"] == "Engineering"


def test_update_group(tenant_a: dict) -> None:
    from llm_wiki.db.groups import create_group, update_group

    g = create_group(tenant_id=tenant_a["tenant_id"], slug="ops", name="Ops")
    updated = update_group(g["id"], name="Operations", description="Nuova desc")
    assert updated is not None
    assert updated["name"] == "Operations"
    assert updated["description"] == "Nuova desc"
    # slug immutato
    assert updated["slug"] == "ops"


def test_delete_group(tenant_a: dict) -> None:
    from llm_wiki.db.groups import create_group, delete_group, get_group_by_id

    g = create_group(tenant_id=tenant_a["tenant_id"], slug="todelete", name="X")
    assert delete_group(g["id"]) is True
    assert get_group_by_id(g["id"]) is None


def test_duplicate_slug_per_tenant_rejected(tenant_a: dict) -> None:
    import psycopg

    from llm_wiki.db.groups import create_group

    create_group(tenant_id=tenant_a["tenant_id"], slug="dup", name="A")
    with pytest.raises(psycopg.errors.UniqueViolation):
        create_group(tenant_id=tenant_a["tenant_id"], slug="dup", name="B")


def test_same_slug_different_tenants_ok(tenant_a: dict, tenant_b: dict) -> None:
    """Slug ``engineering`` può esistere in più tenant indipendenti."""
    from llm_wiki.db.groups import create_group

    a = create_group(tenant_id=tenant_a["tenant_id"], slug="engineering", name="Eng A")
    b = create_group(tenant_id=tenant_b["tenant_id"], slug="engineering", name="Eng B")
    assert a["id"] != b["id"]
    assert a["tenant_id"] != b["tenant_id"]


# --- Membership ----------------------------------------------------------


def test_add_remove_member(tenant_a: dict) -> None:
    from llm_wiki.db.groups import (
        add_member,
        create_group,
        get_group_members,
        get_user_groups,
        remove_member,
    )

    g = create_group(tenant_id=tenant_a["tenant_id"], slug="team1", name="Team 1")
    uid = tenant_a["user"]["id"]

    assert add_member(g["id"], uid) is True
    # Idempotent
    assert add_member(g["id"], uid) is False

    members = get_group_members(g["id"])
    assert any(m["id"] == uid for m in members)

    user_groups = get_user_groups(uid)
    assert any(ug["id"] == g["id"] for ug in user_groups)

    assert remove_member(g["id"], uid) is True
    assert remove_member(g["id"], uid) is False
    assert get_group_members(g["id"]) == []


def test_add_member_cross_tenant_rejected(tenant_a: dict, tenant_b: dict) -> None:
    """Utente tenant_b non può finire in gruppo tenant_a."""
    from llm_wiki.db.groups import CrossTenantError, add_member, create_group

    g = create_group(tenant_id=tenant_a["tenant_id"], slug="ta", name="TA")
    other_uid = tenant_b["user"]["id"]
    with pytest.raises(CrossTenantError):
        add_member(g["id"], other_uid)


def test_add_members_bulk_partitions_added_skipped(tenant_a: dict, tenant_b: dict) -> None:
    from llm_wiki.db.groups import add_members_bulk, create_group

    g = create_group(tenant_id=tenant_a["tenant_id"], slug="bulk", name="Bulk")
    own_uid = tenant_a["user"]["id"]
    foreign_uid = tenant_b["user"]["id"]

    result = add_members_bulk(g["id"], [own_uid, foreign_uid, own_uid])
    assert own_uid in result["added"]
    # Cross-tenant + duplicato → entrambi in skipped
    assert foreign_uid in result["skipped"]
    # Dup deduplicato in input → non riprovato
    assert result["added"].count(own_uid) == 1


# --- Role assignment -----------------------------------------------------


def test_assign_global_role_ok(tenant_a: dict) -> None:
    from llm_wiki.db.groups import assign_role, create_group, get_group_roles
    from llm_wiki.db.roles import list_roles

    g = create_group(tenant_id=tenant_a["tenant_id"], slug="r1", name="R1")
    moderator = next(r for r in list_roles() if r["slug"] == "moderator" and r["is_system"])
    assert assign_role(g["id"], moderator["id"]) is True
    # Idempotent
    assert assign_role(g["id"], moderator["id"]) is False

    roles = get_group_roles(g["id"])
    assert any(r["slug"] == "moderator" for r in roles)


def test_assign_tenant_role_cross_tenant_rejected(tenant_a: dict, tenant_b: dict) -> None:
    """Ruolo creato in tenant_b non può finire su gruppo tenant_a."""
    from llm_wiki.db.connection import get_connection
    from llm_wiki.db.groups import CrossTenantError, assign_role, create_group

    g = create_group(tenant_id=tenant_a["tenant_id"], slug="rc", name="RC")
    # Crea ruolo tenant-scoped in tenant_b
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO roles (slug, name, tenant_id) VALUES (%s, %s, %s) "
                "RETURNING id::text",
                ("tenantbrole", "Tenant B Role", tenant_b["tenant_id"]),
            )
            role_id = cur.fetchone()[0]
        conn.commit()

    with pytest.raises(CrossTenantError):
        assign_role(g["id"], role_id)


# --- Effective permissions ----------------------------------------------


def test_group_role_perms_included_in_get_user_permissions(tenant_a: dict) -> None:
    """Utente in gruppo con ruolo ``admin`` riceve i perms admin nella
    query ``get_user_permissions`` (UNION con user_roles)."""
    from llm_wiki.db.groups import add_member, assign_role, create_group
    from llm_wiki.db.roles import get_user_permissions, list_roles

    uid = tenant_a["user"]["id"]
    # Baseline: zero perms (utente fresco)
    assert get_user_permissions(uid) == []

    g = create_group(tenant_id=tenant_a["tenant_id"], slug="adm", name="Admins")
    admin_role = next(r for r in list_roles() if r["slug"] == "admin" and r["is_system"])
    assign_role(g["id"], admin_role["id"])
    add_member(g["id"], uid)

    perms = set(get_user_permissions(uid))
    assert "wiki.write" in perms
    assert "ingest.run" in perms
    assert "admin.user.manage" in perms


def test_user_roles_and_group_roles_union(tenant_a: dict) -> None:
    """Permessi diretti + permessi via gruppo si sommano (dedup automatico)."""
    from llm_wiki.db.groups import add_member, assign_role, create_group
    from llm_wiki.db.roles import (
        assign_role_to_user,
        get_user_permissions,
        list_roles,
    )

    uid = tenant_a["user"]["id"]
    roles = list_roles()
    user_role = next(r for r in roles if r["slug"] == "user" and r["is_system"])
    moderator_role = next(r for r in roles if r["slug"] == "moderator" and r["is_system"])

    # Ruolo diretto: user
    assign_role_to_user(uid, user_role["id"])
    # Gruppo con ruolo moderator
    g = create_group(tenant_id=tenant_a["tenant_id"], slug="mods", name="Mods")
    assign_role(g["id"], moderator_role["id"])
    add_member(g["id"], uid)

    perms = get_user_permissions(uid)
    # Dedup: no duplicati
    assert len(perms) == len(set(perms))
    # Da user
    assert "wiki.read" in perms
    # Da moderator (via group)
    assert "feedback.delete" in perms
    assert "rbac.assign.user" in perms


def test_remove_member_removes_perms(tenant_a: dict) -> None:
    """Rimuovendo l'utente dal gruppo, i perms ereditati spariscono."""
    from llm_wiki.db.groups import (
        add_member,
        assign_role,
        create_group,
        remove_member,
    )
    from llm_wiki.db.roles import get_user_permissions, list_roles

    uid = tenant_a["user"]["id"]
    g = create_group(tenant_id=tenant_a["tenant_id"], slug="tmp", name="Tmp")
    admin_role = next(r for r in list_roles() if r["slug"] == "admin" and r["is_system"])
    assign_role(g["id"], admin_role["id"])
    add_member(g["id"], uid)
    assert "wiki.write" in get_user_permissions(uid)

    remove_member(g["id"], uid)
    assert "wiki.write" not in get_user_permissions(uid)


def test_group_perms_apply_with_domain_filter(tenant_a: dict) -> None:
    """Group perms restano effettivi anche quando si filtra per domain
    (sono perms globali via group bundle, non domain-scoped)."""
    from llm_wiki.db.groups import add_member, assign_role, create_group
    from llm_wiki.db.roles import get_user_permissions, list_roles

    uid = tenant_a["user"]["id"]
    g = create_group(tenant_id=tenant_a["tenant_id"], slug="gd", name="GD")
    admin_role = next(r for r in list_roles() if r["slug"] == "admin" and r["is_system"])
    assign_role(g["id"], admin_role["id"])
    add_member(g["id"], uid)

    perms_with_domain = set(get_user_permissions(uid, domain_slug="legal"))
    perms_no_domain = set(get_user_permissions(uid))
    assert "wiki.write" in perms_with_domain
    assert "wiki.write" in perms_no_domain


# --- System group protection --------------------------------------------


def test_system_group_cannot_be_deleted(tenant_a: dict) -> None:
    from llm_wiki.db.groups import SystemGroupProtected, create_group, delete_group

    g = create_group(
        tenant_id=tenant_a["tenant_id"],
        slug="sysgrp",
        name="Sys",
        is_system=True,
    )
    with pytest.raises(SystemGroupProtected):
        delete_group(g["id"])


# --- Permission catalog -------------------------------------------------


def test_admin_group_manage_permission_seeded() -> None:
    """Mig 015 seeda ``admin.group.manage`` su superuser + admin."""
    from llm_wiki.db.roles import get_role_permissions, list_roles

    roles = list_roles()
    superuser = next(r for r in roles if r["slug"] == "superuser" and r["is_system"])
    admin = next(r for r in roles if r["slug"] == "admin" and r["is_system"])
    moderator = next(r for r in roles if r["slug"] == "moderator" and r["is_system"])
    user = next(r for r in roles if r["slug"] == "user" and r["is_system"])

    assert "admin.group.manage" in get_role_permissions(superuser["id"])
    assert "admin.group.manage" in get_role_permissions(admin["id"])
    assert "admin.group.manage" not in get_role_permissions(moderator["id"])
    assert "admin.group.manage" not in get_role_permissions(user["id"])

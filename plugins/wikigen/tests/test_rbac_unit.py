"""Unit test RBAC (Fase 7) — no DB.

Copre:
- Catalogo permessi (:class:`Permission`) ↔ ``ALL_PERMISSIONS`` consistenti.
- Helper ``has_permission`` / ``has_any`` / ``has_all`` su user dict.
- ``require_permission`` factory: rifiuta argomenti vuoti/mode invalido.

Test integration con DB live in ``tests/test_rbac_db.py``.
"""

from __future__ import annotations

import pytest


def test_permission_catalog_consistent() -> None:
    """Tutte le costanti :class:`Permission` devono comparire in
    ``ALL_PERMISSIONS`` — guard contro drift in PR future."""
    from llm_wiki.auth.permissions import ALL_PERMISSIONS, Permission

    declared = {
        getattr(Permission, attr)
        for attr in dir(Permission)
        if not attr.startswith("_") and isinstance(getattr(Permission, attr), str)
    }
    assert declared == set(ALL_PERMISSIONS), (
        f"drift: declared-but-not-listed={declared - ALL_PERMISSIONS} "
        f"listed-but-not-declared={ALL_PERMISSIONS - declared}"
    )


def test_has_permission_anonymous() -> None:
    from llm_wiki.auth.permissions import has_permission

    assert not has_permission(None, "wiki.read")
    assert not has_permission({}, "wiki.read")
    assert not has_permission({"perms": []}, "wiki.read")


def test_has_permission_grant() -> None:
    from llm_wiki.auth.permissions import has_permission

    user = {"perms": ["wiki.read", "chat.use"]}
    assert has_permission(user, "wiki.read")
    assert not has_permission(user, "wiki.write")


def test_has_any_all() -> None:
    from llm_wiki.auth.permissions import has_all, has_any

    user = {"perms": ["wiki.read", "chat.use"]}
    assert has_any(user, ["wiki.write", "chat.use"])
    assert not has_any(user, ["wiki.write", "wiki.delete"])
    assert has_all(user, ["wiki.read", "chat.use"])
    assert not has_all(user, ["wiki.read", "wiki.write"])


def test_require_permission_validates_args() -> None:
    from llm_wiki.auth.dependencies import require_permission

    with pytest.raises(ValueError):
        require_permission()  # nessun permesso
    with pytest.raises(ValueError):
        require_permission("wiki.read", mode="bogus")


def _load_migration(name: str):
    """Carica un file alembic come modulo per ispezionare le costanti."""
    import importlib.util
    from pathlib import Path

    mig_path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"mig_{name}", mig_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_seed_migrations_combined_match_python_catalog() -> None:
    """L'unione dei permessi seedati in 007 + 008 deve combaciare con
    :data:`ALL_PERMISSIONS` Python. Drift in entrambe le direzioni
    riportato esplicitamente.
    """
    from llm_wiki.auth.permissions import ALL_PERMISSIONS

    mod_007 = _load_migration("007_rbac")
    mod_008 = _load_migration("008_rbac_hierarchy")
    mod_012 = _load_migration("012_obsidian_permission")
    mod_013 = _load_migration("013_graph_read_permission")
    mod_014 = _load_migration("014_ui_view_permissions")
    mod_015 = _load_migration("015_groups")
    mod_016 = _load_migration("016_conv_write_perm")
    mod_017 = _load_migration("017_embeds")
    seed_slugs = (
        {slug for slug, _ in mod_007.SEED_PERMISSIONS}
        | {slug for slug, _ in mod_008.NEW_PERMISSIONS}
        | {mod_012.PERMISSION_SLUG}
        | {mod_013.PERMISSION_SLUG}
        | {slug for slug, _ in mod_014.PERMISSIONS}
        | {mod_015.PERMISSION_SLUG}
        | {mod_016.PERMISSION_SLUG}
        | {mod_017.PERMISSION_SLUG}
    )
    assert seed_slugs == set(ALL_PERMISSIONS), (
        f"drift seed↔Python: only-in-seed={seed_slugs - ALL_PERMISSIONS} "
        f"only-in-Python={ALL_PERMISSIONS - seed_slugs}"
    )


def test_role_assign_permission_covers_all_system_roles() -> None:
    """Ogni :class:`SystemRole` deve avere un permesso di nomina
    associato in :data:`ROLE_ASSIGN_PERMISSION`. Drift = bug:
    l'endpoint assign_role rifiuterebbe ruoli orfani con messaggio
    confuso."""
    from llm_wiki.auth.permissions import ROLE_ASSIGN_PERMISSION, SystemRole

    declared_roles = {
        getattr(SystemRole, attr)
        for attr in dir(SystemRole)
        if not attr.startswith("_") and isinstance(getattr(SystemRole, attr), str)
    }
    assert declared_roles == set(ROLE_ASSIGN_PERMISSION.keys()), (
        f"missing-from-map={declared_roles - ROLE_ASSIGN_PERMISSION.keys()} "
        f"extra-in-map={ROLE_ASSIGN_PERMISSION.keys() - declared_roles}"
    )


def test_hierarchy_admin_cannot_create_admin() -> None:
    """admin (con `rbac.assign.moderator` + `rbac.assign.user`) NON deve
    avere `rbac.assign.admin` né `rbac.assign.superuser`. Verifica
    diretta del seed 008.
    """
    from llm_wiki.auth.permissions import Permission

    mod_008 = _load_migration("008_rbac_hierarchy")
    admin = next(r for r in mod_008.SEED_ROLES if r.slug == "admin")
    perms = set(admin.permissions)
    assert Permission.RBAC_ASSIGN_MODERATOR in perms
    assert Permission.RBAC_ASSIGN_USER in perms
    assert Permission.RBAC_ASSIGN_ADMIN not in perms
    assert Permission.RBAC_ASSIGN_SUPERUSER not in perms


def test_hierarchy_moderator_only_creates_user() -> None:
    from llm_wiki.auth.permissions import Permission

    mod_008 = _load_migration("008_rbac_hierarchy")
    mod = next(r for r in mod_008.SEED_ROLES if r.slug == "moderator")
    perms = set(mod.permissions)
    assert Permission.RBAC_ASSIGN_USER in perms
    assert Permission.RBAC_ASSIGN_MODERATOR not in perms
    assert Permission.RBAC_ASSIGN_ADMIN not in perms


def test_hierarchy_user_cannot_assign_anyone() -> None:
    mod_008 = _load_migration("008_rbac_hierarchy")
    user = next(r for r in mod_008.SEED_ROLES if r.slug == "user")
    perms = set(user.permissions)
    assert not any(p.startswith("rbac.assign.") for p in perms)
    assert not any(p.startswith("admin.") for p in perms)


def test_hierarchy_superuser_full_grant() -> None:
    """Superuser deve avere TUTTI i permessi del catalogo, inclusi
    quelli di assign per qualsiasi tier."""
    from llm_wiki.auth.permissions import ALL_PERMISSIONS

    mod_008 = _load_migration("008_rbac_hierarchy")
    mod_012 = _load_migration("012_obsidian_permission")
    mod_013 = _load_migration("013_graph_read_permission")
    mod_014 = _load_migration("014_ui_view_permissions")
    mod_015 = _load_migration("015_groups")
    mod_016 = _load_migration("016_conv_write_perm")
    mod_017 = _load_migration("017_embeds")
    su = next(r for r in mod_008.SEED_ROLES if r.slug == "superuser")
    # Mig 008 seeds the bulk; later migrations grant additional perms via
    # role_permissions inserts (mig 012 → obsidian.open, mig 013 →
    # graph.read, mig 014 → view.*, mig 015 → admin.group.manage,
    # mig 016 → conversation.write, mig 017 → admin.embed.manage).
    # Aggregate the post-008 grants targeting ``superuser`` so the union
    # matches the Python catalog (single source of truth).
    later_grants: set[str] = set()
    if "superuser" in mod_012.GRANT_TO_SLUGS:
        later_grants.add(mod_012.PERMISSION_SLUG)
    if "superuser" in mod_013.GRANT_TO_SLUGS:
        later_grants.add(mod_013.PERMISSION_SLUG)
    if "superuser" in mod_014.GRANT_TO_SLUGS:
        later_grants |= {slug for slug, _ in mod_014.PERMISSIONS}
    if "superuser" in mod_015.GRANT_TO_SLUGS:
        later_grants.add(mod_015.PERMISSION_SLUG)
    if "superuser" in mod_016.GRANT_TO_SLUGS:
        later_grants.add(mod_016.PERMISSION_SLUG)
    if "superuser" in mod_017.GRANT_TO_SLUGS:
        later_grants.add(mod_017.PERMISSION_SLUG)
    assert set(su.permissions) | later_grants == set(ALL_PERMISSIONS)

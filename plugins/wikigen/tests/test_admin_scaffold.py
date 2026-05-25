"""Tests for the admin scaffold module + tenant registry.

Covers the surface that the UI wizard depends on:

- ``ScaffoldRequest`` validation (slug regex, reserved names, vault rules)
- ``plan_scaffold`` returns a complete preview without touching disk
- ``scaffold_pack`` is idempotent unless ``force=True``
- vault paths inside ``domains/`` or pointing at engine roots are refused
- ``TenantRegistry`` discovers packs and skips ``_template``
- environment variable ``WIKI_ROOT_<NAME>`` overrides the default vault
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from llm_wiki.admin.scaffold import (
    ScaffoldError,
    ScaffoldRequest,
    plan_scaffold,
    repo_root,
    resolve_vault_path,
    scaffold_pack,
)
from llm_wiki.admin.tenants import TenantRegistry, reset_registry

REPO = repo_root()


@pytest.fixture
def fresh_pack(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    """Yield a (slug, vault) pair and clean up the scaffolded pack after."""
    name = "smoke_admin"
    target = REPO / "domains" / name
    if target.exists():
        shutil.rmtree(target)
    vault = tmp_path / "vault"
    yield name, vault
    if target.exists():
        shutil.rmtree(target)


# --- request validation ----------------------------------------------------


def test_request_rejects_reserved_template_name() -> None:
    with pytest.raises(ValueError):
        ScaffoldRequest(name="_template")


def test_request_rejects_uppercase_name() -> None:
    with pytest.raises(ValueError):
        ScaffoldRequest(name="LegalWiki")


def test_request_accepts_valid_slug() -> None:
    req = ScaffoldRequest(name="my-legal_v2")
    assert req.name == "my-legal_v2"


# --- vault path safety -----------------------------------------------------


def test_vault_under_domains_rejected() -> None:
    domains = REPO / "domains" / "evil"
    with pytest.raises(ScaffoldError):
        resolve_vault_path("evil", str(domains))


def test_vault_at_repo_root_rejected() -> None:
    with pytest.raises(ScaffoldError):
        resolve_vault_path("evil", str(REPO))


def test_vault_relative_path_rejected() -> None:
    with pytest.raises(ScaffoldError):
        resolve_vault_path("evil", "vaults/evil")


def test_default_vault_resolves_under_repo() -> None:
    p = resolve_vault_path("foo", "")
    assert p == (REPO / "vaults" / "foo").resolve()


# --- plan / apply ----------------------------------------------------------


def test_plan_is_pure(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name, vault_root=str(vault), write_env=False, activate=False
    )
    plan = plan_scaffold(req)
    assert plan.name == name
    assert plan.target_pack_dir == REPO / "domains" / name
    assert plan.vault_path == vault.resolve()
    assert any(op["kind"] == "copy" for op in plan.operations)
    # nothing was written
    assert not (REPO / "domains" / name).exists()
    assert not vault.exists()


def test_apply_creates_pack_and_vault(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name,
        label="Smoke Admin",
        description="admin scaffold smoke",
        language="en",
        vault_root=str(vault),
        write_env=False,
        activate=False,
    )
    result = scaffold_pack(req)
    assert result.target_pack_dir.is_dir()
    assert (result.target_pack_dir / "pack.yaml").is_file()
    assert (result.vault_path / "wiki").is_dir()
    assert (result.vault_path / "raw").is_dir()
    text = (result.target_pack_dir / "pack.yaml").read_text(encoding="utf-8")
    assert f"name: {name}" in text
    assert 'label: "Smoke Admin"' in text
    assert "language: en" in text


# --- vault seed (istruzioni.md / Karpathy pattern) ------------------------


def test_vault_seed_creates_index_log_claude(fresh_pack: tuple[str, Path]) -> None:
    """istruzioni.md mandate: vault must ship index.md, log.md and CLAUDE.md
    after scaffold so the LLM agent has the Karpathy pattern files to
    operate against from the very first session."""
    name, vault = fresh_pack
    result = scaffold_pack(
        ScaffoldRequest(
            name=name,
            label="Smoke Wiki",
            vault_root=str(vault),
            write_env=False,
            activate=False,
        )
    )
    index_md = result.vault_path / "wiki" / "index.md"
    log_md = result.vault_path / "wiki" / "log.md"
    claude_md = result.vault_path / "CLAUDE.md"
    assert index_md.is_file()
    assert log_md.is_file()
    assert claude_md.is_file()

    log_text = log_md.read_text(encoding="utf-8")
    # greppable header form per istruzioni.md
    assert "## [" in log_text and f"scaffold | {name}" in log_text

    claude_text = claude_md.read_text(encoding="utf-8")
    assert "Karpathy" in claude_text
    assert f"`{name}`" in claude_text
    assert "raw/" in claude_text
    assert "wiki/" in claude_text


def test_vault_seed_creates_page_type_subfolders(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    result = scaffold_pack(
        ScaffoldRequest(
            name=name, vault_root=str(vault), write_env=False, activate=False
        )
    )
    # _template ships with source/concept/entity/topic page types.
    for folder in ("sources", "concepts", "entities", "topics"):
        assert (result.vault_path / "wiki" / folder).is_dir(), f"missing wiki/{folder}/"


def test_vault_seed_idempotent_does_not_clobber_user_edits(
    fresh_pack: tuple[str, Path],
) -> None:
    """Re-scaffolding with force must NOT overwrite user-edited index/log/CLAUDE."""
    name, vault = fresh_pack
    result = scaffold_pack(
        ScaffoldRequest(
            name=name, vault_root=str(vault), write_env=False, activate=False
        )
    )
    index_md = result.vault_path / "wiki" / "index.md"
    index_md.write_text("# tampered by user\n", encoding="utf-8")

    scaffold_pack(
        ScaffoldRequest(
            name=name,
            vault_root=str(vault),
            write_env=False,
            activate=False,
            force=True,
        )
    )
    assert "tampered by user" in index_md.read_text(encoding="utf-8")


def test_apply_is_idempotent_without_force(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name, vault_root=str(vault), write_env=False, activate=False
    )
    scaffold_pack(req)
    with pytest.raises(ScaffoldError, match="already exists"):
        scaffold_pack(req)


def test_apply_force_overwrites(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name, vault_root=str(vault), write_env=False, activate=False
    )
    scaffold_pack(req)
    # mutate then re-apply with force
    pack_yaml = REPO / "domains" / name / "pack.yaml"
    pack_yaml.write_text("# tampered\n", encoding="utf-8")
    req2 = req.model_copy(update={"force": True})
    scaffold_pack(req2)
    text = pack_yaml.read_text(encoding="utf-8")
    assert "# tampered" not in text
    assert f"name: {name}" in text


# --- tenant registry -------------------------------------------------------


def test_registry_skips_template(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name, vault_root=str(vault), write_env=False, activate=False
    )
    scaffold_pack(req)

    reset_registry()
    reg = TenantRegistry()
    names = {t.name for t in reg.list_tenants()}
    assert "_template" not in names
    assert name in names


def test_registry_distinguishes_seed_vs_user(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name, vault_root=str(vault), write_env=False, activate=False
    )
    scaffold_pack(req)

    reset_registry()
    reg = TenantRegistry()
    seeds = {t.name for t in reg.list_seed_tenants()}
    users = {t.name for t in reg.list_user_tenants()}
    assert "insurance" in seeds  # ships with seed: true
    assert "legal" in seeds
    assert name in users
    assert name not in seeds


def test_setup_required_when_active_is_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    """White-label rule: seed packs are never a valid runtime identity.
    APP_DOMAIN pointing to a seed -> setup_required=True regardless of
    whether the user has scaffolded their own packs."""
    monkeypatch.setenv("APP_DOMAIN", "insurance")
    reset_registry()
    reg = TenantRegistry()
    assert reg.setup_required() is True


def test_setup_required_when_app_domain_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DOMAIN", "")
    reset_registry()
    reg = TenantRegistry()
    assert reg.setup_required() is True


def test_setup_not_required_with_user_pack_active(
    fresh_pack: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name, vault_root=str(vault), write_env=False, activate=False
    )
    scaffold_pack(req)
    monkeypatch.setenv("APP_DOMAIN", name)
    reset_registry()
    reg = TenantRegistry()
    assert reg.has_user_tenants() is True
    assert reg.setup_required() is False


# --- fork from seed --------------------------------------------------------


def test_fork_from_seed_copies_seed_layout(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name,
        vault_root=str(vault),
        write_env=False,
        activate=False,
        from_seed="insurance",
    )
    result = scaffold_pack(req)
    pack_yaml = (result.target_pack_dir / "pack.yaml").read_text(encoding="utf-8")
    assert f"name: {name}" in pack_yaml
    # Forked pack must lose the seed flag so it counts as a user pack.
    assert "seed: true" not in pack_yaml
    assert "seed: false" in pack_yaml
    # Must inherit insurance's strategies/examples (insurance has these; _template doesn't)
    assert (result.target_pack_dir / "strategies.py").is_file() or (
        result.target_pack_dir / "strategies.py.example"
    ).is_file()


def test_fork_rejects_unknown_seed(fresh_pack: tuple[str, Path]) -> None:
    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name,
        vault_root=str(vault),
        write_env=False,
        activate=False,
        from_seed="nonexistent",
    )
    with pytest.raises(ScaffoldError, match="seed pack not found"):
        scaffold_pack(req)


def test_fork_rejects_user_pack_as_seed(
    fresh_pack: tuple[str, Path], tmp_path: Path
) -> None:
    """A user pack (seed: false) must not be selectable as a fork source."""
    user_name = "smoke_user_src"
    user_target = REPO / "domains" / user_name
    if user_target.exists():
        shutil.rmtree(user_target)
    try:
        scaffold_pack(
            ScaffoldRequest(
                name=user_name,
                vault_root=str(tmp_path / "src_vault"),
                write_env=False,
                activate=False,
            )
        )
        # now try to fork from it
        name, vault = fresh_pack
        with pytest.raises(ScaffoldError, match="not marked as seed"):
            scaffold_pack(
                ScaffoldRequest(
                    name=name,
                    vault_root=str(vault),
                    write_env=False,
                    activate=False,
                    from_seed=user_name,
                )
            )
    finally:
        if user_target.exists():
            shutil.rmtree(user_target)


def test_fork_rejects_same_name_as_seed(fresh_pack: tuple[str, Path]) -> None:
    _, vault = fresh_pack
    req = ScaffoldRequest(
        name="insurance",
        vault_root=str(vault),
        write_env=False,
        activate=False,
        force=False,
        from_seed="insurance",
    )
    # Pack already exists -> ScaffoldError before reaching the same-name check is OK,
    # but with force the same-name guard kicks in.
    req_force = req.model_copy(update={"force": True})
    with pytest.raises(ScaffoldError):
        scaffold_pack(req_force)


def test_registry_load_context_uses_env_override(
    fresh_pack: tuple[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Legacy ``WIKI_ROOT_<NAME>`` per-pack override resta supportato come
    fallback (Fase 4 wiki-shared refactor non l'ha rimosso, solo
    deprecato — nuovo scaffold scrive solo ``WIKI_ROOT`` flat).

    Garantisce: l'env legacy viene letta correttamente, e
    ``qdrant_collection`` ora è la costante globale ``"wiki"`` (wiki
    SHARED — niente più suffissi ``<name>-wiki`` per-pack).
    """

    name, vault = fresh_pack
    req = ScaffoldRequest(
        name=name, vault_root=str(vault), write_env=False, activate=False
    )
    scaffold_pack(req)

    custom = tmp_path / "elsewhere"
    # Drop la `WIKI_ROOT` flat altrimenti vince sopra il legacy per-pack.
    monkeypatch.delenv("WIKI_ROOT", raising=False)
    monkeypatch.setenv(f"WIKI_ROOT_{name.upper()}", str(custom))
    reset_registry()
    reg = TenantRegistry()
    ctx = reg.load_context(name)
    assert ctx.vault_root == custom.resolve()
    # Pack non attivo → property deriva ``<name>-wiki`` per pack
    # (vedi TenantContext.qdrant_collection). Solo il pack attivo
    # delega a ``config.COLLECTION_NAME``.
    assert ctx.is_active is False
    assert ctx.qdrant_collection == f"{name}-wiki"
    assert ctx.graph_db_name == f"{name}-wiki"


# --- env mutation: lock + atomic write -------------------------------------


def test_mutate_env_file_atomic_write(tmp_path: Path) -> None:
    """``.env`` write goes through tempfile + ``os.replace``: 0600 perms,
    full content visible after, no partial state."""
    from llm_wiki.admin.scaffold import mutate_env_file

    env = tmp_path / ".env"
    env.write_text("EXISTING=keep\n", encoding="utf-8")

    written = mutate_env_file(env, lambda b: b + "NEW=added\n")
    assert written is True
    text = env.read_text(encoding="utf-8")
    assert "EXISTING=keep" in text
    assert "NEW=added" in text
    # 0600: only owner read/write
    import os as _os
    import stat as _stat

    mode = _stat.S_IMODE(_os.stat(env).st_mode)
    assert mode == 0o600


def test_mutate_env_file_template_fallback(tmp_path: Path) -> None:
    """Missing target + present template → seed from template."""
    from llm_wiki.admin.scaffold import mutate_env_file

    env = tmp_path / ".env"
    template = tmp_path / ".env.example"
    template.write_text("SEED=1\n", encoding="utf-8")

    written = mutate_env_file(env, lambda b: b + "EXTRA=2\n", template=template)
    assert written is True
    text = env.read_text(encoding="utf-8")
    assert "SEED=1" in text
    assert "EXTRA=2" in text


def test_mutate_env_file_concurrent_serialised(tmp_path: Path) -> None:
    """Two threads racing on the same ``.env`` must both land their key.

    Without ``flock`` the read-modify-write would silently drop one
    side. Regression test for the lock helper.
    """
    import threading

    from llm_wiki.admin.scaffold import mutate_env_file

    env = tmp_path / ".env"
    env.write_text("BASE=0\n", encoding="utf-8")

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def _writer(key: str, value: str) -> None:
        def mutator(base: str) -> str:
            # Force interleaving: read base, sleep briefly, append. Without
            # the lock both threads observe the same base and the second
            # write clobbers the first.
            import time

            time.sleep(0.05)
            return base + f"{key}={value}\n"

        try:
            barrier.wait(timeout=2)
            mutate_env_file(env, mutator)
        except Exception as exc:  # pragma: no cover — surfaced via errors list
            errors.append(exc)

    threads = [
        threading.Thread(target=_writer, args=("ALPHA", "1")),
        threading.Thread(target=_writer, args=("BETA", "2")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert errors == []
    text = env.read_text(encoding="utf-8")
    assert "BASE=0" in text
    assert "ALPHA=1" in text
    assert "BETA=2" in text


def test_scaffold_activate_resets_pack_cache_and_syncs_env(
    fresh_pack: tuple[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``scaffold_pack(activate=True)`` must reset the cached DomainPack
    and sync ``APP_DOMAIN``/``WIKI_ROOT`` into ``os.environ`` so
    same-process callers see the new pack without restart."""
    from llm_wiki.admin import scaffold as scaffold_mod
    from llm_wiki.domain import registry as reg_mod

    name, vault = fresh_pack

    fake_env = tmp_path / ".env"
    fake_env.write_text("BASE=0\n", encoding="utf-8")
    # Redirect repo_root only for the .env upsert; scaffold itself still
    # uses the real REPO/domains/<name> (cleaned by fresh_pack fixture).
    real_repo_root = scaffold_mod.repo_root

    def _fake_repo_root() -> Path:
        # Called from _upsert_env_file only; return tmp_path so the
        # write lands on our fake .env, not the developer's real one.
        # Other callers in plan_scaffold (target_pack_dir computation)
        # still want the real repo. Disambiguate by stack frame.
        import sys as _sys

        caller = _sys._getframe(1).f_code.co_name
        if caller == "_upsert_env_file":
            return tmp_path
        return real_repo_root()

    monkeypatch.setattr(scaffold_mod, "repo_root", _fake_repo_root)
    # Plant a sentinel in the pack cache — must be cleared by activation.
    sentinel = object()
    monkeypatch.setattr(reg_mod, "_cached", sentinel)
    monkeypatch.setattr(reg_mod, "_cached_root", Path("/sentinel"))

    req = ScaffoldRequest(
        name=name,
        vault_root=str(vault),
        write_env=True,
        activate=True,
        synthesize_prompts=False,
    )
    scaffold_pack(req)

    import os as _os

    assert _os.environ.get("APP_DOMAIN") == name
    assert _os.environ.get("WIKI_ROOT") == str(vault.resolve())
    # Cache must be dropped — sentinel object is gone.
    assert reg_mod._cached is None
    # .env carries the new keys without dropping BASE.
    text = fake_env.read_text(encoding="utf-8")
    assert "BASE=0" in text
    assert f"APP_DOMAIN={name}" in text
    assert "WIKI_ROOT=" in text

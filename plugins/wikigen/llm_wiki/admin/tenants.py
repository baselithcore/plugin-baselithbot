"""Domain Pack registry (vertical preset, NOT user tenant).

Importante (Fase 4 multi-tenancy refactor)
==========================================

In questo file ``tenant`` significa **Domain Pack vertical** (legal,
medical, insurance), non l'utente loggato. Il "tenant utente" vive in
:mod:`llm_wiki.auth.tenant_context` ed è un concetto ortogonale.

Naming canonico nuovo: ``PackContext``/``PackInfo``/``PackRegistry``
(vedi :mod:`llm_wiki.admin.packs`). Le classi qui dentro mantengono il
nome ``Tenant*`` per back-compat con il codice esistente; le aliases
``PackContext = TenantContext`` etc. sono esportate da ``packs.py``.

Wiki SHARED model
=================

La wiki (filesystem ``vault/wiki/``, Qdrant collection ``wiki``,
graph DB) è risorsa **condivisa** fra tutti gli utenti. ``PackContext``
non porta più ``qdrant_collection`` / ``graph_db_name`` per-pack: usano
le costanti globali ``config.COLLECTION_NAME`` / ``config.GRAPH_DB_NAME``.

Single-active runtime
=====================

Un processo = un Pack (selezionato via ``APP_DOMAIN``). Cambiare pack
richiede restart. Il wizard scrive ``APP_DOMAIN`` in ``.env`` e
schedula restart admin (vedi ``api/admin_runtime.py``).
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki.domain.pack import DomainPack
from llm_wiki.domain.registry import (
    PACK_FILENAME,
    DomainPackInvalidError,
    DomainPackNotFoundError,
)

# --- public models ---------------------------------------------------------


class TenantInfo(BaseModel):
    """Lightweight pack descriptor: enough for listing without loading
    prompts/strategies. Fast — used by the wizard's "select existing" UI.

    ``is_seed`` distinguishes engine-shipped example packs (insurance,
    legal, …) from user-scaffolded packs. The wizard groups them in
    separate sections and offers a Fork action for seeds.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    label: str
    description: str = ""
    language: str = "it"
    page_types: list[str] = Field(default_factory=list)
    pack_dir: Path
    valid: bool = True
    error: str | None = None
    is_active: bool = False
    is_seed: bool = False


class TenantContext(BaseModel):
    """Per-Pack runtime configuration (Pack = vertical preset).

    Wiki paths (``vault_root``, ``wiki_dir``, ``raw_dir``) derivano da
    un singolo root condiviso (vedi :func:`_resolve_vault_root`). Le
    costanti vector-store / graph-DB sono globali (``wiki``); l'engine
    le legge da ``config.COLLECTION_NAME``/``config.GRAPH_DB_NAME``.
    Esposte qui come property per backward-compat con i consumer
    legacy (``ctx.qdrant_collection``).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    pack: DomainPack
    vault_root: Path
    wiki_dir: Path
    raw_dir: Path
    is_active: bool = False

    @property
    def qdrant_collection(self) -> str:
        """Collection name per il Pack.

        Pack attivo → ``config.COLLECTION_NAME`` (rispetta override
        esplicito ``COLLECTION_NAME=`` in ``.env``). Pack non attivo →
        derivata ``<name>-wiki`` per non rispecchiare il nome del pack
        attivo (sarebbe fuorviante in ``GET /api/admin/tenants/{name}``).
        """
        from llm_wiki import config as _cfg

        if self.is_active:
            return _cfg.COLLECTION_NAME
        return f"{self.name}-wiki"

    @property
    def graph_db_name(self) -> str:
        """Graph DB name per il Pack. Stessa logica di ``qdrant_collection``."""
        from llm_wiki import config as _cfg

        if self.is_active:
            return _cfg.GRAPH_DB_NAME
        return f"{self.name}-wiki"

    @classmethod
    def derive(cls, *, pack: DomainPack, vault_root: Path, is_active: bool) -> TenantContext:
        return cls(
            name=pack.name,
            pack=pack,
            vault_root=vault_root,
            wiki_dir=vault_root / "wiki",
            raw_dir=vault_root / "raw",
            is_active=is_active,
        )


# --- registry --------------------------------------------------------------


class TenantRegistry:
    """Discover packs under ``domains/`` and cache loaded contexts.

    Thread-safe (single lock around the discovery cache). Cache is
    invalidated whenever :func:`refresh` is called — admin endpoints call
    it after a successful scaffold so the new pack appears immediately
    in subsequent ``/api/admin/tenants`` responses.
    """

    def __init__(self, *, domains_root: Path | None = None) -> None:
        self._domains_root = domains_root or _default_domains_root()
        self._lock = threading.Lock()
        self._cache: dict[str, TenantInfo] | None = None

    # -- discovery (lightweight) -------------------------------------------

    def list_tenants(self, *, refresh: bool = False) -> list[TenantInfo]:
        with self._lock:
            if self._cache is None or refresh:
                self._cache = _scan(self._domains_root)
            cache = dict(self._cache)
        active = self.active_name()
        return [
            TenantInfo(**{**info.model_dump(), "is_active": info.name == active})
            for info in sorted(cache.values(), key=lambda t: t.name)
        ]

    def list_user_tenants(self) -> list[TenantInfo]:
        """Tenants explicitly scaffolded by the user (``seed: false``)."""
        return [t for t in self.list_tenants() if not t.is_seed]

    def list_seed_tenants(self) -> list[TenantInfo]:
        """Engine-shipped example packs (``seed: true``)."""
        return [t for t in self.list_tenants() if t.is_seed]

    def has_user_tenants(self) -> bool:
        return any(not t.is_seed and t.valid for t in self.list_tenants())

    def setup_required(self) -> bool:
        """Whether the UI should force the setup wizard on this boot.

        Triggers when:
        - ``APP_DOMAIN`` is unset, OR
        - ``APP_DOMAIN`` resolves to an invalid pack, OR
        - ``APP_DOMAIN`` points to a seed pack (regardless of whether
          the user has scaffolded their own packs).

        White-label rule: seed packs are *never* a valid runtime
        identity. The user must explicitly fork (or pick an existing
        user pack) before the chat UI is reachable. Without this rule
        a stale ``APP_DOMAIN=insurance`` in the shell or in ``.env``
        leaks into every fresh install.
        """
        active = self.active_name()
        if not active:
            return True
        info = self.get_info(active)
        if info is None or not info.valid:
            return True
        return info.is_seed

    def get_info(self, name: str) -> TenantInfo | None:
        for info in self.list_tenants():
            if info.name == name:
                return info
        return None

    def refresh(self) -> None:
        with self._lock:
            self._cache = None

    # -- materialisation (heavy) -------------------------------------------

    def load_context(self, name: str) -> TenantContext:
        """Load the full pack and build a :class:`TenantContext`.

        Vault path lookup order:
        1. ``WIKI_ROOT_<NAME_UPPER>`` env (per-tenant override; future-proof)
        2. ``<repo>/vaults/<name>``
        """
        info = self.get_info(name)
        if info is None:
            raise DomainPackNotFoundError(f"unknown tenant: {name}")
        if not info.valid:
            raise DomainPackInvalidError(f"pack {name} invalid: {info.error}")

        # Read pack.yaml in isolation (do NOT mutate the singleton in
        # `domain.registry` — that one is the active runtime pack).
        data = _read_pack(info.pack_dir)
        data.setdefault("name", name)
        pack = DomainPack(**data)
        pack.root = info.pack_dir.resolve()

        vault_root = _resolve_vault_root(name)
        return TenantContext.derive(
            pack=pack, vault_root=vault_root, is_active=name == self.active_name()
        )

    def active_name(self) -> str:
        return os.getenv("APP_DOMAIN", "").strip()


# --- module-level singleton ------------------------------------------------

_registry: TenantRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> TenantRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = TenantRegistry()
        return _registry


def reset_registry() -> None:
    """Test-only: drop the module-level registry."""
    global _registry
    with _registry_lock:
        _registry = None


# --- helpers ---------------------------------------------------------------


def _default_domains_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "domains").exists():
            return parent / "domains"
    return here.parents[2] / "domains"


def _scan(domains_root: Path) -> dict[str, TenantInfo]:
    out: dict[str, TenantInfo] = {}
    if not domains_root.is_dir():
        return out
    for entry in sorted(domains_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("__"):
            continue
        # skip the engine-shipped scaffold; it's not a runnable tenant.
        if entry.name == "_template":
            continue
        pack_file = entry / PACK_FILENAME
        if not pack_file.is_file():
            continue
        try:
            data = _read_pack(entry)
        except (DomainPackInvalidError, OSError) as exc:
            out[entry.name] = TenantInfo(
                name=entry.name,
                label=entry.name,
                pack_dir=entry,
                valid=False,
                error=str(exc),
            )
            continue
        out[entry.name] = TenantInfo(
            name=str(data.get("name") or entry.name),
            label=str(data.get("label") or entry.name),
            description=str(data.get("description") or ""),
            language=str(data.get("language") or "it"),
            page_types=[
                str(pt.get("id"))
                for pt in (data.get("page_types") or [])
                if isinstance(pt, dict) and pt.get("id")
            ],
            pack_dir=entry,
            is_seed=bool(data.get("seed") or False),
        )
    return out


def _read_pack(pack_dir: Path) -> dict[str, Any]:
    pack_file = pack_dir / PACK_FILENAME
    try:
        with pack_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise DomainPackInvalidError(f"invalid YAML in {pack_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise DomainPackInvalidError(f"{pack_file} must contain a YAML mapping at root")
    return data


def _resolve_vault_root(name: str) -> Path:
    """Vault root del Pack.

    Priorità:
    1. ``WIKI_ROOT`` esplicito → applicato a tutti i pack (wiki SHARED).
       Questo è il path normale post-Fase 4.
    2. Per-pack legacy ``WIKI_ROOT_<NAME>`` — deprecated, lasciato per
       backward-compat con .env scritti dal vecchio scaffold. Sarà
       rimosso in una release futura.
    3. Repo-relative ``vaults/<name>/`` — fallback per dev quando nessuna
       variabile è impostata.

    Wiki SHARED: nuove deploy dovrebbero usare un singolo ``WIKI_ROOT``
    senza la per-pack key — i Pack diversi conviveranno sullo stesso
    vault, leggendo wiki condivisa con prompts/labels propri.
    """
    explicit = (os.getenv("WIKI_ROOT") or "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    env_key = f"WIKI_ROOT_{name.upper().replace('-', '_')}"
    legacy = (os.getenv(env_key) or "").strip()
    if legacy:
        return Path(legacy).expanduser().resolve()

    rr = _default_domains_root().parent
    return (rr / "vaults" / name).resolve()

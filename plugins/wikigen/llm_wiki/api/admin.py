"""Admin HTTP router: tenant discovery + scaffold wizard endpoints.

Mounted only when ``ADMIN_API_ENABLED`` is true. A loopback-only
middleware (configured in ``main.py`` for the same flag) refuses any
request from a non-local client *before* it reaches these handlers — the
endpoints assume a trusted caller and write to disk freely.

Surface
-------

``GET  /api/admin/scaffold/defaults``  — defaults derived from `_template`
``GET  /api/admin/tenants``            — list every pack under `domains/`
``GET  /api/admin/tenants/{name}``     — full context for one pack
``POST /api/admin/scaffold/preview``   — dry-run, returns ScaffoldPlan
``POST /api/admin/scaffold``           — apply, returns ScaffoldResult
``POST /api/admin/tenants/{name}/activate``
                                       — write APP_DOMAIN=<name> to .env
                                         (requires_restart=true)
``POST /api/admin/restart``            — schedule worker restart
``POST /api/admin/tenants/{name}/raw|logo|theme``
                                       — see :mod:`admin_uploads`

Tenant uploads (logo, raw deposit) and theme persistence live in
:mod:`llm_wiki.api.admin_uploads`; the restart endpoint in
:mod:`llm_wiki.api.admin_runtime`. Both are mounted on the main router
via ``include_router`` so they share the loopback gate.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from llm_wiki.admin import obsidian_init as _obs_init
from llm_wiki.admin.obsidian_init import ObsidianState
from llm_wiki.admin.scaffold import (
    ScaffoldError,
    ScaffoldPlan,
    ScaffoldRequest,
    ScaffoldResult,
    mutate_env_file,
    plan_scaffold,
    repo_root,
    scaffold_pack,
    template_dir,
)
from llm_wiki.admin.tenants import TenantInfo, get_registry
from llm_wiki.api.admin_branding import router as _branding_router
from llm_wiki.api.admin_perms import require_admin_perm
from llm_wiki.api.admin_runtime import router as _runtime_router
from llm_wiki.api.admin_uploads import router as _uploads_router
from llm_wiki.domain.registry import (
    DomainPackInvalidError,
    DomainPackNotFoundError,
    reset_pack_cache,
)

logger = logging.getLogger(__name__)


# Gating con first-boot bypass:
#
# - Postgres OFF → solo loopback (middleware in main.py). Setup mode iniziale.
# - Postgres ON + users.count > 0 → richiede ``role=admin`` via JWT.
# - Postgres ON + users.count == 0 → bypass role (catch-22: il wizard
#   serve a creare il primo admin; senza bypass nessuno può accedere).
#   Loopback hardening resta attivo dal middleware → fail-closed non-local.
def _require_admin_or_first_boot(request: Request) -> None:
    from llm_wiki import config as _cfg

    if not _cfg.POSTGRES_ENABLED:
        return
    try:
        from llm_wiki.db.users import count_users

        n = count_users()
    except Exception as exc:
        # Hardening: DB irraggiungibile NON deve bypassare il role-check.
        # Versione precedente cadeva-aperta confidando nel solo loopback,
        # ma se Postgres ha un blip transitorio + middleware loopback è
        # disabilitato per deploy con bearer, il bypass diventava
        # universale. Fail-closed: 503 finché il DB non torna su.
        logger.warning("[admin] DB unreachable, refusing admin call: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth backend non disponibile, riprova tra pochi secondi.",
        ) from exc
    if n == 0:
        # First boot: nessun admin esiste ancora → wizard accessibile per
        # creare pack. Bootstrap admin lifespan popolerà users al
        # prossimo restart, riattivando il role check.
        #
        # Hardening: anche se ``ADMIN_API_LOOPBACK_ONLY`` è disabilitato
        # (deploy con bearer-token), il bypass "no users yet" deve
        # comunque richiedere loopback. Senza questo, una finestra
        # transiente (DB appena migrato, users vuoto) esporrebbe lo
        # scaffold endpoint a chiunque sappia raggiungere l'host.
        client = request.client.host if request.client else None
        if not _client_is_loopback(client):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="first-boot wizard reachable only from loopback",
            )
        return
    from llm_wiki.auth.dependencies import require_admin

    require_admin(request)


def _client_is_loopback(host: str | None) -> bool:
    if not host:
        return False
    try:
        import ipaddress as _ip

        return _ip.ip_address(host).is_loopback
    except ValueError:
        return False


def _admin_dependencies():
    return [Depends(_require_admin_or_first_boot)]


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=_admin_dependencies(),
)
router.include_router(_uploads_router)
router.include_router(_runtime_router)
router.include_router(_branding_router)


# --- response models -------------------------------------------------------


class ScaffoldDefaults(BaseModel):
    """Suggested defaults sourced from `_template`. Lets the wizard pre-fill
    page-type chips and language without round-tripping config files."""

    languages: list[str]
    suggested_page_types: list[dict[str, str]]
    template_label: str
    template_description: str


class TenantListResponse(BaseModel):
    count: int
    active: str | None
    tenants: list[TenantInfo]


class TenantContextResponse(BaseModel):
    """Serialisable view of a TenantContext (full pack stripped down)."""

    name: str
    label: str
    is_active: bool
    vault_root: str
    wiki_dir: str
    raw_dir: str
    qdrant_collection: str
    graph_db_name: str
    page_types: list[str]
    grouping_keys: list[str]


class ActivateResponse(BaseModel):
    name: str
    requires_restart: bool = True
    env_path: str | None
    written: bool


class ObsidianStateResponse(BaseModel):
    name: str
    enabled: bool
    initialized_at: str | None = None
    initialized_by: str | None = None


# --- defaults --------------------------------------------------------------


@router.get(
    "/scaffold/defaults",
    response_model=ScaffoldDefaults,
    dependencies=[Depends(require_admin_perm("admin.scaffold"))],
)
def scaffold_defaults() -> ScaffoldDefaults:
    tpl = template_dir() / "pack.yaml"
    if not tpl.is_file():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="_template/pack.yaml missing",
        )
    try:
        data = yaml.safe_load(tpl.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"_template/pack.yaml invalid: {exc}",
        ) from exc

    suggested = [
        {"id": str(p.get("id", "")), "label": str(p.get("label", ""))}
        for p in (data.get("page_types") or [])
        if isinstance(p, dict)
    ]
    return ScaffoldDefaults(
        languages=["it", "en", "es", "fr", "de", "pt"],
        suggested_page_types=suggested,
        template_label=str(data.get("label", "Template Wiki")),
        template_description=str(data.get("description", "")),
    )


# --- tenants ---------------------------------------------------------------


@router.get(
    "/tenants",
    response_model=TenantListResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def list_tenants(refresh: bool = False) -> TenantListResponse:
    reg = get_registry()
    tenants = reg.list_tenants(refresh=refresh)
    active = reg.active_name() or None
    return TenantListResponse(count=len(tenants), active=active, tenants=tenants)


@router.get(
    "/tenants/{name}",
    response_model=TenantContextResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def get_tenant(name: str) -> TenantContextResponse:
    reg = get_registry()
    try:
        ctx = reg.load_context(name)
    except DomainPackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DomainPackInvalidError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return TenantContextResponse(
        name=ctx.name,
        label=ctx.pack.label,
        is_active=ctx.is_active,
        vault_root=str(ctx.vault_root),
        wiki_dir=str(ctx.wiki_dir),
        raw_dir=str(ctx.raw_dir),
        qdrant_collection=ctx.qdrant_collection,
        graph_db_name=ctx.graph_db_name,
        page_types=[pt.id for pt in ctx.pack.page_types],
        grouping_keys=[r.key for r in ctx.pack.grouping],
    )


@router.post(
    "/tenants/{name}/activate",
    response_model=ActivateResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def activate_tenant(name: str) -> ActivateResponse:
    """Point ``APP_DOMAIN`` at an existing pack via ``.env`` upsert.

    Single-tenant runtime: the change takes effect at the next process
    start. The wizard surfaces this in its success panel.
    """
    reg = get_registry()
    info = reg.get_info(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"tenant `{name}` not found")
    if not info.valid:
        raise HTTPException(status_code=422, detail=f"tenant `{name}` invalid: {info.error}")

    rr = repo_root()
    env_path = rr / ".env"
    template = rr / ".env.example"

    # Resolve target vault outside the lock so the read-modify-write
    # window is as short as possible. Falls back gracefully if the pack
    # context can't be loaded.
    vault_root: str | None = None
    try:
        ctx = reg.load_context(name)
        vault_root = str(ctx.vault_root)
    except Exception as exc:  # pragma: no cover — best effort sync
        logger.warning("[admin] activate: could not resolve vault for %s: %s", name, exc)

    def _mutate(base: str) -> str:
        base = _upsert(base, "APP_DOMAIN", name)
        # Realign the flat WIKI_ROOT so a stale value left over from a
        # previous activation can't shadow the new pack. Per-tenant
        # `WIKI_ROOT_<NAME>` slots stay as-is.
        if vault_root is not None:
            base = _upsert(base, "WIKI_ROOT", vault_root)
        return base

    written = mutate_env_file(env_path, _mutate, template=template)
    if not written:
        logger.warning("[admin] activate: write .env failed for %s", env_path)
    else:
        # Sync into the live process: same rationale as
        # ``scaffold._upsert_env_file`` — subsequent same-process reads
        # (registry.active_name(), TenantContext.is_active) must see
        # the new domain without waiting for a restart.
        import os as _os

        _os.environ["APP_DOMAIN"] = name
        if vault_root is not None:
            _os.environ["WIKI_ROOT"] = vault_root
        # Drop the cached DomainPack so callers after activation
        # materialise the freshly-activated pack instead of the stale
        # cache. Worker restart will rebuild it cleanly.
        try:
            reset_pack_cache()
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("[admin] reset_pack_cache failed: %s", exc)
        # Registry cache is keyed off discovery, not env, but its
        # ``is_active`` flag derives from ``os.environ["APP_DOMAIN"]``
        # at call time. Refresh anyway for callers that pass refresh=False.
        reg.refresh()

    return ActivateResponse(name=name, env_path=str(env_path), written=written)


# --- scaffold --------------------------------------------------------------


# --- obsidian per-tenant gating --------------------------------------------


def _resolve_tenant_vault(name: str) -> Path:
    reg = get_registry()
    info = reg.get_info(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"tenant `{name}` not found")
    try:
        ctx = reg.load_context(name)
    except DomainPackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DomainPackInvalidError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ctx.vault_root


def _state_response(name: str, state: ObsidianState) -> ObsidianStateResponse:
    return ObsidianStateResponse(
        name=name,
        enabled=state.enabled,
        initialized_at=state.initialized_at,
        initialized_by=state.initialized_by,
    )


def _actor_id(request: Request) -> str | None:
    """Best-effort: return the calling user id for audit trail.

    Anonymous (loopback / first-boot) calls return ``None``; the marker
    will record ``initialized_by=null`` rather than failing.
    """
    try:
        from llm_wiki.auth.dependencies import _resolve_user

        user = _resolve_user(request)
    except Exception:
        return None
    if not user:
        return None
    uid = user.get("id")
    return str(uid) if uid is not None else None


@router.get(
    "/tenants/{name}/obsidian",
    response_model=ObsidianStateResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def obsidian_status(name: str) -> ObsidianStateResponse:
    vault = _resolve_tenant_vault(name)
    return _state_response(name, _obs_init.read_state(vault))


@router.post(
    "/tenants/{name}/obsidian/init",
    response_model=ObsidianStateResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def obsidian_init(name: str, request: Request) -> ObsidianStateResponse:
    """Idempotent enable + seed `.obsidian/` for the tenant's vault."""
    vault = _resolve_tenant_vault(name)
    try:
        state = _obs_init.initialize(vault, by_user=_actor_id(request))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"filesystem error: {exc}") from exc
    return _state_response(name, state)


@router.post(
    "/tenants/{name}/obsidian/disable",
    response_model=ObsidianStateResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def obsidian_disable(name: str) -> ObsidianStateResponse:
    """Flip the per-tenant flag off without touching `.obsidian/` config."""
    vault = _resolve_tenant_vault(name)
    try:
        state = _obs_init.disable(vault)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"filesystem error: {exc}") from exc
    return _state_response(name, state)


@router.post(
    "/scaffold/preview",
    response_model=ScaffoldPlan,
    dependencies=[Depends(require_admin_perm("admin.scaffold"))],
)
def preview_scaffold(req: ScaffoldRequest) -> ScaffoldPlan:
    try:
        return plan_scaffold(req)
    except ScaffoldError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/scaffold",
    response_model=ScaffoldResult,
    dependencies=[Depends(require_admin_perm("admin.scaffold"))],
)
def apply_scaffold(req: ScaffoldRequest) -> ScaffoldResult:
    try:
        result = scaffold_pack(req)
    except ScaffoldError as exc:
        # Conflict when target already exists; bad-request otherwise.
        msg = str(exc).lower()
        code = 409 if "already exists" in msg else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"filesystem error: {exc}") from exc
    # Refresh the registry so the new pack is visible immediately.
    get_registry().refresh()
    return result


# --- helpers ---------------------------------------------------------------


_ENV_VALUE_FORBIDDEN = re.compile(r"[\r\n\x00]")


def _upsert(text: str, key: str, value: str) -> str:
    # Hardening: vedi `scaffold._upsert_env_kv` — blocca control-char nel
    # valore per impedire injection di chiavi arbitrarie nel .env.
    if _ENV_VALUE_FORBIDDEN.search(value):
        raise HTTPException(
            status_code=400,
            detail=f".env value for {key!r} contains forbidden control characters",
        )
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(f"{key}={value}", text, count=1)
    suffix = "" if (text.endswith("\n") or not text) else "\n"
    return text + suffix + f"{key}={value}\n"


# Keep mypy happy when the module is imported but never mounted.
_: Any = None

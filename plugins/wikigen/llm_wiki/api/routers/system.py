"""System status + branding endpoints.

Exposes ``/api/status`` (provider/embedder/qdrant/vault snapshot) and
``/api/branding`` (UI labels for the active Domain Pack). Both are
tolerant to "setup mode" (no ``APP_DOMAIN``) so the frontend wizard can
reach them before the first activation.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from llm_wiki import config
from llm_wiki.admin.obsidian_init import read_state as read_obsidian_state
from llm_wiki.admin.tenants import TenantContext
from llm_wiki.api.boot import BOOT_AT, BOOT_ID
from llm_wiki.api.deps import get_tenant_optional
from llm_wiki.auth.obsidian_gate import user_can_open_obsidian
from llm_wiki.domain.pack import GroupingRule
from llm_wiki.domain.registry import load_pack
from llm_wiki.graphdb.core import get_graph_db
from llm_wiki.vectorstore.contextual import is_enabled as contextual_enabled
from llm_wiki.vectorstore.embedder import dense_dim, embedder_supports_hybrid, get_embedder
from llm_wiki.vectorstore.qdrant_ops import collection_stats, get_qdrant
from llm_wiki.vectorstore.reranker import is_available as reranker_available
from llm_wiki.wiki.parser import walk_wiki

router = APIRouter()


def _is_admin_request(request: Request) -> bool:
    """Best-effort: only admin callers see filesystem paths in /api/status.

    We do NOT add a hard auth gate here — anonymous callers still get the
    feature flags + boot info needed by the public frontend / wizard.
    Sensitive fields (vault root path, qdrant URL) are stripped for
    non-admin callers via this helper.
    """
    if not config.POSTGRES_ENABLED:
        # Setup mode: no auth backend, status reachable from loopback
        # only via admin gate already; here we treat the request as
        # non-admin to keep the response minimal for any external probe.
        client = request.client.host if request.client else None
        if not client:
            return False
        try:
            import ipaddress as _ip

            return _ip.ip_address(client).is_loopback
        except ValueError:
            return False
    try:
        from llm_wiki.auth.dependencies import _resolve_user

        user = _resolve_user(request)
    except Exception:
        return False
    return bool(user) and (user or {}).get("role") == "admin"


@router.get("/api/status")
def status(request: Request) -> dict[str, Any]:
    """System health snapshot.

    Tolerant to setup mode: when no pack is active the ``domain`` block
    reports ``setup_mode=true`` instead of crashing the endpoint, so the
    StatusPill in the frontend keeps working during the wizard.
    """
    try:
        pack = load_pack()
        domain_block = {
            "name": pack.name,
            "label": pack.label,
            "language": pack.language,
            "page_types": [pt.id for pt in pack.page_types],
            "setup_mode": False,
        }
    except Exception as exc:
        domain_block = {
            "name": "",
            "label": "",
            "language": "",
            "page_types": [],
            "setup_mode": True,
            "setup_error": str(exc),
        }
    emb = get_embedder()
    graph = get_graph_db()
    is_admin = _is_admin_request(request)
    # Hardening: filesystem paths e endpoint provider sono utili in dev
    # ma sono info-leak per probe esterni (path disclosure, fingerprint
    # del cluster Qdrant). Visibili solo per admin / loopback in setup.
    qdrant_target = (
        str(config.QDRANT_PATH) if config.QDRANT_MODE == "embedded" else config.QDRANT_URL
    )
    rag_vendor = config.RAG_VENDOR or config.LLM_VENDOR
    ingest_vendor = config.INGEST_VENDOR or config.LLM_VENDOR
    provider_endpoint = config.OPENAI_API_BASE if rag_vendor == "openai" else config.OLLAMA_URL
    return {
        "domain": domain_block,
        "provider": {
            "vendor": config.LLM_VENDOR,
            "rag_vendor": rag_vendor,
            "ingest_vendor": ingest_vendor,
            "split": rag_vendor != ingest_vendor,
            "model": (config.OPENAI_MODEL if rag_vendor == "openai" else config.OLLAMA_MODEL),
            "ingest_model": (
                config.INGEST_OPENAI_MODEL
                if ingest_vendor == "openai"
                else config.INGEST_OLLAMA_MODEL
            ),
            "endpoint": provider_endpoint if is_admin else None,
        },
        "embedder": {
            "name": emb.name if emb else None,
            "dim": dense_dim(),
            "hybrid": embedder_supports_hybrid(),
        },
        "reranker": {
            "enabled": config.RERANKER_ENABLED,
            "model": config.RERANKER_MODEL,
            "available": reranker_available(),
            "input_mult": config.RERANKER_INPUT_MULT,
        },
        "contextual": {
            "enabled": config.CONTEXTUAL_ENABLED,
            "model": config.CONTEXTUAL_LLM_MODEL,
            "available": contextual_enabled(),
        },
        "qdrant": {
            "mode": config.QDRANT_MODE,
            "target": qdrant_target if is_admin else None,
            "available": get_qdrant() is not None,
            "collection": config.COLLECTION_NAME,
            **collection_stats(),
        },
        "graph": {
            "enabled": graph.is_enabled(),
            **(graph.stats() if graph.is_enabled() else {}),
        },
        "vault": {
            "root": str(config.WIKI_ROOT) if is_admin else None,
            "pages": len(walk_wiki(config.WIKI_DIR)),
        },
        "features": {
            "feedback_enabled": config.FEEDBACK_ENABLED,
        },
    }


@router.get("/api/branding/logo")
def branding_logo(
    ctx: TenantContext | None = Depends(get_tenant_optional),
) -> FileResponse:
    """Serve the active tenant's logo from ``domains/<name>/<ui.logo_path>``.

    Public — no auth gate. Tenants without a configured logo return 404
    so the frontend falls back to the static ``/branding.json`` logo.
    """
    if ctx is None:
        raise HTTPException(status_code=404, detail="no active tenant")
    rel = ctx.pack.ui.logo_path
    if not rel or not ctx.pack.root:
        raise HTTPException(status_code=404, detail="no logo configured")
    target = (ctx.pack.root / rel).resolve()
    try:
        target.relative_to(ctx.pack.root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid logo path") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="logo file missing")
    # Hardening: SVG servito come `application/octet-stream` invece di
    # `image/svg+xml`. Browser non eseguono script in octet-stream;
    # `<img src>` continua a funzionare per i logo legacy ma il file non
    # è più una superficie XSS se viene navigato direttamente.
    media = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(target.suffix.lower(), "application/octet-stream")
    return FileResponse(target, media_type=media)


@router.get("/api/branding")
def branding(
    request: Request,
    ctx: TenantContext | None = Depends(get_tenant_optional),
) -> dict[str, Any]:
    """UI labels for the active Domain Pack.

    The frontend keeps its theme (Tailwind, framer-motion, layout) and
    only swaps the copy returned here. Do **not** put colors or sizing
    in this payload — those belong in the frontend bundle.

    Multi-tenant: a request can override the resolved tenant with the
    ``X-Tenant: <slug>`` header (Phase 2). With no header and no active
    ``APP_DOMAIN`` the response carries ``setup_mode == true`` so the
    frontend can render the setup wizard instead of the chat layout.
    """
    if ctx is None:
        return _setup_mode_branding()
    pack = ctx.pack
    logo_url = "/api/branding/logo" if pack.ui.logo_path else None
    vault_name = config.OBSIDIAN_VAULT_NAME or ctx.vault_root.name
    obs_state = read_obsidian_state(ctx.vault_root)
    obsidian_block = {
        "enabled": obs_state.enabled,
        "user_can_open": obs_state.enabled and user_can_open_obsidian(request),
    }
    return {
        "domain": pack.name,
        "label": pack.label,
        "description": pack.description,
        "language": pack.language,
        "ui": pack.ui.model_dump(),
        "logo_url": logo_url,
        "page_types": [
            {"id": pt.id, "label": pt.label, "plural": pt.plural, "folder": pt.folder}
            for pt in pack.page_types
        ],
        "subtypes": pack.subtypes,
        "groups": [serialize_rule(r) for r in pack.grouping],
        "setup_mode": False,
        "tenant": {"name": ctx.name, "is_active": ctx.is_active},
        "vault": {"name": vault_name},
        "obsidian": obsidian_block,
        "boot_id": BOOT_ID,
        "boot_at": BOOT_AT,
    }


def _setup_mode_branding(error: str | None = None) -> dict[str, Any]:
    """Branding payload returned when no pack is active.

    Mirrors the live shape so the frontend doesn't need branching for the
    setup flow — only the ``setup_mode`` flag and ``domain == ""`` differ.
    """
    return {
        "domain": "",
        "label": "Wiki — Setup",
        "description": "Nessun dominio attivo. Completare il setup wizard per iniziare.",
        "language": "it",
        "ui": {
            "app_name": "Wiki — Setup",
            "short_name": "Setup",
            "vault_label": "Vault",
            "tagline": None,
            "empty_state": None,
            "page_type_labels": {},
            "extra": {},
        },
        "page_types": [],
        "subtypes": {},
        "groups": [],
        "setup_mode": True,
        "setup_error": error,
        "vault": None,
        "obsidian": {"enabled": False, "user_can_open": False},
        "boot_id": BOOT_ID,
        "boot_at": BOOT_AT,
    }


def serialize_rule(rule: GroupingRule) -> dict[str, Any]:
    return {
        "key": rule.key,
        "label": rule.label,
        "page_type": rule.page_type,
        "group_by": rule.group_by,
        "extra_fields": rule.extra_fields,
    }

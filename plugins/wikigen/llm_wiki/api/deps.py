"""Per-request FastAPI dependencies (Domain Pack resolution).

Importante (Fase 4)
===================

Qui ``tenant`` significa **Domain Pack vertical** (legal, medical,
insurance) — NON l'utente loggato. L'utente vive in
:mod:`llm_wiki.auth.dependencies` (``get_current_user``,
``require_user``, ``require_admin``).

API canonica nuova: :func:`get_pack`/:func:`get_default_pack`/
:func:`get_pack_optional`. Le vecchie ``get_tenant``/``get_default_tenant``/
``get_tenant_optional`` restano come alias zero-cost per i route handler
non ancora migrati.

Wiki SHARED
-----------

La wiki (filesystem + Qdrant + graph) è SHARED: ``PackContext`` porta
ancora ``vault_root``/``wiki_dir``/``raw_dir`` per mantenere la
compatibilità con i parser/ingest, ma in nuove deploy questi convergono
su un singolo path. Le proprietà ``qdrant_collection``/``graph_db_name``
sono shim verso ``config.COLLECTION_NAME``/``config.GRAPH_DB_NAME``.

Resolution order
----------------
1. ``X-Tenant`` request header — explicit override (smoke test, admin).
   Slug sconosciuto → 404 (no silent fallback su pack diverso).
2. ``APP_DOMAIN`` env — default di processo. Vuoto → 503 setup_required.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, status

from llm_wiki.admin.tenants import TenantContext, get_registry
from llm_wiki.domain.registry import DomainPackInvalidError, DomainPackNotFoundError


def get_default_tenant() -> TenantContext:
    """Return the tenant pinned by ``APP_DOMAIN``.

    Use this at module/import time when you need the active tenant
    without a request context (e.g. CLI commands, background workers
    started outside FastAPI). Inside HTTP handlers prefer
    :func:`get_tenant` so callers can override via ``X-Tenant``.
    """
    reg = get_registry()
    name = reg.active_name()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "setup_required",
                "message": (
                    "No active tenant. APP_DOMAIN is unset and no X-Tenant header was sent. "
                    "Complete the setup wizard or set APP_DOMAIN in .env."
                ),
            },
        )
    return _load_or_raise(name)


def get_tenant(
    x_tenant: Annotated[str | None, Header(alias="X-Tenant")] = None,
) -> TenantContext:
    """Resolve the tenant for the current request.

    Header form: ``X-Tenant: legal``. Falls back to ``APP_DOMAIN`` when
    the header is absent or empty.
    """
    name = (x_tenant or "").strip() or get_registry().active_name()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "setup_required",
                "message": (
                    "No tenant resolved. Send an X-Tenant header or set APP_DOMAIN in .env."
                ),
            },
        )
    return _load_or_raise(name)


def get_tenant_optional(
    x_tenant: Annotated[str | None, Header(alias="X-Tenant")] = None,
) -> TenantContext | None:
    """Like :func:`get_tenant` but returns ``None`` for the setup case
    (no header *and* no ``APP_DOMAIN``, *or* the active pack is a seed
    with no user pack alongside) instead of raising 503.

    Explicit unknown tenants still raise 404 — silently falling back to
    the default would mask typos and let one tenant's data leak into
    another's UI. Explicit seed slugs are honoured (preview mode for
    the wizard's "fork from this seed" UX).
    """
    explicit = (x_tenant or "").strip()
    if explicit:
        return _load_or_raise(explicit)
    reg = get_registry()
    if reg.setup_required():
        return None
    fallback = reg.active_name()
    if not fallback:
        return None
    return _load_or_raise(fallback)


def _load_or_raise(name: str) -> TenantContext:
    reg = get_registry()
    try:
        return reg.load_context(name)
    except DomainPackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"unknown tenant: {name}") from exc
    except DomainPackInvalidError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# --- canonical naming aliases (Fase 4) -------------------------------------
#
# I nomi ``get_pack*`` riflettono la semantica reale (Pack = vertical
# preset, NON utente). Identici behaviour alle versioni ``get_tenant*``;
# nuovo codice usi le aliases ``pack``.

get_pack = get_tenant
get_default_pack = get_default_tenant
get_pack_optional = get_tenant_optional


__all__ = [
    "get_default_tenant",
    "get_tenant",
    "get_tenant_optional",
    "get_pack",
    "get_default_pack",
    "get_pack_optional",
]

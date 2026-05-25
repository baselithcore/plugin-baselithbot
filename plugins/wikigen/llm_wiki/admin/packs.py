"""Canonical naming per Domain Pack registry (Fase 4 refactor).

Riesporta i simboli di :mod:`llm_wiki.admin.tenants` con nomi
``Pack*`` invece di ``Tenant*`` — clarifies che il "tenant" qui è il
preset verticale (legal/medical), non l'utente loggato (che vive in
:mod:`llm_wiki.auth.tenant_context`).

Nuovi consumer dovrebbero importare da qui:

    from llm_wiki.admin.packs import PackContext, get_registry

I simboli ``Tenant*`` legacy restano funzionanti — questo modulo è
solo aliasing zero-cost senza deprecation warning, da rimuovere in
release futura solo quando tutti gli import sites sono migrati.
"""

from __future__ import annotations

# Mantieni i nomi originali esposti anche da qui, così un consumer può
# fare ``from llm_wiki.admin.packs import TenantContext`` senza che
# lo splitting cognitivo rompa la migration.
from llm_wiki.admin.tenants import (  # noqa: F401
    DomainPackInvalidError,
    DomainPackNotFoundError,
    TenantContext,
    TenantInfo,
    TenantRegistry,
    get_registry,
    reset_registry,
)
from llm_wiki.admin.tenants import (
    TenantContext as PackContext,
)
from llm_wiki.admin.tenants import (
    TenantInfo as PackInfo,
)
from llm_wiki.admin.tenants import (
    TenantRegistry as PackRegistry,
)

__all__ = [
    "PackContext",
    "PackInfo",
    "PackRegistry",
    "TenantContext",
    "TenantInfo",
    "TenantRegistry",
    "DomainPackInvalidError",
    "DomainPackNotFoundError",
    "get_registry",
    "reset_registry",
]

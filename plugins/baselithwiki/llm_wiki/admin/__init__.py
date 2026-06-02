"""Admin-side surfaces of the engine: scaffolding new Domain Packs and
discovering installed tenants.

These modules never run during normal request handling. They are mounted
behind ``ADMIN_API_ENABLED`` (and a loopback-only middleware) and are the
only place in the engine that mutates ``domains/`` and ``.env`` on disk.

Public API
----------
``scaffold_pack``  — pure function: copy ``_template`` → ``domains/<name>/``,
                     customise ``pack.yaml``, prepare vault dirs, optionally
                     upsert ``.env``. Idempotent unless ``force=True``.
``TenantRegistry`` — discover packs on disk and materialise per-tenant
                     :class:`TenantContext` objects. Phase 1 uses it for
                     listing/scaffolding only; phase 2 will route requests
                     through it.
"""

from llm_wiki.admin.scaffold import (
    ScaffoldError,
    ScaffoldPlan,
    ScaffoldRequest,
    ScaffoldResult,
    plan_scaffold,
    scaffold_pack,
)
from llm_wiki.admin.tenants import (
    TenantContext,
    TenantInfo,
    TenantRegistry,
    get_registry,
)

__all__ = [
    "ScaffoldError",
    "ScaffoldPlan",
    "ScaffoldRequest",
    "ScaffoldResult",
    "TenantContext",
    "TenantInfo",
    "TenantRegistry",
    "get_registry",
    "plan_scaffold",
    "scaffold_pack",
]

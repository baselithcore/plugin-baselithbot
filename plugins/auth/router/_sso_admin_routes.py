"""Admin CRUD for SSO identity providers. Secrets are encrypted at rest and
never returned to the client."""

import re

from fastapi import APIRouter, Depends, HTTPException

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.dependencies import get_auth_persistence_dep, require_admin
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._models import (
    MessageResponse,
    SsoProviderOut,
    SsoProviderUpsert,
)
from plugins.auth.sso import encrypt_secret

logger = get_logger(__name__)

router = APIRouter(prefix="/sso/admin")

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$")


def _to_out(row: dict) -> SsoProviderOut:
    return SsoProviderOut(
        id=str(row["id"]),
        slug=row["slug"],
        name=row["name"],
        protocol=row["protocol"],
        enabled=bool(row.get("enabled", True)),
        auto_provision=bool(row.get("auto_provision", True)),
        config=row.get("config") or {},
        default_roles=list(row.get("default_roles") or []),
        has_secret=bool(row.get("has_secret")),
    )


@router.get("/providers", response_model=list[SsoProviderOut])
async def list_providers(
    _: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """List all configured providers (admin)."""
    return [_to_out(p) for p in persistence.list_sso_providers()]


@router.put("/providers/{slug}", response_model=SsoProviderOut)
async def upsert_provider(
    slug: str,
    body: SsoProviderUpsert,
    _: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Create or update a provider. Omit ``secret`` to keep the existing one."""
    if not _SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="Invalid slug (a-z, 0-9, hyphens)")
    row = persistence.upsert_sso_provider(
        slug=slug,
        name=body.name,
        protocol=body.protocol,
        config=body.config,
        secret_enc=encrypt_secret(body.secret) if body.secret else None,
        default_roles=body.default_roles,
        enabled=body.enabled,
        auto_provision=body.auto_provision,
    )
    logger.info("SSO provider upserted: %s (%s)", slug, body.protocol)
    out = persistence.get_sso_provider(slug) or row
    out["has_secret"] = bool(out.get("secret_enc"))
    return _to_out(out)


@router.delete("/providers/{slug}", response_model=MessageResponse)
async def delete_provider(
    slug: str,
    _: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Delete a provider and its linked identities."""
    if not persistence.delete_sso_provider(slug):
        raise HTTPException(status_code=404, detail="Provider not found")
    return MessageResponse(message="Provider deleted.")

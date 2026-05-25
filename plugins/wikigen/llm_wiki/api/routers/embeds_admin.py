"""Embed admin endpoints — CRUD + rotate token (mig 017).

Surface
-------

``GET    /api/admin/embeds``             — list (tenant del caller)
``POST   /api/admin/embeds``             — create (ritorna plaintext UNA volta)
``GET    /api/admin/embeds/{eid}``       — detail (NO plaintext)
``PATCH  /api/admin/embeds/{eid}``       — edit allowlist/theme/limits/...
``DELETE /api/admin/embeds/{eid}``       — hard delete
``POST   /api/admin/embeds/{eid}/rotate-token``  — nuovo token, vecchio invalida

Gating: ``admin.embed.manage`` (mig 017, seed superuser+admin).
Audit: ``embed.{created,updated,deleted,token.rotated}``.

Cross-tenant: ogni mutation usa ``tenant_id = actor.tenant_id``; 404 se
embed id non appartiene al tenant del caller (no info leak).
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import require_permission
from llm_wiki.auth.permissions import Permission
from llm_wiki.db import embeds as embeds_db

logger = logging.getLogger(__name__)


_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_ORIGIN_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9._-]+(?::\d{1,5})?$",
)


# --- models ---------------------------------------------------------------


class EmbedSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    slug: str
    name: str
    description: str = ""
    tenant_id: str
    token_prefix: str
    origin_allowlist: list[str] = Field(default_factory=list)
    theme: dict = Field(default_factory=dict)
    welcome_message: str = ""
    suggested_questions: list[str] = Field(default_factory=list)
    rate_limit_per_minute: int = 30
    is_enabled: bool = True
    created_by: str | None = None
    last_used_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class EmbedWithToken(EmbedSummary):
    """Response per create/rotate — include plaintext UNA volta sola."""

    embed_token: str


def _validate_origins(origins: list[str]) -> list[str]:
    out: list[str] = []
    for raw in origins:
        candidate = (raw or "").strip().rstrip("/")
        if not candidate:
            continue
        if not _ORIGIN_PATTERN.match(candidate):
            raise ValueError(
                f"origin non valido: {raw!r}. Atteso 'https://host[:port]' senza path."
            )
        out.append(candidate)
    # Dedup preservando ordine.
    seen: set[str] = set()
    deduped: list[str] = []
    for o in out:
        if o not in seen:
            seen.add(o)
            deduped.append(o)
    return deduped


class CreateEmbedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    origin_allowlist: list[str] = Field(default_factory=list, max_length=20)
    theme: dict = Field(default_factory=dict)
    welcome_message: str = Field(default="", max_length=500)
    suggested_questions: list[str] = Field(default_factory=list, max_length=8)
    rate_limit_per_minute: int = Field(default=30, ge=0, le=600)

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not _SLUG_PATTERN.match(v):
            raise ValueError("slug deve iniziare con [a-z0-9] e usare solo [a-z0-9._-]")
        return v

    @field_validator("origin_allowlist")
    @classmethod
    def _origins(cls, v: list[str]) -> list[str]:
        return _validate_origins(v)


class UpdateEmbedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    origin_allowlist: list[str] | None = Field(default=None, max_length=20)
    theme: dict | None = None
    welcome_message: str | None = Field(default=None, max_length=500)
    suggested_questions: list[str] | None = Field(default=None, max_length=8)
    rate_limit_per_minute: int | None = Field(default=None, ge=0, le=600)
    is_enabled: bool | None = None

    @field_validator("origin_allowlist")
    @classmethod
    def _origins(cls, v: list[str] | None) -> list[str] | None:
        return _validate_origins(v) if v is not None else None


# --- router ---------------------------------------------------------------


router = APIRouter(
    prefix="/api/admin/embeds",
    tags=["admin", "embeds"],
    dependencies=[Depends(require_permission(Permission.ADMIN_EMBED_MANAGE, rate_limit="admin"))],
)


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def _require_embed(embed_id: str, actor: dict) -> dict:
    embed = embeds_db.get_embed_by_id(embed_id, tenant_id=actor.get("tenant_id"))
    if not embed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="embed non trovato")
    return embed


@router.get("", response_model=list[EmbedSummary])
def list_embeds_endpoint(
    actor: dict = Depends(require_permission(Permission.ADMIN_EMBED_MANAGE, rate_limit="admin")),
) -> list[EmbedSummary]:
    tenant_id = actor.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context assente per il caller.",
        )
    rows = embeds_db.list_embeds(tenant_id)
    return [EmbedSummary(**r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=EmbedWithToken)
def create_embed_endpoint(
    body: CreateEmbedRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_EMBED_MANAGE, rate_limit="admin")),
) -> EmbedWithToken:
    tenant_id = actor.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context assente per il caller.",
        )
    try:
        record, plaintext = embeds_db.create_embed(
            tenant_id=tenant_id,
            slug=body.slug,
            name=body.name,
            description=body.description,
            origin_allowlist=body.origin_allowlist,
            theme=body.theme,
            welcome_message=body.welcome_message,
            suggested_questions=body.suggested_questions,
            rate_limit_per_minute=body.rate_limit_per_minute,
            created_by=actor["id"],
        )
    except Exception as exc:
        if "uq_embeds_tenant_slug" in str(exc) or "duplicate key" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"slug '{body.slug}' già usato in questo tenant",
            ) from exc
        raise
    write_event(
        "embed.created",
        tenant_id=tenant_id,
        user_id=actor["id"],
        payload={
            "embed_id": record["id"],
            "slug": record["slug"],
            "origins": record["origin_allowlist"],
        },
        ip_address=_client_ip(request),
    )
    return EmbedWithToken(**record, embed_token=plaintext)


@router.get("/{embed_id}", response_model=EmbedSummary)
def get_embed_endpoint(
    embed_id: str,
    actor: dict = Depends(require_permission(Permission.ADMIN_EMBED_MANAGE, rate_limit="admin")),
) -> EmbedSummary:
    embed = _require_embed(embed_id, actor)
    return EmbedSummary(**embed)


@router.patch("/{embed_id}", response_model=EmbedSummary)
def update_embed_endpoint(
    embed_id: str,
    body: UpdateEmbedRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_EMBED_MANAGE, rate_limit="admin")),
) -> EmbedSummary:
    _require_embed(embed_id, actor)
    tenant_id = actor["tenant_id"]
    updated = embeds_db.update_embed(
        embed_id,
        tenant_id,
        name=body.name,
        description=body.description,
        origin_allowlist=body.origin_allowlist,
        theme=body.theme,
        welcome_message=body.welcome_message,
        suggested_questions=body.suggested_questions,
        rate_limit_per_minute=body.rate_limit_per_minute,
        is_enabled=body.is_enabled,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="embed non trovato")
    write_event(
        "embed.updated",
        tenant_id=tenant_id,
        user_id=actor["id"],
        payload={
            "embed_id": embed_id,
            "fields": {k: v for k, v in body.model_dump(exclude_none=True).items()},
        },
        ip_address=_client_ip(request),
    )
    return EmbedSummary(**updated)


@router.delete("/{embed_id}", status_code=status.HTTP_200_OK)
def delete_embed_endpoint(
    embed_id: str,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_EMBED_MANAGE, rate_limit="admin")),
) -> dict:
    embed = _require_embed(embed_id, actor)
    removed = embeds_db.delete_embed(embed_id, actor["tenant_id"])
    write_event(
        "embed.deleted",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={"embed_id": embed_id, "slug": embed["slug"], "noop": not removed},
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "removed": removed}


@router.post("/{embed_id}/rotate-token", response_model=EmbedWithToken)
def rotate_token_endpoint(
    embed_id: str,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_EMBED_MANAGE, rate_limit="admin")),
) -> EmbedWithToken:
    _require_embed(embed_id, actor)
    rotated = embeds_db.rotate_token(embed_id, actor["tenant_id"])
    if not rotated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="embed non trovato")
    record, plaintext = rotated
    write_event(
        "embed.token.rotated",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={"embed_id": embed_id, "slug": record["slug"]},
        ip_address=_client_ip(request),
    )
    return EmbedWithToken(**record, embed_token=plaintext)


__all__ = ["router"]

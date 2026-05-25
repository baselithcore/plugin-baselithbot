"""Tenant branding edit — admin sub-router.

Surface
-------

``GET  /api/admin/tenants/{name}/branding`` — current pack.yaml branding
``PUT  /api/admin/tenants/{name}/branding`` — patch label/description + UI labels

Mutates the on-disk ``pack.yaml`` via YAML round-trip (PyYAML
``safe_load`` → mutate → ``safe_dump``). Re-validates the entire pack
through :class:`DomainPack` before writing so a bad edit can never
corrupt the file. Refreshes the live registry + drops the cached pack
so the active tenant picks up changes without a restart.

Note: logo asset upload and theme color persistence live in
:mod:`admin_uploads` — kept there because they touch the filesystem
(assets dir) on top of pack.yaml.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki.admin.tenants import TenantInfo, get_registry
from llm_wiki.api.admin_perms import require_admin_perm
from llm_wiki.domain.pack import DomainPack, UISuggestedQuestion
from llm_wiki.domain.registry import reset_pack_cache

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_tenant_or_404(name: str) -> TenantInfo:
    info = get_registry().get_info(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"tenant `{name}` not found")
    if not info.valid:
        raise HTTPException(status_code=422, detail=f"tenant `{name}` invalid: {info.error}")
    return info


def _load_pack_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"cannot read pack.yaml: {exc}") from exc
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=500, detail=f"pack.yaml invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="pack.yaml: top level is not a mapping")
    return data


class BrandingReadResponse(BaseModel):
    name: str
    label: str
    description: str
    ui: dict[str, Any]


class BrandingUpdateRequest(BaseModel):
    """All fields optional; missing keys leave the existing value intact."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    app_name: str | None = Field(default=None, min_length=1, max_length=128)
    short_name: str | None = Field(default=None, max_length=64)
    vault_label: str | None = Field(default=None, max_length=64)
    tagline: str | None = Field(default=None, max_length=160)
    empty_state: str | None = Field(default=None, max_length=400)
    hero_question: str | None = Field(default=None, max_length=160)
    hero_highlight: str | None = Field(default=None, max_length=160)
    hero_pill: str | None = Field(default=None, max_length=120)
    hero_pill_icon: str | None = Field(default=None, max_length=64)
    disclaimer: str | None = Field(default=None, max_length=600)
    suggested_questions: list[UISuggestedQuestion] | None = Field(default=None, max_length=8)


_TOP_LEVEL_KEYS = ("label", "description")
_UI_KEYS = (
    "app_name",
    "short_name",
    "vault_label",
    "tagline",
    "empty_state",
    "hero_question",
    "hero_highlight",
    "hero_pill",
    "hero_pill_icon",
    "disclaimer",
)


def _apply_patch(data: dict[str, Any], req: BrandingUpdateRequest) -> dict[str, Any]:
    """In-place mutation of the parsed pack.yaml dict. Empty strings clear
    optional fields (set to None); ``None`` from the request leaves the
    field untouched."""
    for key in _TOP_LEVEL_KEYS:
        v = getattr(req, key)
        if v is None:
            continue
        data[key] = v

    ui = data.get("ui")
    if not isinstance(ui, dict):
        ui = {}
        data["ui"] = ui

    for key in _UI_KEYS:
        v = getattr(req, key)
        if v is None:
            continue
        if v == "" and key != "app_name":
            # Empty string = explicit clear for optional fields. app_name
            # is required, so silently ignore an empty submission.
            ui.pop(key, None)
        else:
            ui[key] = v

    if req.suggested_questions is not None:
        ui["suggested_questions"] = [
            q.model_dump(exclude_none=False) for q in req.suggested_questions
        ]
    return data


@router.get(
    "/tenants/{name}/branding",
    response_model=BrandingReadResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def read_tenant_branding(name: str) -> BrandingReadResponse:
    info = _resolve_tenant_or_404(name)
    data = _load_pack_yaml(info.pack_dir / "pack.yaml")
    raw_ui = data.get("ui")
    ui: dict[str, Any] = dict(raw_ui) if isinstance(raw_ui, dict) else {}
    return BrandingReadResponse(
        name=info.name,
        label=str(data.get("label", "")),
        description=str(data.get("description", "")),
        ui=ui,
    )


@router.put(
    "/tenants/{name}/branding",
    response_model=BrandingReadResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def update_tenant_branding(name: str, req: BrandingUpdateRequest) -> BrandingReadResponse:
    info = _resolve_tenant_or_404(name)
    pack_yaml = info.pack_dir / "pack.yaml"
    data = _load_pack_yaml(pack_yaml)

    patched = _apply_patch(dict(data), req)

    # Full re-validation via the pydantic contract — guarantees the
    # on-disk pack stays loadable. Failing here aborts before write.
    try:
        DomainPack(**patched)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid branding patch: {exc}") from exc

    try:
        dumped = yaml.safe_dump(
            patched,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=4096,
        )
        pack_yaml.write_text(dumped, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"cannot write pack.yaml: {exc}") from exc

    # Live process picks up the change without restart: drop cached pack
    # + refresh tenants registry. The active tenant's TenantContext is
    # cache-busted on next access.
    try:
        reset_pack_cache()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("[admin] reset_pack_cache after branding edit failed: %s", exc)
    get_registry().refresh()

    raw_ui = patched.get("ui")
    ui: dict[str, Any] = dict(raw_ui) if isinstance(raw_ui, dict) else {}
    return BrandingReadResponse(
        name=info.name,
        label=str(patched.get("label", "")),
        description=str(patched.get("description", "")),
        ui=ui,
    )

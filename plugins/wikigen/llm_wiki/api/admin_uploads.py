"""Tenant uploads + theme persistence (admin sub-router).

Endpoints scoped under ``/api/admin/tenants/{name}/...`` that mutate
files inside ``domains/<name>/`` (logo asset, raw deposit) or
``pack.yaml`` (logo path, theme block). Mounted on the main admin
router via ``include_router`` so they keep the same loopback gate.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from llm_wiki.admin.tenants import TenantInfo, get_registry
from llm_wiki.api.admin_perms import require_admin_perm
from llm_wiki.config import INGEST_SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

router = APIRouter()


# Hardening: SVG rimossi dall'allowlist. Un SVG può contenere
# `<script>` / `<foreignObject>` ed eseguire JS quando il browser lo
# carica come top-level navigation o `<object>` — XSS persistente sotto
# l'origin del wizard. PNG/WEBP/JPG/JPEG bastano per il logo branding.
# Per riabilitare SVG, sanificarlo lato server (es. defusedxml + strip
# di tag/attributi pericolosi) prima di accettarlo.
ALLOWED_LOGO_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
# Multi-format: derived dall'env ``INGEST_SUPPORTED_EXTENSIONS`` per
# tenere router upload e pipeline ingest allineati. PDF resta sempre
# supportato anche se l'env non lo include (fallback safety).
ALLOWED_RAW_EXTS: set[str] = set(INGEST_SUPPORTED_EXTENSIONS) | {".pdf"}
MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_RAW_BYTES = 50 * 1024 * 1024
_SAFE_FILENAME_RE = re.compile(r"[^a-z0-9._-]+")


def _sanitize_filename(name: str, allowed: set[str]) -> str:
    if not name or "\x00" in name:
        raise HTTPException(status_code=400, detail="invalid filename")
    name = Path(name).name
    norm = unicodedata.normalize("NFKD", name)
    ascii_ = norm.encode("ascii", "ignore").decode("ascii")
    base, _, ext = ascii_.rpartition(".")
    if not base:
        base = ascii_
        ext = ""
    base = _SAFE_FILENAME_RE.sub("-", base.lower()).strip("-")
    ext = ext.lower()
    if not base:
        raise HTTPException(status_code=400, detail="filename empty after sanitisation")
    if not ext or f".{ext}" not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"extension `.{ext}` not allowed. Allowed: {sorted(allowed)}",
        )
    return f"{base}.{ext}"


def _resolve_tenant_or_404(name: str) -> TenantInfo:
    """Return the validated TenantInfo or raise 404/422."""
    info = get_registry().get_info(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"tenant `{name}` not found")
    if not info.valid:
        raise HTTPException(status_code=422, detail=f"tenant `{name}` invalid: {info.error}")
    return info


async def _stream_to_disk(file: UploadFile, target: Path, *, max_bytes: int) -> int:
    """Stream upload to disk, enforcing ``max_bytes``. Returns bytes written.
    Cleans up the partial file on overflow."""
    bytes_read = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_read += len(chunk)
                if bytes_read > max_bytes:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"file too large (> {max_bytes // (1024 * 1024)} MB)",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"upload failed: {exc}") from exc
    return bytes_read


class TenantUploadResponse(BaseModel):
    name: str
    filename: str
    size: int
    target_path: str


@router.post(
    "/tenants/{name}/raw",
    response_model=TenantUploadResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
async def upload_tenant_raw(
    name: str,
    file: UploadFile = File(...),
    overwrite: bool = Form(False),
) -> TenantUploadResponse:
    """Deposit a PDF directly into ``<vault>/raw/`` of a scaffolded tenant.

    Used by the wizard's "Documenti" step: the user picks files while
    creating the wiki, and they land in the new tenant's vault before
    the backend restart so the first chat session can immediately ingest
    them. No ingestion is triggered here — that requires the runtime
    pack load (single-tenant) which only happens after restart.
    """
    info = _resolve_tenant_or_404(name)
    ctx = get_registry().load_context(info.name)
    raw_dir = ctx.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    if file.filename is None:
        raise HTTPException(status_code=400, detail="missing filename")
    safe = _sanitize_filename(file.filename, ALLOWED_RAW_EXTS)
    target = (raw_dir / safe).resolve()
    try:
        target.relative_to(raw_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid path") from exc
    if target.exists() and not overwrite:
        raise HTTPException(
            status_code=409,
            detail=f"`{safe}` already in raw/. Send overwrite=true to replace.",
        )
    bytes_read = await _stream_to_disk(file, target, max_bytes=MAX_RAW_BYTES)
    return TenantUploadResponse(
        name=info.name,
        filename=safe,
        size=bytes_read,
        target_path=str(target),
    )


@router.post(
    "/tenants/{name}/logo",
    response_model=TenantUploadResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
async def upload_tenant_logo(name: str, file: UploadFile = File(...)) -> TenantUploadResponse:
    """Save a logo into ``domains/<name>/assets/`` and update
    ``pack.yaml ui.logo_path`` to reference it.

    The frontend serves logos from a dedicated read-only endpoint (Phase 3);
    for now the path is stored as ``assets/<safe-filename>`` so the user
    can copy it to ``frontend/public/`` manually if needed.
    """
    info = _resolve_tenant_or_404(name)
    if file.filename is None:
        raise HTTPException(status_code=400, detail="missing filename")
    safe = _sanitize_filename(file.filename, ALLOWED_LOGO_EXTS)

    assets_dir = info.pack_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    target = (assets_dir / safe).resolve()
    try:
        target.relative_to(assets_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid path") from exc
    bytes_read = await _stream_to_disk(file, target, max_bytes=MAX_LOGO_BYTES)

    # update pack.yaml ui.logo_path so /api/branding picks it up after restart.
    pack_yaml = info.pack_dir / "pack.yaml"
    try:
        text = pack_yaml.read_text(encoding="utf-8")
        rel = f"assets/{safe}"
        if "logo_path:" in text:
            text = re.sub(r"^(\s*logo_path:)[^\n]*$", rf'\1 "{rel}"', text, count=1, flags=re.M)
        else:
            # insert under the `ui:` block. crude but stable for our YAML shape.
            text = re.sub(
                r"^(ui:[^\n]*\n)",
                rf'\1  logo_path: "{rel}"\n',
                text,
                count=1,
                flags=re.M,
            )
        pack_yaml.write_text(text, encoding="utf-8")
        get_registry().refresh()
    except OSError as exc:
        logger.warning("[admin] could not update pack.yaml after logo upload: %s", exc)

    return TenantUploadResponse(
        name=info.name,
        filename=safe,
        size=bytes_read,
        target_path=str(target),
    )


class ThemeUpdateRequest(BaseModel):
    primary: str | None = None
    primary_hover: str | None = None
    accent: str | None = None


@router.post(
    "/tenants/{name}/theme",
    response_model=dict[str, Any],
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def update_tenant_theme(name: str, req: ThemeUpdateRequest) -> dict[str, Any]:
    """Persist ``ui.theme`` in pack.yaml. Validates hex colors."""
    info = _resolve_tenant_or_404(name)
    hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
    for key in ("primary", "primary_hover", "accent"):
        v = getattr(req, key)
        if v is not None and not hex_re.match(v):
            raise HTTPException(status_code=400, detail=f"{key}: invalid hex color")

    pack_yaml = info.pack_dir / "pack.yaml"
    try:
        text = pack_yaml.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"cannot read pack.yaml: {exc}") from exc

    # Build the theme block we want to inject under `ui:`.
    block_lines = ["  theme:"]
    if req.primary:
        block_lines.append(f'    primary: "{req.primary}"')
    if req.primary_hover:
        block_lines.append(f'    primary_hover: "{req.primary_hover}"')
    if req.accent:
        block_lines.append(f'    accent: "{req.accent}"')
    block = "\n".join(block_lines) + "\n"

    if re.search(r"^\s+theme:", text, flags=re.M):
        # replace existing theme block (matches the indented `theme:` plus its children).
        text = re.sub(
            r"^\s+theme:\n(?:    [^\n]*\n)*",
            block,
            text,
            count=1,
            flags=re.M,
        )
    else:
        text = re.sub(r"^(ui:[^\n]*\n)", rf"\1{block}", text, count=1, flags=re.M)

    pack_yaml.write_text(text, encoding="utf-8")
    get_registry().refresh()
    return {"name": info.name, "theme": req.model_dump(exclude_none=True)}

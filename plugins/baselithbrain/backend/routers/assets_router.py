"""Attachment upload + serve endpoints.

Images are uploaded to the vault's ``_assets/`` dir and served back by
content-addressed name. The SPA stores portable ``_assets/<name>`` paths in the
Markdown and swaps them for these URLs only at display time.

Security: the accepted type is decided by **sniffing the payload's magic
bytes**, never by the client-supplied ``Content-Type``. Only raster formats are
allowed — SVG is intentionally rejected (it is an XSS vector when served inline).
Served responses are additionally locked down with ``nosniff`` and a
deny-all CSP/sandbox so a mislabeled file can never execute in the app origin.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from ..attachments import AttachmentStore
from ..config_proxy import get_settings

router = APIRouter(prefix="/api/assets", tags=["assets"])

_MAX_BYTES = 10 * 1024 * 1024  # 10 MiB

# Hardened serve headers: never sniff, never execute, never reach app cookies.
_SAFE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox",
    "Cache-Control": "private, max-age=31536000, immutable",
}


def _sniff_image(data: bytes) -> str | None:
    """Return a safe media type from magic bytes, or ``None`` if not a raster.

    Decided from the payload only — the client ``Content-Type`` is never
    trusted. SVG/XML and everything else map to ``None`` (rejected).
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _store() -> AttachmentStore:
    return AttachmentStore(get_settings().vault_root)


@router.post("", status_code=201)
async def upload_asset(file: UploadFile = File(...)) -> dict[str, str]:
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large (max 10 MiB)")
    media = _sniff_image(data)
    if media is None:
        raise HTTPException(
            status_code=415, detail="unsupported type (only png/jpeg/gif/webp images)"
        )
    name = _store().save(file.filename or "image", data, media)
    return {"name": name, "path": f"_assets/{name}", "url": f"api/assets/{name}"}


@router.get("/{name}")
async def get_asset(name: str) -> Response:
    store = _store()
    try:
        if not store.exists(name):
            raise HTTPException(status_code=404, detail="asset not found")
        data = store.read(name)
    except ValueError as exc:  # invalid / traversal name
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Re-sniff on the way out so the served Content-Type can never be an
    # executable/active type, regardless of how the file landed on disk.
    media = _sniff_image(data) or "application/octet-stream"
    return Response(content=data, media_type=media, headers=_SAFE_HEADERS)

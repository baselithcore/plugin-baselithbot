"""Binary / file upload + static-analysis scan endpoints.

Operators upload an executable, document, or archive; the file is
quarantined under ``runtime/quarantine/<sha256>/`` with restricted
permissions, then a scan is dispatched against
``Target(type=BINARY, value=sha256)`` using the ``binary_analyzer``
scanner. The sample is **never executed** — the analyzer parses bytes
in-process.

Limits:
  • Max upload size: 256 MiB (matches the analyzer cap).
  • MIME / extension allowlist drawn from common reverse-engineering
    targets (PE, ELF, Mach-O, Office, PDF, archives, scripts).

Reuses the existing scan pipeline so findings, audit, RBAC, SLA,
graph-pivot and UI listing all work out of the box.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)

from core.context import get_current_tenant_id
from core.observability.logging import get_logger
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.dependencies import (
    get_red_agent,
    require_security_operator,
    require_viewer,
)
from plugins.red_agent.guardrails import GuardrailViolation
from plugins.red_agent.models import (
    ScanIntensity,
    ScanRequest,
    Target,
    TargetType,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/file-scans", tags=["red-agent"])

# 256 MiB cap shared with ``binary_analyzer._MAX_BYTES``.
_MAX_UPLOAD_BYTES = 256 * 1024 * 1024

# Read in 4 MiB chunks so a malicious upload cannot pin a worker on a
# single ``read()`` and we can stop early once the cap is exceeded.
_CHUNK = 4 * 1024 * 1024

# Extension allowlist. Anything else is rejected before quarantine to
# limit the attack surface (no .lnk, .url, .scf shortcut tricks etc.).
# Traffic Light Protocol markings — operators tag the sample's sharing
# class so downstream IOC export can honour disclosure constraints.
# Default WHITE for permissive labs; production operators must override.
_VALID_TLP = {"clear", "white", "green", "amber", "amber+strict", "red"}

_ALLOWED_SUFFIXES = {
    ".exe",
    ".dll",
    ".sys",
    ".ocx",
    ".cpl",
    ".scr",
    ".so",
    ".out",
    ".bin",
    ".elf",
    ".dylib",
    ".macho",
    ".apk",
    ".jar",
    ".class",
    ".dex",
    ".pyc",
    ".ps1",
    ".vbs",
    ".js",
    ".bat",
    ".cmd",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".pdf",
    ".rtf",
    ".zip",
    ".7z",
    ".tar",
    ".gz",
    ".rar",
    ".iso",
    ".img",
}


def _quarantine_root() -> Path:
    """Resolve the quarantine root, honouring ``RED_AGENT_QUARANTINE_DIR``."""
    override = os.environ.get("RED_AGENT_QUARANTINE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.cwd() / "runtime" / "quarantine").resolve()


def _validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if not suffix:
        raise HTTPException(400, "filename must include an extension")
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            415,
            f"extension {suffix!r} is not in the allowlist; "
            f"accepted: {sorted(_ALLOWED_SUFFIXES)}",
        )
    return suffix


async def _stream_to_quarantine(upload: UploadFile, dest: Path) -> tuple[int, str]:
    """Write the upload to ``dest`` while computing its SHA-256.

    Returns ``(bytes_written, sha256_hex)``. Raises ``HTTPException`` if
    the upload exceeds the size cap; the partial file is unlinked first.
    """
    digest = hashlib.sha256()
    written = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Restrictive umask before file create so the inode is born 0600.
    prev = os.umask(0o077)
    try:
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC, 0o600)
        try:
            while True:
                chunk = await upload.read(_CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > _MAX_UPLOAD_BYTES:
                    os.close(fd)
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        413,
                        f"upload exceeds {_MAX_UPLOAD_BYTES} byte cap",
                    )
                digest.update(chunk)
                os.write(fd, chunk)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
    finally:
        os.umask(prev)
    return written, digest.hexdigest()


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[require_security_operator()],
)
async def upload_and_scan(
    http_request: Request,
    file: UploadFile = File(...),
    engagement_id: UUID | None = Form(default=None),
    notes: str | None = Form(default=None),
    tlp: str = Form(default="amber"),
    source: str | None = Form(default=None),
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, str | int]:
    """Quarantine an uploaded sample and dispatch the binary analyzer.

    The response carries the sha256 (so the UI can pivot to the report
    even before the scan completes) and the scan_id (for status polling
    and the WebSocket stream).
    """
    if not file.filename:
        raise HTTPException(400, "filename required")
    tlp_norm = tlp.lower().strip()
    if tlp_norm not in _VALID_TLP:
        raise HTTPException(
            400,
            f"tlp {tlp!r} invalid — accepted: {sorted(_VALID_TLP)}",
        )
    suffix = _validate_extension(file.filename)

    # Stage to a temp path under the quarantine root, then rename to the
    # canonical sha256-keyed path so concurrent uploads of the same file
    # cannot race on the same destination.
    qroot = _quarantine_root()
    qroot.mkdir(parents=True, exist_ok=True, mode=0o700)
    staging = qroot / f".incoming-{os.getpid()}-{id(file)}{suffix}"

    try:
        size, sha256 = await _stream_to_quarantine(file, staging)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        staging.unlink(missing_ok=True)
        logger.warning("file_scan.upload_failed", extra={"err": str(e)})
        raise HTTPException(500, "upload failed")

    final_dir = qroot / sha256
    final_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    final_path = final_dir / f"sample{suffix}"
    if final_path.exists():
        # Same content already quarantined — drop the duplicate copy.
        staging.unlink(missing_ok=True)
    else:
        staging.replace(final_path)
        os.chmod(final_path, 0o600)

    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    request = ScanRequest(
        target=Target(
            type=TargetType.BINARY,
            value=sha256,
            metadata={
                "path": str(final_path),
                "filename": file.filename,
                "size": size,
                "content_type": file.content_type or "application/octet-stream",
                "tlp": tlp_norm,
                "source": source,
                "uploaded_from": client_ip,
                "user_agent": user_agent,
            },
        ),
        engagement_id=engagement_id,
        scanners=["binary_analyzer"],
        intensity=ScanIntensity.PASSIVE,
        requested_by="api-caller",
        notes=notes,
        tenant_id=get_current_tenant_id(),
    )
    try:
        scan_id = await agent.submit_scan(request)
    except GuardrailViolation as e:
        raise HTTPException(400, detail={"code": e.code, "message": e.message})

    return {
        "scan_id": str(scan_id),
        "sha256": sha256,
        "size": size,
        "filename": file.filename,
    }


@router.delete(
    "/{sha256}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    dependencies=[require_security_operator()],
)
async def purge_sample(sha256: str) -> None:
    """Delete a quarantined sample. Findings remain referenced by sha256."""
    if len(sha256) != 64 or not all(c in "0123456789abcdef" for c in sha256):
        raise HTTPException(400, "sha256 must be 64 lowercase hex chars")
    folder = _quarantine_root() / sha256
    if not folder.exists():
        raise HTTPException(404, "sample not found")
    for p in folder.iterdir():
        try:
            p.unlink()
        except OSError:
            pass
    try:
        folder.rmdir()
    except OSError:
        pass


@router.get(
    "/{sha256}/info",
    dependencies=[require_viewer()],
)
async def sample_info(sha256: str) -> dict[str, object]:
    """Lightweight existence check — useful for the UI to know whether a
    quarantined copy is still on disk before offering re-scan or purge."""
    if len(sha256) != 64:
        raise HTTPException(400, "sha256 must be 64 chars")
    folder = _quarantine_root() / sha256
    if not folder.exists():
        return {"sha256": sha256, "available": False}
    files = [f.name for f in folder.iterdir()]
    return {"sha256": sha256, "available": True, "files": files}

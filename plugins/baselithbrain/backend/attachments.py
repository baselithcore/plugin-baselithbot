"""Local attachment store — images and files living beside the vault.

Binary assets are written under ``<vault>/_assets/`` with content-addressed,
slugified names so the vault stays portable (Obsidian reads the same relative
``_assets/<name>`` paths). This module owns *bytes on disk only*; the
markdown↔display URL rewrite lives in the SPA's markdown bridge.

All reads/writes are confined to the assets directory (traversal-guarded), and
uploads are capped + restricted to an image allowlist by the router.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
ASSETS_DIRNAME = "_assets"

# File extension is chosen from the *sniffed* media type, never the client
# filename — so a mislabeled upload can never land an active extension on disk.
_EXT_BY_MEDIA = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
}


def _slug_stem(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return _SLUG_RE.sub("-", norm.lower()).strip("-") or "file"


class AttachmentStore:
    """Filesystem gateway for ``<vault>/_assets/<name>`` binary files."""

    def __init__(self, vault_root: Path) -> None:
        self.root = (vault_root / ASSETS_DIRNAME).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        """Resolve an asset name to a confined path (traversal-guarded)."""
        if not _NAME_RE.match(name):
            raise ValueError(f"invalid asset name: {name!r}")
        path = (self.root / name).resolve()
        if self.root not in path.parents:
            raise ValueError(f"path escapes assets dir: {name!r}")
        return path

    def save(self, filename: str, data: bytes, media: str) -> str:
        """Persist ``data`` under a content-addressed name; return the name.

        Name = ``<slug>-<sha8>.<ext>`` where ``ext`` is derived from the sniffed
        ``media`` type (not the client filename), so re-uploading identical bytes
        is idempotent and no active extension can ever be written.
        """
        ext = _EXT_BY_MEDIA.get(media, "bin")
        stem = _slug_stem(Path(filename).stem)
        digest = hashlib.sha256(data).hexdigest()[:8]
        name = f"{stem}-{digest}.{ext}"
        self._path(name).write_bytes(data)
        return name

    def read(self, name: str) -> bytes:
        return self._path(name).read_bytes()

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

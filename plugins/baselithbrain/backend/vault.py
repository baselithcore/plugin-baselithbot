"""Local Markdown vault — the single source of truth.

Pure filesystem IO over a flat directory of ``<id>.md`` files. All paths are
confined to the vault root (traversal-guarded). Higher layers (notes, index)
build on top; this module knows nothing about links, search, or graphs.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def slugify(text: str) -> str:
    """ASCII, lowercase, hyphenated slug. Empty input → ``untitled``."""
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = _SLUG_RE.sub("-", norm.lower()).strip("-")
    return slug or "untitled"


class Vault:
    """Filesystem gateway for ``<id>.md`` note files under one root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- path helpers ----------------------------------------------------
    def _path(self, note_id: str) -> Path:
        """Resolve a note id to a vault-confined file path.

        Raises ``ValueError`` on any id that would escape the vault or contain
        path separators — the id is a flat key, never a relative path.
        """
        if not _ID_RE.match(note_id):
            raise ValueError(f"invalid note id: {note_id!r}")
        path = (self.root / f"{note_id}.md").resolve()
        if self.root not in path.parents:
            raise ValueError(f"path escapes vault: {note_id!r}")
        return path

    def unique_id(self, base: str) -> str:
        """Return a free note id derived from ``base`` (slug), de-duplicated."""
        slug = slugify(base)
        candidate = slug
        n = 2
        while self._path(candidate).exists():
            candidate = f"{slug}-{n}"
            n += 1
        return candidate

    # ---- IO --------------------------------------------------------------
    def exists(self, note_id: str) -> bool:
        return self._path(note_id).exists()

    def read(self, note_id: str) -> str:
        return self._path(note_id).read_text(encoding="utf-8")

    def write(self, note_id: str, text: str) -> None:
        self._path(note_id).write_text(text, encoding="utf-8")

    def delete(self, note_id: str) -> bool:
        path = self._path(note_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def rename(self, old_id: str, new_id: str) -> None:
        self._path(old_id).rename(self._path(new_id))

    def mtime(self, note_id: str) -> float:
        return self._path(note_id).stat().st_mtime

    def list_ids(self) -> list[str]:
        """All note ids in the vault (sorted), one per ``*.md`` file.

        Non-recursive, so files kept under ``.brain/`` (trash, history,
        templates) are never mistaken for live notes.
        """
        return sorted(p.stem for p in self.root.glob("*.md") if p.is_file())

    # ---- trash (soft delete) --------------------------------------------
    def _trash_dir(self) -> Path:
        d = self.root / ".brain" / "trash"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _trash_path(self, note_id: str) -> Path:
        """Vault-confined path for a trashed note (same id guard as live)."""
        if not _ID_RE.match(note_id):
            raise ValueError(f"invalid note id: {note_id!r}")
        path = (self._trash_dir() / f"{note_id}.md").resolve()
        if self._trash_dir().resolve() not in path.parents:
            raise ValueError(f"path escapes trash: {note_id!r}")
        return path

    def trash(self, note_id: str) -> bool:
        """Soft-delete: move the live file into ``.brain/trash`` (overwrite)."""
        src = self._path(note_id)
        if not src.exists():
            return False
        src.replace(self._trash_path(note_id))
        return True

    def list_trashed(self) -> list[str]:
        """Ids currently in the trash (sorted)."""
        return sorted(p.stem for p in self._trash_dir().glob("*.md") if p.is_file())

    def read_trashed(self, note_id: str) -> str:
        return self._trash_path(note_id).read_text(encoding="utf-8")

    def restore(self, note_id: str, new_id: str | None = None) -> str:
        """Move a trashed note back to the live vault under a free id."""
        src = self._trash_path(note_id)
        target = new_id or note_id
        if self._path(target).exists():
            target = self.unique_id(target)
        src.replace(self._path(target))
        return target

    def purge(self, note_id: str) -> bool:
        """Permanently delete a single trashed note."""
        path = self._trash_path(note_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def purge_all(self) -> int:
        """Permanently delete every trashed note; return the count."""
        count = 0
        for p in self._trash_dir().glob("*.md"):
            p.unlink()
            count += 1
        return count

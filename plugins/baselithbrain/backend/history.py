"""Note version history — lightweight on-disk revision snapshots.

Each save captures the *previous* raw file (frontmatter + body) under
``.brain/history/<id>/<version>.md`` before it is overwritten, so any edit can
be reviewed or rolled back. Snapshots are pruned to a bounded count per note so
history never grows without limit. Derived/disposable: deleting it loses
history but never the live notes.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .models import HistoryEntry

_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_VERSION_RE = re.compile(r"^[0-9]{8}T[0-9]{6}[0-9]{0,6}$")
_MAX_PER_NOTE = 30


class HistoryStore:
    """Bounded per-note revision store under the vault's ``.brain/history``."""

    def __init__(self, vault_root: Path, max_per_note: int = _MAX_PER_NOTE) -> None:
        self._root = vault_root.resolve() / ".brain" / "history"
        self._max = max_per_note

    def _note_dir(self, note_id: str) -> Path:
        if not _ID_RE.match(note_id):
            raise ValueError(f"invalid note id: {note_id!r}")
        return self._root / note_id

    def _version_path(self, note_id: str, version: str) -> Path:
        if not _VERSION_RE.match(version):
            raise ValueError(f"invalid version: {version!r}")
        return self._note_dir(note_id) / f"{version}.md"

    @staticmethod
    def _new_version() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")

    @staticmethod
    def _saved_iso(version: str) -> str | None:
        try:
            dt = datetime.strptime(version[:15], "%Y%m%dT%H%M%S")
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return None

    def snapshot(self, note_id: str, raw_text: str) -> None:
        """Capture ``raw_text`` as a new revision, then prune old ones."""
        if not raw_text:
            return
        d = self._note_dir(note_id)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{self._new_version()}.md").write_text(raw_text, encoding="utf-8")
        self._prune(note_id)

    def list(self, note_id: str) -> list[HistoryEntry]:
        """All revisions for a note, newest first."""
        d = self._note_dir(note_id)
        if not d.exists():
            return []
        entries = [
            HistoryEntry(
                version=p.stem,
                saved=self._saved_iso(p.stem) or "",
                size=p.stat().st_size,
            )
            for p in d.glob("*.md")
            if p.is_file()
        ]
        entries.sort(key=lambda e: e.version, reverse=True)
        return entries

    def get(self, note_id: str, version: str) -> str:
        """Raw text of one revision (frontmatter + body)."""
        return self._version_path(note_id, version).read_text(encoding="utf-8")

    def _prune(self, note_id: str) -> None:
        d = self._note_dir(note_id)
        revisions = sorted(
            (p for p in d.glob("*.md") if p.is_file()), key=lambda p: p.stem
        )
        for stale in revisions[: max(0, len(revisions) - self._max)]:
            stale.unlink(missing_ok=True)

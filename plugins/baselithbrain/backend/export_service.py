"""Export — hand the user back their own open-format files.

Single note → its raw ``<id>.md`` (frontmatter + body, exactly as on disk).
Whole vault (optionally one workspace) → a flat ``.zip`` of those Markdown
files. No proprietary packaging: what you export is what Obsidian/any editor
reads.
"""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .index_state import BrainIndex


def export_note(index: "BrainIndex", note_id: str) -> tuple[str, str]:
    """Return ``(filename, raw_markdown)`` for one note (frontmatter + body)."""
    raw = index.notes.vault.read(note_id)
    return f"{note_id}.md", raw


def export_vault(index: "BrainIndex", workspace: str | None = None) -> tuple[str, bytes]:
    """Return ``(filename, zip_bytes)`` bundling every note's raw Markdown."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for meta in index.notes.list_meta(workspace=workspace):
            try:
                archive.writestr(f"{meta.id}.md", index.notes.vault.read(meta.id))
            except (FileNotFoundError, ValueError):
                continue
    name = f"{workspace or 'vault'}.zip"
    return name, buffer.getvalue()

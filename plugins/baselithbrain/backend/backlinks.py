"""Backlinks with context — the line of text around each inbound link.

A plain backlink list answers "who links here"; the *context* answers "in what
sentence". For every note that links to the target, find the line carrying the
``[[wikilink]]`` and return it as a trimmed snippet, so the panel reads like
Obsidian's linked-mentions view.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import links as link_utils
from .models import BacklinkContext

if TYPE_CHECKING:  # avoid an import cycle with the index
    from .index_state import BrainIndex

_SNIPPET_MAX = 220


def _snippet_for(body: str, target_id: str) -> str:
    """First line of ``body`` whose wikilink resolves to ``target_id``."""
    for line in body.splitlines():
        if "[[" not in line:
            continue
        if target_id in link_utils.extract_targets(line):
            trimmed = line.strip()
            return trimmed[:_SNIPPET_MAX] + ("…" if len(trimmed) > _SNIPPET_MAX else "")
    return ""


def backlinks_with_context(index: "BrainIndex", note_id: str) -> list[BacklinkContext]:
    """Inbound links to ``note_id`` enriched with their surrounding line."""
    out: list[BacklinkContext] = []
    for source_id in index.graph.backlinks(note_id):
        try:
            source = index.notes.get(source_id)
        except (FileNotFoundError, ValueError):
            continue
        out.append(
            BacklinkContext(
                id=source_id,
                title=source.title,
                snippet=_snippet_for(source.body, note_id),
            )
        )
    out.sort(key=lambda b: b.title.lower())
    return out

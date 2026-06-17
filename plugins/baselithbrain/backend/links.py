"""Wikilink parsing and backlink resolution.

The LYT/Zettelkasten link layer. Explicit links are authored as ``[[target]]``
or ``[[target|alias]]`` inside note bodies — they live in the user's files and
are the source of truth for graph edges. Backlinks and unlinked mentions are
*derived* (computed from the corpus), never stored.
"""

from __future__ import annotations

import re
from collections import defaultdict

from .vault import slugify

# [[target]] or [[target|display alias]] — target captured, alias ignored.
_WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:\#[^\]\|]+)?(?:\|[^\]]+)?\]\]")


def extract_targets(body: str) -> list[str]:
    """Return resolved note ids referenced by ``[[wikilinks]]`` in ``body``.

    Targets are slugified so ``[[My Note]]`` and ``[[my-note]]`` resolve to the
    same id. Order-preserving, de-duplicated.
    """
    seen: dict[str, None] = {}
    for match in _WIKILINK_RE.finditer(body):
        target = slugify(match.group(1).strip())
        if target:
            seen.setdefault(target, None)
    return list(seen)


def build_backlinks(links_by_note: dict[str, list[str]]) -> dict[str, list[str]]:
    """Invert a forward-link map into a backlink map.

    ``links_by_note[a] == [b]`` (a links to b) ⇒ ``result[b] == [a]``. Only
    existing notes appear as keys; dangling targets are ignored here (surfaced
    separately as suggestions).
    """
    back: dict[str, list[str]] = defaultdict(list)
    known = set(links_by_note)
    for source, targets in links_by_note.items():
        for target in targets:
            if target in known and source != target:
                back[target].append(source)
    return {k: sorted(set(v)) for k, v in back.items()}


def unlinked_mentions(
    note_id: str,
    body: str,
    titles_by_id: dict[str, str],
    existing_links: set[str],
) -> list[str]:
    """Find note ids whose title appears verbatim in ``body`` but isn't linked.

    Case-insensitive whole-word match. Excludes the note itself and anything
    already linked — these become one-click "link this mention" suggestions.
    """
    found: list[str] = []
    lower_body = body.lower()
    for other_id, other_title in titles_by_id.items():
        if other_id == note_id or other_id in existing_links:
            continue
        needle = other_title.strip().lower()
        if len(needle) < 3:
            continue
        if re.search(rf"\b{re.escape(needle)}\b", lower_body):
            found.append(other_id)
    return found

"""YAML frontmatter parsing and serialization.

Notes are stored as an *open format*: a leading ``---`` YAML block followed by a
Markdown body. No proprietary or binary state — the file on disk is fully
human-readable and portable to Obsidian/any Markdown tool.
"""

from __future__ import annotations

from typing import Any

import yaml

_FENCE = "---"


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Split raw file text into (frontmatter dict, Markdown body).

    Tolerant: a file with no frontmatter returns ``({}, text)``. Malformed YAML
    degrades to an empty mapping rather than raising, so a hand-edited file can
    never make a note unreadable.
    """
    if not text.startswith(_FENCE):
        return {}, text
    parts = text.split(_FENCE, 2)
    # parts == ["", "<yaml>\n", "\n<body>"] for a well-formed header.
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    body = parts[2].lstrip("\n")
    return meta, body


def serialize(meta: dict[str, Any], body: str) -> str:
    """Render (frontmatter, body) back to file text.

    Keys are emitted in a stable order so diffs stay clean across saves.
    """
    ordered = {k: meta[k] for k in sorted(meta) if meta[k] is not None}
    header = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True).strip()
    return f"{_FENCE}\n{header}\n{_FENCE}\n\n{body.strip()}\n"

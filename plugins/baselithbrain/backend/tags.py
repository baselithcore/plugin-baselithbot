"""Tag aggregation — derive a tag browser index from note metadata.

Pure functions over the note metas the index already holds. Tags are a portable
frontmatter scalar, so this needs no extra storage: it just counts.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .models import NoteMeta, TagInfo


def collect_tags(metas: Iterable[NoteMeta]) -> list[TagInfo]:
    """Count tag usage across ``metas``, sorted by count (desc) then name."""
    counter: Counter[str] = Counter()
    for meta in metas:
        for tag in meta.tags:
            cleaned = tag.strip()
            if cleaned:
                counter[cleaned] += 1
    return [
        TagInfo(tag=tag, count=count)
        for tag, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    ]


def notes_with_tag(metas: Iterable[NoteMeta], tag: str) -> list[NoteMeta]:
    """Subset of ``metas`` carrying ``tag`` (case-insensitive)."""
    needle = tag.strip().lower()
    return [m for m in metas if any(t.strip().lower() == needle for t in m.tags)]

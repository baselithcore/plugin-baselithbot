"""Generic grouping over wiki pages, driven by Domain Pack rules.

Replaces the hardcoded ``/api/editions`` endpoint of the reference project.
A :class:`GroupingRule` declares which page type to scan, which
frontmatter fields form the composite group key, and how to derive a
human label. The HTTP layer translates ``GET /api/groups?rule=<key>``
into a call to :func:`compute_groups`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from llm_wiki import config
from llm_wiki.domain.pack import DomainPack, GroupingRule
from llm_wiki.domain.registry import get_pack
from llm_wiki.wiki.parser import parse_file, walk_wiki


def list_rules(pack: DomainPack | None = None) -> list[GroupingRule]:
    """Grouping rules declared by the given pack (or the active one)."""
    return list((pack or get_pack()).grouping)


def get_rule(key: str, pack: DomainPack | None = None) -> GroupingRule | None:
    for rule in list_rules(pack):
        if rule.key == key:
            return rule
    return None


def compute_groups(
    rule: GroupingRule,
    *,
    wiki_dir: Path | None = None,
    wiki_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Materialise the groups for ``rule`` by scanning the vault.

    Pure function over the wiki state on disk: no side effects, no caches.
    Cheap enough at MVP scale (a few hundred pages); promote to an LRU
    cache keyed on vault mtime if it ever shows up in profiles.

    ``wiki_dir`` / ``wiki_root`` are optional per-tenant overrides; when
    omitted the legacy single-tenant globals are used.
    """
    files = walk_wiki(wiki_dir if wiki_dir is not None else config.WIKI_DIR)
    root = wiki_root if wiki_root is not None else config.WIKI_ROOT
    buckets: dict[tuple[str, ...], dict[str, Any]] = {}

    for f in files:
        page = parse_file(f, root)
        if page is None or page.page_type != rule.page_type:
            continue

        fm = page.frontmatter
        key_parts = tuple(str(fm.get(k, "")) for k in rule.group_by)
        if not any(key_parts):
            continue

        bucket = buckets.setdefault(
            key_parts,
            {
                "id": "-".join(p or "_" for p in key_parts),
                "key": dict(zip(rule.group_by, key_parts, strict=False)),
                "label": _render_label(rule.label_from, page=page, fm=fm),
                "members": [],
                "extras": {field: None for field in rule.extra_fields},
            },
        )
        bucket["members"].append(
            {
                "document_id": page.document_id,
                "title": page.title,
                "subtype": fm.get("subtype"),
                "page_type": page.page_type,
            }
        )
        for field in rule.extra_fields:
            current = bucket["extras"].get(field)
            value = fm.get(field)
            if value and not current:
                bucket["extras"][field] = value

    out = list(buckets.values())
    if rule.sort_by:
        out.sort(key=lambda g: tuple(str(g["key"].get(k, "")) for k in rule.sort_by), reverse=True)
    return out


_TEMPLATE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_-]*)\}")


def _render_label(template: str, *, page: Any, fm: dict[str, Any]) -> str:
    """Resolve a label template like ``"{title} — {edizione}"``.

    Recognised tokens: ``{title}`` (page title) and any frontmatter key.
    Unknown tokens collapse to empty strings instead of raising — labels
    are display-only and shouldn't crash the API on partial data.
    """

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        if token == "title":
            return str(page.title)
        return str(fm.get(token, ""))

    rendered = _TEMPLATE_RE.sub(repl, template).strip()
    return rendered or page.title

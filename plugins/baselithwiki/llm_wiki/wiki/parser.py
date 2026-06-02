"""Markdown wiki page parser with YAML frontmatter.

The parser is **domain-agnostic**: page-type detection, frontmatter
validation rules and Qdrant payload projection all derive from the active
:class:`DomainPack`. The reference project hardcoded these — that coupling
has moved into ``domains/<APP_DOMAIN>/{pack.yaml,schema.yaml}``.

Vault conventions still hold:

- First ``---`` ... ``---`` block at the top is YAML frontmatter.
- Body is plain Markdown with headings, callouts and Obsidian wikilinks.
- ``document_id`` is the slug derived from the relative path under
  ``WIKI_DIR``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-not-found]

from llm_wiki.domain.pack import DomainPack
from llm_wiki.domain.registry import get_pack
from llm_wiki.domain.schema import FrontmatterSchema, get_schema
from llm_wiki.vectorstore.chunking import extract_wikilinks

logger = logging.getLogger(__name__)

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class WikiPage:
    path: Path
    relative_path: str
    document_id: str
    title: str
    page_type: str
    category: str
    tags: list[str]
    aliases: list[str]
    frontmatter: dict[str, Any]
    body: str
    wikilinks: list[str]

    def to_payload(self, schema: FrontmatterSchema | None = None) -> dict[str, Any]:
        """Project the frontmatter into a Qdrant-safe payload.

        ``schema`` defaults to the active pack's :class:`FrontmatterSchema`
        — pass an explicit one only in tests. The keys allowed in the
        payload are exactly those declared in ``schema.yaml`` for the
        page's type, plus the universal navigation fields.
        """
        active = schema or get_schema()
        payload: dict[str, Any] = {
            "document_id": self.document_id,
            "title": self.title,
            "page_type": self.page_type,
            "category": self.category,
            "tags": self.tags,
            "aliases": self.aliases,
            "source_file": self.relative_path,
            "relative_path": self.relative_path,
            "wikilinks_out": self.wikilinks,
        }

        for key in active.payload_keys(self.page_type):
            if key in self.frontmatter and key not in payload:
                value = self.frontmatter[key]
                if isinstance(value, str | int | float | bool):
                    payload[key] = value
                elif isinstance(value, list):
                    payload[key] = [str(v) for v in value]
                elif hasattr(value, "isoformat"):
                    payload[key] = value.isoformat()
        return payload


def parse_file(file_path: Path, wiki_root: Path) -> WikiPage | None:
    """Load and normalise a wiki page. Returns ``None`` if unreadable."""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    frontmatter: dict[str, Any] = {}
    body = raw

    match = _FRONTMATTER.match(raw)
    if match:
        try:
            parsed = yaml.safe_load(match.group(1)) or {}
            if isinstance(parsed, dict):
                frontmatter = parsed
        except yaml.YAMLError:
            frontmatter = {}
        body = raw[match.end() :]

    relative = file_path.relative_to(wiki_root).as_posix()
    document_id = _make_doc_id(relative)

    pack = _try_get_pack()

    title = str(frontmatter.get("title") or _fallback_title(file_path, body))
    page_type = str(frontmatter.get("type") or _infer_type(relative, pack))
    category = _infer_category(relative, page_type)
    tags = _coerce_list(frontmatter.get("tags"))
    aliases = _coerce_list(frontmatter.get("aliases"))

    return WikiPage(
        path=file_path,
        relative_path=relative,
        document_id=document_id,
        title=title,
        page_type=page_type,
        category=category,
        tags=tags,
        aliases=aliases,
        frontmatter=frontmatter,
        body=body.strip(),
        wikilinks=extract_wikilinks(body),
    )


def walk_wiki(wiki_subdir: Path) -> list[Path]:
    """Recursive listing of every ``*.md`` page under ``wiki_subdir``."""
    if not wiki_subdir.exists():
        return []
    return sorted(
        p
        for p in wiki_subdir.rglob("*.md")
        if p.is_file() and not p.name.startswith(".")
    )


# --- helpers ----------------------------------------------------------------


def _try_get_pack() -> DomainPack | None:
    """Return the active pack or ``None`` if it cannot be loaded.

    The parser is sometimes invoked from contexts that don't have a pack
    (linters, ad-hoc scripts). We fall back to legacy folder-name inference
    rather than blowing up.
    """
    try:
        return get_pack()
    except Exception as exc:
        logger.debug("[parser] no active pack, using legacy folder inference: %s", exc)
        return None


def _make_doc_id(relative: str) -> str:
    if relative.endswith(".md"):
        relative = relative[:-3]
    if relative.startswith("wiki/"):
        relative = relative[len("wiki/") :]
    return relative


def _fallback_title(path: Path, body: str) -> str:
    for line in body.splitlines()[:10]:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def _infer_type(relative: str, pack: DomainPack | None) -> str:
    """Infer ``page_type`` from the path using the pack's folder map.

    Falls back to legacy hardcoded folder names when no pack is loaded —
    keeps utility scripts working out of the box.
    """
    parts = relative.split("/")
    if pack is not None:
        folder_to_type = {pt.folder or pt.id: pt.id for pt in pack.page_types}
        for part in parts:
            if part in folder_to_type:
                return folder_to_type[part]

    legacy = {
        "sources": "source",
        "entities": "entity",
        "concepts": "concept",
        "topics": "topic",
        "syntheses": "synthesis",
    }
    for part in parts:
        if part in legacy:
            return legacy[part]
    return "unknown"


def _infer_category(relative: str, page_type: str) -> str:
    parts = relative.split("/")
    if len(parts) >= 3 and parts[-3] == "wiki":
        return parts[-2]
    if len(parts) >= 4 and parts[-4] == "wiki":
        return f"{parts[-3]}/{parts[-2]}"
    return page_type


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    return [str(value)]

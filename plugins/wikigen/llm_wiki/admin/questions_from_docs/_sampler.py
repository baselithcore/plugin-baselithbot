"""Sample representative wiki pages to ground starter-question generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


@dataclass(slots=True)
class PageSample:
    """Slim view of a wiki page: enough for the LLM, no parser dep."""

    relative_path: str
    title: str
    page_type: str
    folder: str
    excerpt: str


def sample_pages(
    wiki_dir: Path,
    *,
    page_types: list[dict[str, Any]],
    max_pages: int,
    max_chars: int,
) -> list[PageSample]:
    """Pick up to ``max_pages`` wiki pages, source-folder-first.

    Strategy (deterministic so re-runs produce the same chips):
    1. Prefer pages whose folder matches the pack's *source* page-type
       (post-ingest these are high-signal pages grounded in raw docs).
    2. Then other page-type folders in declaration order.
    3. Skip ``.new.md`` / ``.needs-review.md`` (incomplete content),
       ``index.md`` / ``log.md`` (vault scaffolding, not knowledge).
    4. Within a folder, sort by filename for stable picks.
    """
    if not wiki_dir.is_dir():
        return []

    ordered_folders = _ordered_page_folders(page_types)
    if not ordered_folders:
        ordered_folders = [(p.name, "page") for p in sorted(wiki_dir.iterdir()) if p.is_dir()]

    seen: set[str] = set()
    samples: list[PageSample] = []
    for folder, type_id in ordered_folders:
        folder_path = wiki_dir / folder
        if not folder_path.is_dir():
            continue
        for md_path in sorted(folder_path.glob("*.md")):
            if md_path.name in {"index.md", "log.md"}:
                continue
            lower = md_path.name.lower()
            if lower.endswith(".new.md") or lower.endswith(".needs-review.md"):
                continue
            rel = md_path.relative_to(wiki_dir).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            try:
                sample = _read_sample(md_path, wiki_dir, type_id, folder, max_chars)
            except OSError:
                continue
            if sample is not None:
                samples.append(sample)
                if len(samples) >= max_pages:
                    return samples
    return samples


def _ordered_page_folders(page_types: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """``[(folder, page_type_id)]`` with source-like types prioritised.

    Substring match on the type id + folder so a forked pack that
    renamed ``source`` to ``fonti`` / ``documents`` still benefits.
    """
    seen: set[str] = set()
    source_first: list[tuple[str, str]] = []
    rest: list[tuple[str, str]] = []
    for pt in page_types:
        folder = pt.get("folder") or pt.get("plural") or pt.get("id")
        if not folder:
            continue
        type_id = str(pt.get("id") or folder)
        folder_s = str(folder)
        if folder_s in seen:
            continue
        seen.add(folder_s)
        haystack = f"{type_id} {folder_s}".lower()
        if any(token in haystack for token in ("source", "fonti", "document")):
            source_first.append((folder_s, type_id))
        else:
            rest.append((folder_s, type_id))
    return [*source_first, *rest]


def _read_sample(
    md_path: Path,
    wiki_root: Path,
    page_type_id: str,
    folder: str,
    max_chars: int,
) -> PageSample | None:
    raw = md_path.read_text(encoding="utf-8")
    frontmatter: dict[str, Any] = {}
    body = raw
    match = _FRONTMATTER_RE.match(raw)
    if match:
        try:
            import yaml

            parsed = yaml.safe_load(match.group(1)) or {}
            if isinstance(parsed, dict):
                frontmatter = parsed
        except Exception:  # noqa: BLE001 — frontmatter best-effort
            frontmatter = {}
        body = raw[match.end() :]
    body = body.strip()
    if not body:
        return None
    title = str(frontmatter.get("title") or md_path.stem.replace("-", " ").title())
    return PageSample(
        relative_path=md_path.relative_to(wiki_root).as_posix(),
        title=title,
        page_type=page_type_id,
        folder=folder,
        excerpt=_excerpt(body, max_chars),
    )


def _excerpt(body: str, max_chars: int) -> str:
    """Body excerpt with wikilinks reduced to bare display names.

    Wikilink targets leak slugs the LLM might echo verbatim into a
    suggested question, producing prompts like
    ``"che cos'è sources/foo-bar?"`` — readable, but ugly. The bare
    name reads cleanly.
    """
    cleaned = _WIKILINK_RE.sub(lambda m: m.group(1).split("/")[-1].replace("-", " "), body).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[:max_chars].rsplit("\n", 1)[0].rstrip()
    return cut + "\n…[troncato]"


__all__ = ["PageSample", "_ordered_page_folders", "sample_pages"]

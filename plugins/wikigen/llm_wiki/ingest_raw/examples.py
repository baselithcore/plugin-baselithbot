"""Few-shot example retrieval from existing wiki pages.

The local LLM (70B Q4 on DGX Spark) keeps style **much better** when
fed 1-3 sibling pages as examples. Selection priority:

1. Same ``page_type`` + ``subtype`` (high).
2. Same ``page_type`` only (medium).
3. Anything else at the same hierarchy level (fallback).

White-label note
----------------
Examples can come from two places:

- **Vault pages** under ``WIKI_DIR``: real pages already in the wiki.
- **Pack examples** under ``<pack>/examples/``: hand-curated reference
  files shipped with the Domain Pack so a freshly-scaffolded wiki has
  something to imitate before any source has been ingested.

Both sources are merged transparently. Pack examples are loaded once and
cached; vault examples are cached per-process — invalidate by restarting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from llm_wiki.config import WIKI_DIR
from llm_wiki.domain.registry import get_pack

logger = logging.getLogger(__name__)


_EXAMPLE_BODY_CAP = 2000


@dataclass
class Example:
    path: Path
    page_type: str
    subtype: str
    title: str
    body: str

    def as_prompt_block(self) -> str:
        """Render con cap sul body: oltre ~2KB il marginal value cala forte
        e il costo di latenza/timeout sul LLM cresce linearmente. Lo stile
        è già evidente nei primi 1500 char (frontmatter + 1-2 sezioni)."""
        try:
            label = self.path.relative_to(WIKI_DIR)
        except ValueError:
            label = self.path
        body = self.body
        if len(body) > _EXAMPLE_BODY_CAP:
            body = (
                body[:_EXAMPLE_BODY_CAP].rstrip() + "\n\n<!-- (esempio troncato) -->\n"
            )
        return f"<!-- ESEMPIO: {label} -->\n{body}"


def pick_examples(
    *,
    page_type: str,
    subtype: str | None = None,
    hint_keywords: list[str] | None = None,
    max_examples: int = 2,
) -> list[Example]:
    candidates = [c for c in _load_candidates() if c.path.exists()]
    exact = [c for c in candidates if c.page_type == page_type and c.subtype == subtype]
    partial = [c for c in candidates if c.page_type == page_type and c not in exact]
    loose = [c for c in candidates if c not in exact and c not in partial]

    ordered: list[Example] = []
    for pool in (exact, partial, loose):
        for ex in _score_sort(pool, hint_keywords or []):
            if ex not in ordered:
                ordered.append(ex)
            if len(ordered) >= max_examples:
                return ordered[:max_examples]
    return ordered[:max_examples]


_CACHE: list[Example] | None = None


def reset_cache() -> None:
    """Drop the cached example list. Test-only."""
    global _CACHE
    _CACHE = None


def add_to_cache(paths: list[Path]) -> int:
    """Aggiunge incrementally pagine appena scritte alla cache few-shot.

    Senza questo passaggio il primo ingest popola ``_CACHE`` con le pagine
    iniziali del vault; gli ingest successivi nello stesso processo (boot
    auto-ingest, wizard multi-PDF, server long-running) NON vedrebbero
    come few-shot le pagine prodotte da ingest precedenti, dato che il
    cache è process-lifetime.

    Append diretto invece di reset: evita rilettura completa del vault
    (rglob + parse N file). Ritorna il numero di esempi aggiunti.
    """
    global _CACHE
    if _CACHE is None:
        return 0
    import yaml  # type: ignore[import-not-found]

    added = 0
    for path in paths:
        if any(ex.path == path for ex in _CACHE):
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, _body = _split_fm(raw)
        try:
            parsed = yaml.safe_load(fm) or {}
            if not isinstance(parsed, dict):
                parsed = {}
        except yaml.YAMLError:
            parsed = {}
        _CACHE.append(
            Example(
                path=path,
                page_type=str(parsed.get("type", "")),
                subtype=str(parsed.get("subtype", "")),
                title=str(parsed.get("title", path.stem)),
                body=raw,
            )
        )
        added += 1
    return added


def _load_candidates() -> list[Example]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    out: list[Example] = []
    out.extend(_load_dir(WIKI_DIR))

    try:
        pack = get_pack()
        if pack.examples_path.exists():
            out.extend(_load_dir(pack.examples_path))
    except Exception as exc:
        logger.debug("[examples] no pack examples: %s", exc)

    _CACHE = out
    return out


def _load_dir(directory: Path) -> list[Example]:
    if not directory.exists():
        return []
    import yaml  # type: ignore[import-not-found]

    out: list[Example] = []
    for md in directory.rglob("*.md"):
        try:
            raw = md.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, _body = _split_fm(raw)
        try:
            parsed = yaml.safe_load(fm) or {}
            if not isinstance(parsed, dict):
                parsed = {}
        except yaml.YAMLError:
            parsed = {}
        out.append(
            Example(
                path=md,
                page_type=str(parsed.get("type", "")),
                subtype=str(parsed.get("subtype", "")),
                title=str(parsed.get("title", md.stem)),
                body=raw,
            )
        )
    return out


def _split_fm(raw: str) -> tuple[str, str]:
    import re

    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if not m:
        return "", raw
    return m.group(1), raw[m.end() :]


def _score_sort(pool: list[Example], keywords: list[str]) -> list[Example]:
    kws = [k.lower() for k in keywords if k]

    def score(ex: Example) -> int:
        hay = f"{ex.title} {ex.body[:300]}".lower()
        return sum(1 for k in kws if k in hay)

    return sorted(pool, key=score, reverse=True)

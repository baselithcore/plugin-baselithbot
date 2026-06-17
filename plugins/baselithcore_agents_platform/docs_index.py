"""Documentation index for MCP grounding.

The platform grounds synthesised agents in the framework's own documentation so
they stay in-scope. This module discovers Markdown sources across the repository,
splits them into heading-delimited sections, and serves keyword-ranked excerpts.

Retrieval is built on the framework's native hybrid-search primitives rather than
a bespoke scorer: a body :class:`BM25Index` and a heading :class:`BM25Index` are
fused with :class:`HybridSearcher` (Reciprocal Rank Fusion), so an exact heading
hit and a body keyword hit reinforce each other. The dense leg of the hybrid can
later be supplied from ``core.nlp`` embeddings behind the same interface.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from core.memory.hybrid_search import BM25Index, HybridSearcher
from core.observability.logging import get_logger

from .types import DocCitation

logger = get_logger(__name__)

__all__ = ["DocSection", "DocIndexer"]

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")

# Default discovery globs, relative to the repository root. Kept conservative so
# indexing stays fast and never wanders into build output or dependencies.
_DEFAULT_GLOBS: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "CONTRIBUTING.md",
    "docs/**/*.md",
    "plugins/*/README.md",
    "plugins/*/docs/**/*.md",
)
_EXCLUDED_PARTS = frozenset({"node_modules", "dist", "__pycache__", ".git"})


@dataclass(slots=True)
class DocSection:
    """A heading-delimited slice of a Markdown document."""

    namespace: str
    heading: str
    text: str


class DocIndexer:
    """Builds and queries a hybrid index of framework documentation.

    The index is built lazily on first use and cached for the process lifetime.
    All public methods are async and guarded by a single build lock so the
    (CPU-light) indexing pass runs at most once under concurrent access.
    """

    def __init__(
        self,
        repo_root: Path,
        globs: tuple[str, ...] | None = None,
        max_section_chars: int = 1200,
    ) -> None:
        """Initialise the indexer.

        Args:
            repo_root: Absolute path to the repository root to index from.
            globs: Discovery globs relative to ``repo_root``; defaults applied
                when omitted.
            max_section_chars: Hard cap on a section's text length to bound
                prompt-context size.
        """
        self._repo_root = repo_root
        self._globs = globs or _DEFAULT_GLOBS
        self._max_section_chars = max_section_chars
        self._sections: list[DocSection] = []
        self._body_index = BM25Index()
        self._heading_index = BM25Index()
        self._fuser = HybridSearcher()
        self._built = False
        self._lock = asyncio.Lock()

    async def ensure_built(self) -> None:
        """Build the index once, idempotently and concurrency-safe."""
        if self._built:
            return
        async with self._lock:
            if self._built:
                return
            # Filesystem walk is blocking; offload so the loop stays responsive.
            self._sections = await asyncio.to_thread(self._build_sections)
            self._index_sections()
            self._built = True
            logger.info(
                "docs_index_built",
                sections=len(self._sections),
                roots=len(self._globs),
            )

    def _index_sections(self) -> None:
        """Build the body and heading BM25 indices over the section list."""
        body: dict[str, str] = {}
        headings: dict[str, str] = {}
        for i, section in enumerate(self._sections):
            doc_id = str(i)
            body[doc_id] = f"{section.heading}\n{section.text}"
            headings[doc_id] = section.heading
        self._body_index.index(body)
        self._heading_index.index(headings)

    def _iter_files(self) -> list[Path]:
        """Resolve discovery globs into a de-duplicated, filtered file list."""
        seen: set[Path] = set()
        for pattern in self._globs:
            for path in self._repo_root.glob(pattern):
                if not path.is_file():
                    continue
                if any(part in _EXCLUDED_PARTS for part in path.parts):
                    continue
                seen.add(path)
        return sorted(seen)

    def _build_sections(self) -> list[DocSection]:
        """Read every discovered file and split it into indexed sections."""
        sections: list[DocSection] = []
        for path in self._iter_files():
            try:
                raw = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:  # pragma: no cover
                logger.warning("docs_index_read_failed", path=str(path), error=str(exc))
                continue
            namespace = path.relative_to(self._repo_root).as_posix()
            sections.extend(self._split_document(namespace, raw))
        return sections

    def _split_document(self, namespace: str, raw: str) -> list[DocSection]:
        """Split a document into sections at Markdown headings."""
        sections: list[DocSection] = []
        heading = namespace
        buffer: list[str] = []

        def flush() -> None:
            text = "\n".join(buffer).strip()
            if not text:
                return
            sections.append(
                DocSection(
                    namespace=namespace,
                    heading=heading,
                    text=text[: self._max_section_chars],
                )
            )

        for line in raw.splitlines():
            match = _HEADING_RE.match(line)
            if match:
                flush()
                heading = match.group(2).strip() or namespace
                buffer = []
            else:
                buffer.append(line)
        flush()
        return sections

    async def search(
        self,
        query: str,
        namespaces: list[str] | None = None,
        top_k: int = 4,
    ) -> list[DocCitation]:
        """Return the top-k documentation sections for a query.

        Body and heading BM25 rankings are fused with Reciprocal Rank Fusion,
        then optionally filtered to the requested namespace prefixes.

        Args:
            query: Free-text query.
            namespaces: Optional path-prefix filter (a section matches when its
                namespace starts with any provided prefix).
            top_k: Maximum number of citations to return.

        Returns:
            Ranked citations, highest fused score first. Empty when nothing
            matches.
        """
        await self.ensure_built()
        if not query.strip() or not self._sections:
            return []

        # Over-fetch before namespace filtering so a prefix filter does not
        # starve the result set.
        pool = max(top_k * 5, top_k)
        body_hits = self._body_index.search(query, top_k=pool)
        heading_hits = self._heading_index.search(query, top_k=pool)
        fused = self._fuser.fuse(bm25=body_hits, dense=heading_hits, top_k=pool)

        prefixes = tuple(namespaces or ())
        citations: list[DocCitation] = []
        for hit in fused:
            section = self._sections[int(hit.doc_id)]
            if prefixes and not section.namespace.startswith(prefixes):
                continue
            citations.append(
                DocCitation(
                    namespace=section.namespace,
                    snippet=f"{section.heading}\n{section.text}"[:600],
                    score=hit.score,
                )
            )
            if len(citations) >= top_k:
                break
        return citations

    async def get_document(self, namespace: str) -> str | None:
        """Return the concatenated text of a single document by namespace."""
        await self.ensure_built()
        parts = [s.text for s in self._sections if s.namespace == namespace]
        return "\n\n".join(parts) if parts else None

    async def namespaces(self) -> list[str]:
        """Return the sorted set of indexed document namespaces."""
        await self.ensure_built()
        return sorted({s.namespace for s in self._sections})

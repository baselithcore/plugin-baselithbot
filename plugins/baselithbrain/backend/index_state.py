"""Derived index — the single in-memory read model over the vault.

Owns the wiring of :class:`NoteService` (persistence) with the disposable
derived services (search, graph, semantic). The index is rebuilt from disk on
startup and after writes; it is never the source of truth, so it can be dropped
and regenerated at any time without data loss.

Exposed as a lazily-built singleton (:func:`get_index`) shared by every router.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from . import links as link_utils
from .config_proxy import get_settings
from .conversations import ConversationService
from .graph_service import GraphService
from .history import HistoryStore
from .notes import NoteService
from .search_service import SearchService
from .semantic import SemanticIndex
from .templates import TemplateStore
from .vault import Vault
from .workspaces import WorkspaceService


class BrainIndex:
    """Coordinates persistence + derived search/graph/semantic views."""

    def __init__(self, vault_root: Path) -> None:
        self.notes = NoteService(Vault(vault_root))
        self.workspaces = WorkspaceService(vault_root)
        self.conversations = ConversationService(vault_root)
        self.history = HistoryStore(vault_root)
        self.templates = TemplateStore(vault_root)
        self._semantic = SemanticIndex(vault_root)
        self.search = SearchService(self._semantic)
        self.graph = GraphService(self._semantic)
        self._lock = asyncio.Lock()
        self.ready = False

    def snapshot(self, note_id: str) -> None:
        """Capture the current on-disk note as a history revision (best-effort).

        Called before an overwriting update so the prior text is recoverable.
        Never raises into the request path — history is non-critical.
        """
        try:
            self.history.snapshot(note_id, self.notes.vault.read(note_id))
        except (FileNotFoundError, ValueError, OSError):
            pass

    def note_ids(self, workspace: str | None = None) -> set[str] | None:
        """Set of note ids in ``workspace`` (``None`` ⇒ unscoped → ``None``)."""
        if workspace is None:
            return None
        return {m.id for m in self.notes.list_meta(workspace=workspace)}

    async def rebuild(self) -> None:
        """Re-derive every index from the current vault contents."""
        async with self._lock:
            titles: dict[str, str] = {}
            bodies: dict[str, str] = {}
            tags: dict[str, list[str]] = {}
            links: dict[str, list[str]] = {}

            for note in self.notes.list_meta():
                full = self.notes.get(note.id)
                titles[note.id] = full.title
                bodies[note.id] = full.body
                tags[note.id] = full.tags
                links[note.id] = link_utils.extract_targets(full.body)

            self.search.rebuild(titles, bodies)
            self.graph.rebuild(titles, tags, links)

            if get_settings().semantic_enabled:
                texts = {nid: f"{titles[nid]}\n{bodies[nid]}" for nid in bodies}
                await self._semantic.rebuild(texts)

            self.ready = True

    def hydrate(self, note_id: str):
        """Return a full note enriched with resolved forward/back links."""
        note = self.notes.get(note_id)
        note.links = self.graph.forward_links(note_id)
        note.backlinks = self.graph.backlinks(note_id)
        return note


# One derived index per tenant scope (vault sub-root). Keyed by the resolved
# path so the default/unbound scope reuses the historical single index and each
# ``personal`` user gets an isolated one. Background rebuild tasks are pinned in
# ``_bg_tasks`` so they are not garbage-collected mid-flight.
_indexes: dict[Path, BrainIndex] = {}
_bg_tasks: set[asyncio.Task[None]] = set()


def _build_index(root: Path) -> BrainIndex:
    """Construct + seed a fresh index for ``root`` (notes/workspaces usable at once)."""
    from .seed import seed_if_empty  # local import avoids an import cycle

    root.mkdir(parents=True, exist_ok=True)
    idx = BrainIndex(root)
    idx.workspaces.ensure_default()
    seed_if_empty(idx.notes)
    return idx


def _schedule_rebuild(idx: BrainIndex) -> None:
    """Build the derived (search/graph/semantic) views in the background, if a loop runs."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # no event loop (sync/test context) — explicit rebuild covers it
    task = loop.create_task(idx.rebuild())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


def get_index() -> BrainIndex:
    """Return the derived index for the current request's tenant scope.

    Resolves the scoped vault root from the bound identity (honouring the
    plugin's tenancy + any admin override). The default scope reuses the index
    the lifespan builds at boot; a new ``personal`` scope is constructed on first
    access (notes/workspaces work immediately) with its derived views rebuilt in
    the background — mirroring the existing degraded-until-ready model.
    """
    from .tenancy import scoped_vault_root

    base = get_settings().vault_root
    root = scoped_vault_root(base)
    idx = _indexes.get(root)
    if idx is None:
        idx = _build_index(root)
        _indexes[root] = idx
        if root != base:  # default scope is built by the app lifespan, not here
            _schedule_rebuild(idx)
    return idx


def _clear_index_cache() -> None:
    """Drop every per-scope index (used by tests, and on a vault-root change)."""
    _indexes.clear()


# Preserve the previous ``lru_cache`` reset API so callers/tests that rebuilt
# the index by clearing the cache keep working after the per-scope refactor.
get_index.cache_clear = _clear_index_cache  # type: ignore[attr-defined]

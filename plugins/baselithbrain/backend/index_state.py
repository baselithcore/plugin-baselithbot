"""Derived index — the single in-memory read model over the vault.

Owns the wiring of :class:`NoteService` (persistence) with the disposable
derived services (search, graph, semantic). The index is rebuilt from disk on
startup and after writes; it is never the source of truth, so it can be dropped
and regenerated at any time without data loss.

Exposed as a lazily-built singleton (:func:`get_index`) shared by every router.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path

from . import links as link_utils
from .config_proxy import get_settings
from .conversations import ConversationService
from .graph_service import GraphService
from .notes import NoteService
from .search_service import SearchService
from .semantic import SemanticIndex
from .vault import Vault
from .workspaces import WorkspaceService


class BrainIndex:
    """Coordinates persistence + derived search/graph/semantic views."""

    def __init__(self, vault_root: Path) -> None:
        self.notes = NoteService(Vault(vault_root))
        self.workspaces = WorkspaceService(vault_root)
        self.conversations = ConversationService(vault_root)
        self._semantic = SemanticIndex(vault_root)
        self.search = SearchService(self._semantic)
        self.graph = GraphService(self._semantic)
        self._lock = asyncio.Lock()
        self.ready = False

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


@lru_cache(maxsize=1)
def get_index() -> BrainIndex:
    return BrainIndex(get_settings().vault_root)

"""NoteService — CRUD over the Markdown vault.

Bridges raw files (:mod:`vault` + :mod:`frontmatter`) and the API DTOs
(:mod:`models`). Each note file is ``<id>.md`` with YAML frontmatter
(``title``, ``tags``, ``created``, ``updated``) and a Markdown body.

This layer owns *persistence only*. Link resolution, search and graph live in
the derived index so the files stay clean and tool-agnostic.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import frontmatter
from .models import Note, NoteCreate, NoteMeta, NoteMove, NoteUpdate
from .vault import Vault
from .workspaces import DEFAULT_WORKSPACE_ID


def _now() -> str:
    """UTC ISO-8601 timestamp (second precision)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_int(value: object) -> int | None:
    """Coerce a frontmatter scalar to ``int`` (None / non-numeric → None)."""
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class NoteService:
    """Reads and writes notes as open-format Markdown files."""

    def __init__(self, vault: Vault) -> None:
        self.vault = vault

    # ---- reads -----------------------------------------------------------
    def _load_raw(self, note_id: str) -> tuple[dict, str]:
        meta, body = frontmatter.parse(self.vault.read(note_id))
        return meta, body

    def get(self, note_id: str) -> Note:
        meta, body = self._load_raw(note_id)
        return Note(
            id=note_id,
            title=str(meta.get("title") or note_id),
            tags=list(meta.get("tags") or []),
            created=meta.get("created"),
            updated=meta.get("updated"),
            path=f"{note_id}.md",
            parent=self._parent_of(meta),
            order=_as_int(meta.get("order")),
            workspace=self._workspace_of(meta),
            body=body,
        )

    def get_meta(self, note_id: str) -> NoteMeta:
        meta, _ = self._load_raw(note_id)
        return NoteMeta(
            id=note_id,
            title=str(meta.get("title") or note_id),
            tags=list(meta.get("tags") or []),
            created=meta.get("created"),
            updated=meta.get("updated"),
            path=f"{note_id}.md",
            parent=self._parent_of(meta),
            order=_as_int(meta.get("order")),
            workspace=self._workspace_of(meta),
        )

    def _parent_of(self, meta: dict) -> str | None:
        """Read a sane parent id from frontmatter (own-id / unknown → root)."""
        raw = meta.get("parent")
        return str(raw) if raw else None

    def _workspace_of(self, meta: dict) -> str:
        """Owning workspace id — a missing scalar falls back to the default."""
        raw = meta.get("workspace")
        return str(raw) if raw else DEFAULT_WORKSPACE_ID

    def list_meta(self, workspace: str | None = None) -> list[NoteMeta]:
        """All note metas, optionally narrowed to one ``workspace``."""
        metas = [self.get_meta(nid) for nid in self.vault.list_ids()]
        if workspace is None:
            return metas
        return [m for m in metas if m.workspace == workspace]

    def exists(self, note_id: str) -> bool:
        return self.vault.exists(note_id)

    # ---- writes ----------------------------------------------------------
    def create(self, payload: NoteCreate, note_id: str | None = None) -> Note:
        # An explicit id is used verbatim (stable ids, e.g. daily notes); the
        # caller guarantees it is free. Otherwise derive a unique slug.
        note_id = note_id or self.vault.unique_id(payload.title or "untitled")
        ts = _now()
        parent = (
            payload.parent if payload.parent and self.exists(payload.parent) else None
        )
        # A child always lives in its parent's workspace; a root note honours
        # the requested workspace (falling back to the default).
        workspace = (
            self.get_meta(parent).workspace
            if parent
            else (payload.workspace or DEFAULT_WORKSPACE_ID)
        )
        meta = {
            "title": payload.title or note_id,
            "tags": payload.tags,
            "created": ts,
            "updated": ts,
            "parent": parent,
            "workspace": workspace,
        }
        self.vault.write(note_id, frontmatter.serialize(meta, payload.body))
        return self.get(note_id)

    def set_workspace(self, note_id: str, workspace: str) -> Note:
        """Re-home a note (and its whole subtree) into ``workspace``.

        Membership is hierarchical: moving a note carries its descendants along
        so a subtree never straddles two workspaces.
        """
        meta, body = self._load_raw(note_id)
        meta["workspace"] = workspace
        meta["updated"] = _now()
        self.vault.write(note_id, frontmatter.serialize(meta, body))
        for child in self.children_of(note_id):
            self.set_workspace(child, workspace)
        return self.get(note_id)

    def reassign_workspace(self, src: str, dst: str) -> int:
        """Move every note from workspace ``src`` to ``dst``; return the count."""
        moved = 0
        for meta in self.list_meta(workspace=src):
            raw, body = self._load_raw(meta.id)
            raw["workspace"] = dst
            raw["updated"] = _now()
            self.vault.write(meta.id, frontmatter.serialize(raw, body))
            moved += 1
        return moved

    def update(self, note_id: str, patch: NoteUpdate) -> Note:
        meta, body = self._load_raw(note_id)
        if patch.title is not None:
            meta["title"] = patch.title
        if patch.tags is not None:
            meta["tags"] = patch.tags
        if patch.body is not None:
            body = patch.body
        meta["updated"] = _now()
        meta.setdefault("created", meta["updated"])
        self.vault.write(note_id, frontmatter.serialize(meta, body))
        return self.get(note_id)

    def move(self, note_id: str, payload: NoteMove) -> Note:
        """Re-parent / reorder ``note_id``. Guards against cycles & self-parent.

        An invalid or cyclic ``parent`` (the target being a descendant of the
        moved note, or the note itself) falls back to the root, so the tree can
        never become disconnected or recursive.
        """
        meta, body = self._load_raw(note_id)
        parent = payload.parent
        if parent == note_id or not (parent and self.exists(parent)):
            parent = None
        elif self._is_descendant(parent, note_id):
            parent = None
        if parent is None:
            meta.pop("parent", None)
        else:
            meta["parent"] = parent
        if payload.order is not None:
            meta["order"] = payload.order
        meta["updated"] = _now()
        self.vault.write(note_id, frontmatter.serialize(meta, body))
        return self.get(note_id)

    def _is_descendant(self, candidate: str, ancestor: str) -> bool:
        """True if ``candidate`` is ``ancestor`` or sits below it in the tree."""
        seen: set[str] = set()
        current: str | None = candidate
        while current and current not in seen:
            if current == ancestor:
                return True
            seen.add(current)
            current = self.get_meta(current).parent
        return False

    def delete(self, note_id: str) -> bool:
        """Soft-delete a note to the trash; re-parent its children (no orphans).

        The file is moved into ``.brain/trash`` rather than erased, so a
        mistaken delete is recoverable via :meth:`restore`. Children climb to
        the deleted note's parent first, exactly as before.
        """
        if not self.exists(note_id):
            return False
        new_parent = self.get_meta(note_id).parent
        for child in self.children_of(note_id):
            self.move(child, NoteMove(parent=new_parent))
        return self.vault.trash(note_id)

    def list_trash(self) -> list[NoteMeta]:
        """Metadata for every soft-deleted note in the trash (newest first)."""
        out: list[NoteMeta] = []
        for nid in self.vault.list_trashed():
            meta, _ = frontmatter.parse(self.vault.read_trashed(nid))
            out.append(
                NoteMeta(
                    id=nid,
                    title=str(meta.get("title") or nid),
                    tags=list(meta.get("tags") or []),
                    created=meta.get("created"),
                    updated=meta.get("updated"),
                    path=f"{nid}.md",
                    parent=self._parent_of(meta),
                    order=_as_int(meta.get("order")),
                    workspace=self._workspace_of(meta),
                )
            )
        out.sort(key=lambda m: m.updated or "", reverse=True)
        return out

    def restore(self, note_id: str) -> Note:
        """Move a trashed note back into the live vault under a free id."""
        live_id = self.vault.restore(note_id)
        return self.get(live_id)

    def children_of(self, note_id: str) -> list[str]:
        """Ids whose ``parent`` is ``note_id`` (direct children only)."""
        return [m.id for m in self.list_meta() if m.parent == note_id]

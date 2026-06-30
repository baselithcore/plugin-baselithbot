"""Data-transfer objects for the BaselithBrain API.

Plain Pydantic models — the wire contract between backend and SPA. Notes are
serialized to/from Markdown + YAML frontmatter on disk; these models are the
in-memory / JSON view, never a storage format.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NoteMeta(BaseModel):
    """Lightweight note descriptor (list views, graph nodes, search hits)."""

    id: str
    title: str
    tags: list[str] = Field(default_factory=list)
    created: str | None = None
    updated: str | None = None
    path: str
    #: Parent note id (folder-less hierarchy). ``None`` ⇒ a root note. The
    #: tree is *derived* from this scalar — files stay flat and portable.
    parent: str | None = None
    #: Sort key among siblings (lower first). ``None`` ⇒ fall back to title.
    order: int | None = None
    #: Owning workspace id (logical grouping). A missing scalar resolves to the
    #: default workspace — like ``parent``, the grouping is a portable scalar,
    #: never a directory.
    workspace: str = "default"


class Note(NoteMeta):
    """Full note: metadata + Markdown body + resolved link sets."""

    body: str = ""
    links: list[str] = Field(default_factory=list)
    backlinks: list[str] = Field(default_factory=list)


class NoteCreate(BaseModel):
    """Payload to create a note."""

    title: str
    body: str = ""
    tags: list[str] = Field(default_factory=list)
    parent: str | None = None
    #: Target workspace. ``None`` ⇒ the default workspace.
    workspace: str | None = None


class NoteUpdate(BaseModel):
    """Partial update payload (only provided fields change)."""

    title: str | None = None
    body: str | None = None
    tags: list[str] | None = None


class NoteMove(BaseModel):
    """Re-parent / reorder a note in the page tree.

    ``parent`` is always explicit (``None`` moves the note to the root), so the
    move is unambiguous — unlike :class:`NoteUpdate` where ``None`` means
    "leave unchanged".
    """

    parent: str | None = None
    order: int | None = None


class NoteAssign(BaseModel):
    """Move a note into another workspace."""

    workspace: str


class Workspace(BaseModel):
    """A logical grouping of notes (a separate ``second brain`` namespace)."""

    id: str
    name: str
    #: Accent color (CSS value) for the switcher chip. Cosmetic only.
    color: str | None = None
    #: Optional lucide icon name rendered beside the workspace label.
    icon: str | None = None
    description: str = ""
    #: Manual sort order in the switcher (lower first).
    order: int | None = None
    created: str | None = None
    updated: str | None = None


class WorkspaceInfo(Workspace):
    """A workspace enriched with its live note count (list views)."""

    note_count: int = 0


class WorkspaceCreate(BaseModel):
    """Payload to create a workspace."""

    name: str
    color: str | None = None
    icon: str | None = None
    description: str = ""


class WorkspaceUpdate(BaseModel):
    """Partial update payload (only provided fields change)."""

    name: str | None = None
    color: str | None = None
    icon: str | None = None
    description: str | None = None
    order: int | None = None


class TreeNode(BaseModel):
    """A node in the derived page tree (sidebar navigation)."""

    id: str
    title: str
    children: list["TreeNode"] = Field(default_factory=list)


class SearchHit(BaseModel):
    """A ranked search result."""

    id: str
    title: str
    score: float
    snippet: str = ""
    kind: str = "keyword"  # keyword | semantic | hybrid


class GraphNode(BaseModel):
    """A node in the knowledge graph (a note, tag, or MOC)."""

    id: str
    label: str
    kind: str = "note"  # note | tag | moc
    degree: int = 0


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""

    source: str
    target: str
    kind: str = "explicit"  # explicit | derived | tag


class GraphData(BaseModel):
    """Serialized graph for the UI renderer."""

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class LinkSuggestion(BaseModel):
    """A suggested (currently unlinked) connection for a note."""

    id: str
    title: str
    score: float
    reason: str = "semantic"  # semantic | unlinked-mention


class TagInfo(BaseModel):
    """A tag with its usage count across the vault (tag browser)."""

    tag: str
    count: int = 0


class BacklinkContext(BaseModel):
    """A backlink enriched with the surrounding line of text (context)."""

    id: str
    title: str
    snippet: str = ""


class TemplateMeta(BaseModel):
    """Lightweight note-template descriptor."""

    id: str
    name: str
    updated: str | None = None


class Template(TemplateMeta):
    """A reusable note template — its body is inserted into new notes.

    The body may contain ``{{date}}``, ``{{time}}``, ``{{datetime}}`` and
    ``{{title}}`` placeholders, expanded at apply time.
    """

    body: str = ""


class TemplateCreate(BaseModel):
    """Payload to create / overwrite a template."""

    name: str
    body: str = ""


class DailyRequest(BaseModel):
    """Get-or-create the daily note for a date (``YYYY-MM-DD``; today if null)."""

    date: str | None = None
    #: Optional template id whose body seeds a freshly created daily note.
    template: str | None = None


class HistoryEntry(BaseModel):
    """One saved revision of a note (newest first)."""

    version: str  # opaque timestamp id
    saved: str  # ISO-8601 capture time
    size: int = 0


class TrashEntry(BaseModel):
    """A soft-deleted note awaiting restore or purge."""

    id: str
    title: str
    deleted: str | None = None

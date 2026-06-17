"""Expose the note vault over the Model Context Protocol (MCP).

Wraps the host's :class:`core.mcp.MCPServer` around the brain's read/write
services so any MCP client — Claude Desktop, an IDE, or a peer agent — can
search, read, list and create notes in the second brain.

Two transports share **one** tool definition (:func:`brain_tool_defs`):

* the host's central MCP server picks the tools up via the plugin's
  :meth:`get_mcp_tools` hook (stdio transport → Claude Desktop);
* :mod:`routers.mcp_router` serves the same tools over HTTP JSON-RPC (the MCP
  "streamable HTTP" transport) for standalone / mounted operation.

Everything is built lazily on first use, so a missing or misconfigured host MCP
layer can never break plugin import or the existing REST API.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Awaitable, Callable

from core.observability.logging import get_logger

from .index_state import get_index
from .models import NoteCreate

logger = get_logger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]


# ---------------------------------------------------------------------------
# Tool handlers — thin async wrappers over the derived index. Each returns
# JSON-serialisable data (dicts/lists) so the MCP layer can render it as text.
# ---------------------------------------------------------------------------
async def _brain_search(
    query: str, top_k: int = 10, workspace: str | None = None
) -> list[dict[str, Any]]:
    idx = get_index()
    scope = idx.note_ids(workspace) if workspace else None
    hits = await idx.search.search(query, top_k=top_k, scope=scope)
    return [h.model_dump() for h in hits]


async def _brain_get_note(note_id: str) -> dict[str, Any]:
    idx = get_index()
    if not idx.notes.exists(note_id):
        return {"error": f"note not found: {note_id}"}
    return idx.hydrate(note_id).model_dump()


async def _brain_list_notes(workspace: str | None = None) -> list[dict[str, Any]]:
    idx = get_index()
    return [m.model_dump() for m in idx.notes.list_meta(workspace=workspace)]


async def _brain_create_note(
    title: str,
    body: str = "",
    tags: list[str] | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    idx = get_index()
    note = idx.notes.create(
        NoteCreate(title=title, body=body, tags=tags or [], workspace=workspace)
    )
    # Mirror the REST create path: re-derive links/search so the new note is
    # immediately discoverable by subsequent tool calls.
    await idx.rebuild()
    return idx.hydrate(note.id).model_dump()


async def _brain_neighbors(note_id: str) -> dict[str, Any]:
    idx = get_index()
    if not idx.notes.exists(note_id):
        return {"error": f"note not found: {note_id}"}
    note = idx.hydrate(note_id)
    return {
        "id": note_id,
        "title": note.title,
        "tags": note.tags,
        "links": note.links,
        "backlinks": note.backlinks,
    }


# ---------------------------------------------------------------------------
# Tool definitions — single source of truth for both transports.
# ---------------------------------------------------------------------------
def _tool(
    name: str, description: str, schema: dict[str, Any], handler: ToolHandler
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_schema": schema,
        "handler": handler,
    }


def brain_tool_defs() -> list[dict[str, Any]]:
    """Return the MCP tool definitions exposed by the second brain."""
    return [
        _tool(
            "brain_search",
            "Search the second-brain note vault (BM25 keyword, fused with "
            "semantic when enabled). Returns ranked hits with title and snippet.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {
                        "type": "integer",
                        "description": "Max results (default 10)",
                        "default": 10,
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Restrict to one workspace id (optional)",
                    },
                },
                "required": ["query"],
            },
            _brain_search,
        ),
        _tool(
            "brain_get_note",
            "Fetch a single note by id, including its Markdown body and resolved "
            "forward links and backlinks.",
            {
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note id"},
                },
                "required": ["note_id"],
            },
            _brain_get_note,
        ),
        _tool(
            "brain_list_notes",
            "List note metadata (id, title, tags), optionally scoped to one workspace.",
            {
                "type": "object",
                "properties": {
                    "workspace": {
                        "type": "string",
                        "description": "Restrict to one workspace id (optional)",
                    },
                },
                "required": [],
            },
            _brain_list_notes,
        ),
        _tool(
            "brain_create_note",
            "Create a new note in the vault and return it. The note is indexed "
            "immediately so it is searchable right away.",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "body": {
                        "type": "string",
                        "description": "Markdown body (optional)",
                        "default": "",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags (optional)",
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Target workspace id (optional)",
                    },
                },
                "required": ["title"],
            },
            _brain_create_note,
        ),
        _tool(
            "brain_neighbors",
            "Return a note's graph neighbourhood: its tags, forward links and "
            "backlinks — useful for multi-hop exploration of the knowledge graph.",
            {
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note id"},
                },
                "required": ["note_id"],
            },
            _brain_neighbors,
        ),
    ]


@lru_cache(maxsize=1)
def get_mcp_server() -> Any:
    """Build (once) an :class:`MCPServer` with the brain tools registered.

    Imported lazily so plugin import never depends on the host MCP layer.
    """
    from core.mcp import MCPServer

    server = MCPServer(name="baselithbrain", version="0.1.0")
    for spec in brain_tool_defs():
        server.register_tool(
            name=spec["name"],
            description=spec["description"],
            input_schema=spec["input_schema"],
            handler=spec["handler"],
        )
    logger.info("baselithbrain_mcp_server_ready", tools=len(server._tools))
    return server

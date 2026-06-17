"""MCP endpoint — exposes the vault as MCP tools over HTTP.

Implements the MCP "streamable HTTP" transport: the client POSTs a JSON-RPC
message, the host :class:`MCPServer` routes it (``initialize`` / ``tools/list``
/ ``tools/call`` / …), and we return the JSON-RPC reply. Notifications (no
``id``) produce ``202 Accepted`` with an empty body.

Mounted under ``/baselithbrain``, the public URL is ``/baselithbrain/api/mcp``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from ..mcp_service import get_mcp_server

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


def _parse_error() -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error"},
        },
    )


@router.post("")
async def mcp_endpoint(request: Request) -> Response:
    """Handle a single MCP JSON-RPC request."""
    try:
        message: Any = await request.json()
    except Exception:  # noqa: BLE001 — any malformed body is a parse error
        return _parse_error()

    if not isinstance(message, dict):
        return _parse_error()

    reply = await get_mcp_server().handle_message(message)
    if reply is None:
        # Notification — acknowledged, nothing to return.
        return Response(status_code=202)
    return JSONResponse(reply)


@router.get("")
async def mcp_info() -> dict[str, Any]:
    """Lightweight discovery: server identity + registered tool names."""
    server = get_mcp_server()
    return {
        "name": server.info.name,
        "version": server.info.version,
        "transport": "streamable-http",
        "tools": list(server._tools.keys()),
    }

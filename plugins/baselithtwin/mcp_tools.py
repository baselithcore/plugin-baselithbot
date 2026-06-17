"""MCP tools exposing the twin's read/advisory surface.

Read-only and human-in-the-loop-safe tools only: status, style inspection,
salient-fact recall, and listing the approval queue. Sending or auto-approving
a reply is deliberately **not** exposed over MCP — those actions stay behind the
authenticated HTTP surface so an agent can never bypass the HITL gate.
"""

from __future__ import annotations

from typing import Any

from core.plugins.result import SkillResult, ok
from .service import TwinService


def build_twin_mcp_tools(service: TwinService, version: str) -> list[dict[str, Any]]:
    """Build the MCP tool descriptors for the twin service."""

    async def twin_status() -> SkillResult:
        """Report the twin's aggregate health and configuration."""
        status = await service.status(version)
        return ok(status.model_dump(mode="json"), message="twin status")

    async def twin_style() -> SkillResult:
        """Return the learned communicative-style profile."""
        profile = await service.get_style()
        data = profile.model_dump(mode="json") if profile else None
        return ok(data, message="style profile" if data else "style not trained")

    async def twin_recall_facts(contact_id: str | None = None) -> SkillResult:
        """Recall salient facts from long-term memory, optionally per contact."""
        facts = await service.list_facts(contact_id)
        return ok(
            [f.model_dump(mode="json") for f in facts], message=f"{len(facts)} facts"
        )

    async def twin_pending_replies(only_queued: bool = True) -> SkillResult:
        """List replies awaiting human approval (read-only; no decisions here)."""
        pending = await service.list_pending(only_queued=only_queued)
        return ok(
            [p.model_dump(mode="json") for p in pending],
            message=f"{len(pending)} replies",
        )

    return [
        {
            "name": "twin_status",
            "description": "Get the digital twin's health and configuration.",
            "handler": twin_status,
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "twin_style",
            "description": "Get the owner's learned communicative-style profile.",
            "handler": twin_style,
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "twin_recall_facts",
            "description": "Recall salient facts from the twin's long-term memory.",
            "handler": twin_recall_facts,
            "input_schema": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "Optional WhatsApp contact id to scope recall.",
                    }
                },
            },
        },
        {
            "name": "twin_pending_replies",
            "description": "List replies awaiting human approval (read-only).",
            "handler": twin_pending_replies,
            "input_schema": {
                "type": "object",
                "properties": {
                    "only_queued": {
                        "type": "boolean",
                        "description": "Only replies still awaiting a decision.",
                    }
                },
            },
        },
    ]


__all__ = ["build_twin_mcp_tools"]

"""The twin's orchestrator-facing agent.

A thin :class:`AgentPlugin` agent so the framework can route persona/style
requests ("reply as me", "draft a WhatsApp reply") into the twin. It generates a
reply in the owner's voice using the same style-grounded prompt the ingest path
uses, via the LLM service the framework injects.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger

logger = get_logger(__name__)


class TwinAgent:
    """Drafts replies in the owner's voice on demand."""

    name = "baselith-twin-agent"

    def __init__(self, llm_service: Any = None, owner_name: str = "Owner") -> None:
        self._llm = llm_service
        self._owner_name = owner_name

    async def execute(self, query: str, **_: Any) -> str:
        """Draft a reply to ``query`` as the owner.

        Degrades to an explanatory message if no LLM service is bound, so the
        agent never raises into the orchestration loop.
        """
        from .twin.prompt import build_system_prompt

        system = build_system_prompt(self._owner_name, None, [])
        if self._llm is None:
            return f"[{self._owner_name}'s twin] No LLM bound; cannot draft a reply."
        try:
            return await self._llm.generate_response(query, system_prompt=system)
        except Exception as exc:  # noqa: BLE001 — never crash the loop
            logger.warning("twin_agent_failed", error=str(exc))
            return f"[{self._owner_name}'s twin] Unable to draft a reply right now."


__all__ = ["TwinAgent"]

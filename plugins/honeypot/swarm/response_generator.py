"""LLM response generation mixin for HoneypotSwarmCoordinator.

Handles SSH and HTTP response generation using LLM agents.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .coordinator import HoneypotSwarmCoordinator


class ResponseGeneratorMixin:
    """Mixin providing LLM-powered response generation capabilities."""

    async def generate_ssh_response(
        self: "HoneypotSwarmCoordinator",
        command: str,
        session_id: str,
    ) -> str:
        """Generate LLM-powered SSH response.

        Args:
            command: Command from attacker
            session_id: Session ID

        Returns:
            Response to send
        """
        from .coordinator import PheromoneTypes

        session = self._sessions.get(session_id)
        context = None
        if session:
            context = {
                "username": session.username,
                "commands": session.commands[-5:],
            }

        response = await self._llm_responder.generate_ssh_response(
            command=command,
            session_context=context,
        )

        # Emit pheromone if attacker engaged
        if len(session.commands) > 3 if session else False:
            self._pheromones.emit(
                PheromoneTypes.DECEPTION_SUCCESS,
                strength=0.6,
                metadata={"session_id": session_id},
            )

        return response

    async def generate_http_response(
        self: "HoneypotSwarmCoordinator",
        path: str,
        method: str,
        body: Optional[str] = None,
    ) -> str:
        """Generate LLM-powered HTTP response.

        Args:
            path: HTTP request path
            method: HTTP method
            body: Optional request body

        Returns:
            Response to send
        """
        return await self._llm_responder.generate_http_response(
            path=path,
            method=method,
            body=body,
        )

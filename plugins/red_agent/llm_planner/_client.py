"""LLM client surface for the planner.

Decouples the planner from ``core.services.llm.LLMService`` so tests can
inject a deterministic mock.
"""

from __future__ import annotations

from typing import Any, Protocol


class _LLMService(Protocol):
    """Internal protocol for the LLM service methods used by the client."""

    async def generate_response(
        self,
        prompt: str,
        model: str | None = None,
        json: bool = False,
        system_prompt: str | None = None,
    ) -> str: ...


class LLMPlannerClient(Protocol):
    """Minimal async LLM surface the planner depends on.

    Decouples the planner from ``core.services.llm.LLMService`` so tests
    can inject a deterministic mock. ``complete`` returns the model
    response text plus the total tokens billed for the call (input +
    output). The wrapper :class:`CoreLLMServiceClient` adapts the
    real service.
    """

    async def complete(
        self,
        *,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]: ...


class CoreLLMServiceClient:
    """Adapter over ``core.services.llm.LLMService.generate_response``.

    Reuses the production caching/cost-control/circuit-breaker stack
    instead of speaking to the provider directly. Token usage is read
    from the service's tracker per-call when available, otherwise an
    estimate based on prompt + response length is used.
    """

    _service: _LLMService | Any | None

    def __init__(self, service: _LLMService | Any | None = None) -> None:
        self._service = service

    async def complete(
        self,
        *,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        if self._service is None:
            from core.services.llm.service import get_llm_service

            self._service = get_llm_service()

        from core.services.llm.cost_control import estimate_tokens

        text = await self._service.generate_response(
            prompt=prompt,
            model=model,
            json=True,
            system_prompt=system,
        )
        tokens = estimate_tokens(prompt) + estimate_tokens(text)
        del max_tokens, temperature  # forwarded via service config
        return text, tokens

"""
ConfessGPT — LLM backend adapter.

Wraps ``core.services.llm.LLMService`` into the minimal ``LLMBackend``
protocol the flow expects. Caching is disabled because every
sacramental turn is unique and we never want to reuse a generated
utterance for a different penitent.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from core.services.llm import LLMService

logger = get_logger(__name__)


class LLMServiceBackend:
    """Adapter from ``LLMService`` to the flow's ``LLMBackend`` protocol."""

    def __init__(
        self,
        *,
        service: LLMService,
        model_id: str | None = None,
    ) -> None:
        self._service = service
        self._model_id = model_id

    async def generate(self, prompt: str, *, system: str) -> str:
        """Generate a confessor turn in JSON mode."""
        return await self._service.generate_response(
            prompt=prompt,
            model=self._model_id,
            json=True,
            system_prompt=system,
        )


def build_llm_service(*, enable_cache: bool = False) -> LLMService:
    """Construct a fresh ``LLMService`` with caching disabled.

    Caching is disabled by default so identical prompts (rare but
    possible across sessions) never produce shared output: every
    sacrament is its own act.
    """
    return LLMService(enable_cache=enable_cache)

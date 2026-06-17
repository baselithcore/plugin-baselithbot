"""The draft-generation engine — turns an inbound message into a reply draft.

Composes the persona prompt (style + memory) and calls the core LLM service to
produce a reply in the owner's voice. The LLM is bound lazily and every failure
degrades to a deterministic template reply, so the engine never raises into the
ingest path and the plugin works with no LLM configured.
"""

from __future__ import annotations

from core.observability.logging import get_logger

from ..gateway.models import InboundMessage
from ..models import DraftReply, SalientFact
from ..style.models import StyleProfile
from .prompt import build_system_prompt, build_user_prompt

logger = get_logger(__name__)


class DraftEngine:
    """Generates style- and memory-grounded reply drafts."""

    def __init__(self, owner_name: str) -> None:
        self._owner_name = owner_name

    async def draft(
        self,
        message: InboundMessage,
        profile: StyleProfile | None,
        facts: list[SalientFact],
        history: list[InboundMessage],
    ) -> DraftReply:
        """Produce a :class:`DraftReply` for ``message``.

        Tries the LLM first; on any error (no provider, budget, network) returns
        a clearly-flagged template fallback so the caller always gets a draft.
        """
        system = build_system_prompt(self._owner_name, profile, facts)
        user = build_user_prompt(message, history)
        try:
            text = await self._generate(system, user)
        except Exception as exc:  # noqa: BLE001 — degrade, never crash ingest
            logger.warning("twin_draft_degraded", error=str(exc))
            return self._fallback(message, profile)

        text = text.strip()
        if not text:
            return self._fallback(message, profile)
        return DraftReply(
            contact_id=message.contact_id,
            in_reply_to=message.id,
            text=text,
            confidence=0.7 if (profile and profile.trained) else 0.5,
            style_applied=bool(profile and profile.trained),
            degraded=False,
            rationale="LLM reply grounded in style profile and salient facts.",
        )

    @staticmethod
    async def _generate(system: str, user: str) -> str:
        """Call the core LLM service (lazy import keeps discovery cheap)."""
        from core.services.llm.service import get_llm_service

        service = get_llm_service()
        return await service.generate_response(user, system_prompt=system)

    def _fallback(
        self, message: InboundMessage, profile: StyleProfile | None
    ) -> DraftReply:
        """Deterministic, low-confidence reply used when the LLM is unavailable."""
        locale = profile.metrics.dominant_locale if profile else "en"
        text = (
            "Ciao! Ho ricevuto il tuo messaggio, ti rispondo a breve."
            if locale == "it"
            else "Hi! Got your message, I'll get back to you shortly."
        )
        return DraftReply(
            contact_id=message.contact_id,
            in_reply_to=message.id,
            text=text,
            confidence=0.2,
            style_applied=False,
            degraded=True,
            rationale="Template fallback — no LLM available.",
        )


__all__ = ["DraftEngine"]

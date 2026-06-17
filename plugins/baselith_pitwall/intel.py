"""AI synthesis layer — turns fused indicators into an intelligence brief.

This is the "AI processes the fused data" step: the cross-source
:class:`~.ontology.IndicatorSet` is handed to the core LLM, which writes a
concise strategist's read of the situation. The brief is grounded strictly in
the fused indicators and their provenance, so it never invents data. With no LLM
configured it degrades to a deterministic, provenance-aware summary.
"""

from __future__ import annotations

from core.observability.logging import get_logger

from .ontology import IndicatorSet

logger = get_logger(__name__)


class IntelSynthesizer:
    """Produces a natural-language intelligence brief from fused indicators."""

    def __init__(self, use_llm: bool = True, model: str | None = None) -> None:
        self._use_llm = use_llm
        self._model = model

    async def brief(self, indicators: IndicatorSet) -> str:
        """Synthesise a short strategist's read of the fused picture."""
        if not indicators.indicators:
            return "No fused signals yet."
        template = self._template(indicators)
        if not self._use_llm:
            return template
        try:
            from core.services.llm.service import get_llm_service

            service = get_llm_service()
            prompt = self._prompt(indicators)
            text = await service.generate_response(prompt, model=self._model)
            return text.strip() or template
        except Exception as exc:  # noqa: BLE001 — graceful degrade
            logger.info("pitwall_intel_llm_unavailable", error=str(exc))
            return template

    def _prompt(self, indicators: IndicatorSet) -> str:
        """Build a grounded prompt from the fused indicators + provenance."""
        lines = [
            f"You are a Formula race strategy intelligence analyst. Car "
            f"{indicators.car_id}, lap {indicators.lap}. Below are fused, "
            "cross-source indicators (0..1) with their source provenance and "
            "confidence. Write a 2-3 sentence intelligence brief: the single most "
            "important read, the key risk, and the recommended posture. Ground "
            "every claim in the indicators; do not invent data.\n",
        ]
        for ind in indicators.top(5):
            srcs = "+".join(s.value for s in ind.provenance.sources)
            lines.append(
                f"- {ind.label}: {ind.value:.2f} ({ind.severity.value}, "
                f"conf {ind.confidence:.2f}, agree {ind.provenance.agreement:.2f}, "
                f"sources {srcs}) — {ind.rationale}"
            )
        lines.append("\nIntelligence brief:")
        return "\n".join(lines)

    @staticmethod
    def _template(indicators: IndicatorSet) -> str:
        """Deterministic, provenance-aware fallback brief."""
        top = indicators.top(3)
        parts = [
            f"{i.label} {i.value:.0%} ({i.severity.value}, "
            f"{i.provenance.source_count} sources)"
            for i in top
        ]
        lead = top[0]
        return (
            f"Top read: {lead.label} at {lead.value:.0%} "
            f"[{lead.severity.value}]. {lead.rationale} "
            f"Fused picture — {'; '.join(parts)}."
        )


__all__ = ["IntelSynthesizer"]

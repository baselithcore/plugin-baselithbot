"""Groundedness scoring — how faithful is an answer to the cited notes.

Reuses the host's LLM-as-judge (``core.evaluation`` ``FaithfulnessEvaluator``)
to score, *after* the answer has streamed, how much of it is supported by the
retrieved note context. Surfaced to the UI as a trust badge.

Entirely best-effort: a missing evaluator, a judge failure, or a fallback
verdict all yield ``None`` so the chat turn is never affected. It reuses the
already-acquired LLM client, so no extra service is spun up — just one extra
judge call, which runs off the critical path (tokens are already on the wire).
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger

logger = get_logger(__name__)


async def score_groundedness(
    llm: Any, question: str, context: str, answer: str
) -> dict[str, Any] | None:
    """Return ``{score, level, feedback}`` or ``None`` if unavailable.

    ``score`` is 0.0–1.0 (1.0 = fully supported by the cited notes); ``level``
    is the coarse :class:`QualityLevel` label.
    """
    if not answer.strip() or not context.strip():
        return None
    try:
        from core.evaluation.judges import FaithfulnessEvaluator  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 — optional capability
        logger.info("groundedness scorer unavailable: %s", exc)
        return None

    try:
        evaluator = FaithfulnessEvaluator(llm_service=llm)
        result = await evaluator.evaluate(answer, question, {"memory_context": context})
    except Exception as exc:  # noqa: BLE001 — never break the chat turn
        logger.warning("groundedness scoring failed: %s", exc)
        return None

    if result.metadata.get("fallback"):
        # Judge errored internally and returned a placeholder — don't mislead.
        return None
    return {
        "score": round(float(result.score), 3),
        "level": result.quality.value,
        "feedback": result.feedback,
    }

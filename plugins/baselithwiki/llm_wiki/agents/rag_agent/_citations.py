"""Citation validation + repair-loop helpers."""

from __future__ import annotations

import logging
from typing import Any

from llm_wiki.agents.citation_validator import (
    CitationReport,
    build_repair_feedback,
)
from llm_wiki.agents.citation_validator import (
    validate as validate_citations,
)
from llm_wiki.agents.rag_guards import rag_sampling_options
from llm_wiki.config import (
    CITATION_REPAIR_ENABLED,
    CITATION_STRICT_GROUNDING,
    CITATION_VALIDATION_ENABLED,
)
from llm_wiki.domain.registry import get_pack
from llm_wiki.utils.llm import generate

logger = logging.getLogger(__name__)


def allowed_citation_folders() -> set[str]:
    """Folder ammessi nei wikilink (taxonomy del pack attivo).

    Risolto al volo via :func:`get_pack` per non legare l'agent al pack
    a costruzione (il pack può cambiare fra invocazioni in contesti di
    test). Ritorna set vuoto se il pack non è caricato — disattiva la
    validation (graceful).
    """
    try:
        pack = get_pack()
    except Exception:
        return set()
    out: set[str] = set()
    for pt in pack.page_types:
        folder = pt.folder or pt.plural or pt.id
        if folder:
            out.add(folder)
    return out


def validate(*, answer: str, sources: list[dict[str, Any]]) -> CitationReport | None:
    """Esegui la validazione delle citazioni; ritorna ``None`` se
    disabilitata via env o se il pack non è disponibile."""
    if not CITATION_VALIDATION_ENABLED or not answer:
        return None
    folders = allowed_citation_folders()
    if not folders:
        return None
    from llm_wiki.config import CITATION_ANCHOR_VALIDATION_ENABLED

    report = validate_citations(
        answer,
        allowed_folders=folders,
        sources=sources,
        strict_grounding=CITATION_STRICT_GROUNDING,
        validate_anchors=CITATION_ANCHOR_VALIDATION_ENABLED,
    )
    if report.has_violations:
        logger.warning("[rag] citation violations: %s", report.summary())
    return report


def maybe_repair(
    *,
    answer: str,
    sources: list[dict[str, Any]],
    messages: list[dict[str, str]],
) -> tuple[str, CitationReport | None]:
    """Valida + (se abilitato e ci sono violazioni) ricomponi via
    repair-loop LLM con feedback strutturato.

    Costo del repair: 1 LLM call extra. Solo path sync; nello stream
    l'eventuale repair romperebbe l'UX dei token già emessi — meglio
    segnalare al frontend via evento.
    """
    report = validate(answer=answer, sources=sources)
    if report is None or not report.has_violations or not CITATION_REPAIR_ENABLED:
        return answer, report

    feedback = build_repair_feedback(report, sources)
    repair_messages = [
        *messages,
        {"role": "assistant", "content": answer},
        {"role": "user", "content": feedback},
    ]
    try:
        repaired = generate(
            messages=repair_messages,
            use_cache=False,
            options=rag_sampling_options(),
        )
    except Exception as exc:
        logger.warning("[rag] repair-loop fallito (%s) — uso risposta originale", exc)
        return answer, report
    post = validate(answer=repaired, sources=sources)
    if post and post.has_violations:
        logger.warning("[rag] repair non risolve completamente: %s", post.summary())
    return repaired, post or report

"""Guard helpers used by :class:`RAGAgent`.

Wrappers per ciascuna policy difensiva (intent / groundedness / code-block
/ numeric) + sampling options. Ogni helper rispetta il proprio feature
flag e ritorna ``None`` quando disabilitato, così il chiamante può
testarne il risultato senza branching ridondante.

Estratti da ``rag_agent.py`` per rispettare il budget 500 LOC/file.
Comportamento invariato; nessuna nuova logica.
"""

from __future__ import annotations

from typing import Any

from llm_wiki.agents.code_block_guard import (
    CodeBlockReport,
    strip_fabricated_fences,
)
from llm_wiki.agents.code_block_guard import (
    analyze as analyze_code_blocks,
)
from llm_wiki.agents.groundedness import (
    GroundednessReport,
)
from llm_wiki.agents.groundedness import (
    score as score_groundedness,
)
from llm_wiki.agents.intent_classifier import IntentReport
from llm_wiki.agents.intent_classifier import analyze as analyze_intent
from llm_wiki.agents.numeric_guard import (
    NumericGuardReport,
    strip_unsupported_numerics,
)
from llm_wiki.agents.numeric_guard import (
    analyze as analyze_numeric_claims,
)
from llm_wiki.config import (
    RAG_CODE_BLOCK_GUARD_ENABLED,
    RAG_CODE_BLOCK_STRIP,
    RAG_GROUNDEDNESS_ENABLED,
    RAG_GROUNDEDNESS_MIN,
    RAG_GROUNDEDNESS_MODEL,
    RAG_INTENT_GUARD_ENABLED,
    RAG_NUM_PREDICT,
    RAG_NUMERIC_GUARD_ENABLED,
    RAG_NUMERIC_GUARD_INCLUDE_GENERIC,
    RAG_NUMERIC_STRIP,
    RAG_SEED,
    RAG_TEMPERATURE,
    RAG_TOP_P,
)


def maybe_intent_report(
    question: str,
    context_text: str,
    hits: list[dict[str, Any]] | None = None,
) -> IntentReport | None:
    """Calcola l'``IntentReport`` quando l'intent-guard è attivo.

    Passa anche gli ``hits`` al classifier: i payload Qdrant possono
    contenere ``doc_register`` esplicito (ingest-time, deterministico),
    signal preferito rispetto all'euristica regex su ``context_text``.
    Output ``None`` solo se la feature è disabilitata via env
    (``RAG_INTENT_GUARD_ENABLED=false``).
    """
    if not RAG_INTENT_GUARD_ENABLED:
        return None
    return analyze_intent(question, context_text, hits=hits)


def apply_intent_warning(context_text: str, report: IntentReport | None) -> str:
    """Prepend dello scope-warning al CONTESTO quando c'è mismatch.

    No-op se il report è None o non rileva mismatch. Il warning è marcato
    come commento HTML così il modello lo distingue dai chunk del vault.
    """
    if not report or not report.mismatch:
        return context_text
    return f"{report.warning_block()}{context_text}"


def maybe_score_groundedness(answer: str, context: str) -> GroundednessReport | None:
    """Lancia il judge solo se ``RAG_GROUNDEDNESS_ENABLED`` e c'è risposta da valutare."""
    if not RAG_GROUNDEDNESS_ENABLED or not answer or not context:
        return None
    return score_groundedness(
        answer,
        context,
        threshold=RAG_GROUNDEDNESS_MIN,
        model=RAG_GROUNDEDNESS_MODEL or None,
    )


def rag_sampling_options() -> dict[str, Any]:
    """Opzioni di sampling per le chiamate LLM del RAG.

    Forziamo bassa temperatura per privilegiare l'aderenza al CONTESTO
    sopra la creatività. Letto al volo da env (via :mod:`config`) per
    consentire override a runtime senza restart durante tuning.
    """
    opts: dict[str, Any] = {
        "temperature": RAG_TEMPERATURE,
        "top_p": RAG_TOP_P,
    }
    if RAG_NUM_PREDICT and RAG_NUM_PREDICT > 0:
        opts["num_predict"] = RAG_NUM_PREDICT
    if RAG_SEED:
        opts["seed"] = RAG_SEED
    return opts


def maybe_check_code_blocks(answer: str, context: str) -> CodeBlockReport | None:
    if not RAG_CODE_BLOCK_GUARD_ENABLED or not answer:
        return None
    return analyze_code_blocks(answer, context)


def maybe_strip_code_blocks(answer: str, report: CodeBlockReport | None) -> str:
    if not report or not report.has_violations or not RAG_CODE_BLOCK_STRIP:
        return answer
    return strip_fabricated_fences(answer, report)


def maybe_check_numerics(answer: str, context: str) -> NumericGuardReport | None:
    """Lancia il numeric guard se abilitato e c'è risposta+contesto."""
    if not RAG_NUMERIC_GUARD_ENABLED or not answer or not context:
        return None
    return analyze_numeric_claims(
        answer, context, include_generic=RAG_NUMERIC_GUARD_INCLUDE_GENERIC
    )


def maybe_strip_numerics(answer: str, report: NumericGuardReport | None) -> str:
    if not report or not report.has_violations or not RAG_NUMERIC_STRIP:
        return answer
    return strip_unsupported_numerics(answer, report)


__all__ = [
    "apply_intent_warning",
    "maybe_check_code_blocks",
    "maybe_check_numerics",
    "maybe_intent_report",
    "maybe_score_groundedness",
    "maybe_strip_code_blocks",
    "maybe_strip_numerics",
    "rag_sampling_options",
]

"""History-aware query condensing for conversational RAG.

Modern conversational RAG best practice (LangChain
``create_history_aware_retriever``, LlamaIndex ``CondenseQuestion``,
OpenAI Assistants memory): when prior turns exist, follow-up questions
("approfondiscilo", "e per la v3?", "perché?") arrive at retrieval as
bare strings that match nothing semantically — the dense/sparse
indices cannot resolve anaphora. The fix is to rewrite the question
into a self-contained, standalone form BEFORE retrieval, using the
last N turns as resolution context.

Two-stage gate:

1. **Heuristic skip** — if no history, or the question is already
   long and self-contained (no anaphoric / continuation markers),
   skip the LLM call entirely. Saves latency + cost on the typical
   first turn or new-topic switch.
2. **LLM condense** — single fast call with a strict prompt that
   yields only the rewritten standalone query. Output is clamped to
   ``RAG_HISTORY_CONDENSE_MAX_OUTPUT_CHARS`` so a misbehaving model
   can't return a mini-essay.

Fallback-safe at every step: any failure → return original question
verbatim (degrades cleanly to the legacy retrieval path).

The condensed query is used ONLY for retrieval. Synthesis still
receives the ORIGINAL question + full history block — the LLM must
see the user's wording to keep the answer phrased naturally and to
avoid the "but I asked X" UX regression where the model answers a
rephrased question and the user is confused.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from llm_wiki.config import (
    RAG_HISTORY_CONDENSE_ENABLED,
    RAG_HISTORY_CONDENSE_MAX_OUTPUT_CHARS,
    RAG_HISTORY_CONDENSE_MAX_TURNS,
    RAG_HISTORY_CONDENSE_MODEL,
    RAG_HISTORY_TURN_MAX_CHARS,
)

logger = logging.getLogger(__name__)


# Markers that strongly suggest the question depends on prior context.
# IT + EN coverage. Word-boundary, case-insensitive. False positives are
# cheap (an extra LLM call); false negatives are expensive (retrieval
# returns garbage). NB: bare IT object pronouns ``lo/la/le/gli/li`` are
# OMITTED because they collide with articles ("le differenze fra…") —
# instead we keep the unambiguous imperative forms ("approfondiscilo")
# and demonstrative pronouns.
_ANAPHORA_PATTERNS: tuple[str, ...] = (
    # Italian demonstratives + neutral pronouns (unambiguous when bare)
    r"\b(?:quello|quella|quelli|quelle|ciò|esso|essa|essi|esse)\b",
    # Imperative continuations with attached object clitic
    r"\b(?:approfondisci|spiegami|dimmi|elaboralo|elaborala|continua|prosegui|elabora)(?:lo|la|li|le|gli|mi|ci|ne)?\b",
    # Continuation cues (must be at sentence start to be unambiguous)
    r"^(?:e|ma|invece|inoltre|anche|altro)\b",
    # "questo/questa/questi/queste" pronoun standalone (NOT followed by noun)
    r"\bquest[oaie]\?",
    r"\bquest[oaie]$",
    # Explicit follow-up phrases
    r"\brispetto a (?:quello|questo|ciò|quelli|questi)\b",
    r"\bcosa intend[io]\b",
    r"\bcome mai\b",
    r"\bperché\??$",
    r"^perché\b",
    # English demonstrative/anaphoric markers
    r"\b(?:it|its|this|that|these|those|they|them|their)\b",
    r"\b(?:expand|elaborate|continue|further)\b",
    r"\bwhat about\b",
    r"\bhow about\b",
    r"\bhow come\b",
    r"^why\??$",
)
_ANAPHORA_RE = re.compile("|".join(_ANAPHORA_PATTERNS), re.IGNORECASE | re.MULTILINE)

# Below this length the question is too short to risk skipping —
# ellipsis ("e altro?", "perché?") needs condensing. Above, only if
# no anaphora marker. Conservative: a missed condense costs a wasted
# retrieval, a missed skip costs a wasted LLM call. The latter is
# cheaper, so we keep the threshold low.
_LONG_QUESTION_THRESHOLD = 30


@dataclass
class CondenseResult:
    """Outcome of the condensing pipeline.

    - ``query``: query da passare al retrieval (original o rewritten).
    - ``original``: domanda utente verbatim.
    - ``rewritten``: True quando la query passa al retrieval ≠ originale.
    - ``skip_reason``: stringa diagnostica quando rewrite NON eseguito
      (``"no_history"``, ``"heuristic_standalone"``, ``"disabled"``,
      ``"llm_failed"``, ``"empty_output"``). ``None`` quando rewritten.
    """

    query: str
    original: str
    rewritten: bool = False
    skip_reason: str | None = None


def _looks_standalone(question: str) -> bool:
    """Heuristic: long question without anaphoric markers = standalone.

    Conservative — biased toward returning False (i.e. ``condense``)
    because the cost of a wasted LLM call is small vs. the cost of
    leaving an unresolved follow-up to the retriever.
    """
    if _ANAPHORA_RE.search(question):
        return False
    return len(question) >= _LONG_QUESTION_THRESHOLD


def _format_history_for_condense(turns: list[dict[str, Any]], max_turns: int) -> str:
    """Compact dialog format for the condense prompt. Drops system role,
    trims long turns, caps total turns to ``max_turns`` keeping the
    most-recent N (slice end)."""
    if not turns:
        return ""
    keep = [t for t in turns if (t.get("role") in ("user", "assistant"))][-max_turns:]
    lines: list[str] = []
    for t in keep:
        role = "Utente" if t.get("role") == "user" else "Assistente"
        content = (t.get("content") or "").strip()
        if not content:
            continue
        if len(content) > RAG_HISTORY_TURN_MAX_CHARS:
            content = content[: RAG_HISTORY_TURN_MAX_CHARS - 1].rstrip() + "…"
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


_CONDENSE_SYSTEM = """Sei un riformulatore di query per un sistema RAG conversazionale.

Compito: data una conversazione precedente e una nuova domanda dell'utente, riscrivi \
la domanda in forma AUTONOMA (standalone) che possa essere capita SENZA leggere lo \
storico. Risolvi pronomi anaforici ("quello", "lo", "it", "this"), riferimenti \
impliciti ("approfondiscilo", "e per la v3?", "perché?"), e continuazioni ellittiche.

Regole strette:
- Output: SOLO la query riscritta, una riga, niente preambolo né punteggiatura finale superflua.
- Mantieni la lingua originale (italiano se la domanda è in italiano, inglese altrimenti).
- Se la nuova domanda è GIÀ autonoma (cambio di topic, niente riferimenti impliciti),  \
restituiscila INVARIATA verbatim.
- Mai inventare entità non presenti nello storico o nella domanda.
- Massimo {max_chars} caratteri. Sintetica e precisa, non discorsiva.
- NIENTE risposta, NIENTE spiegazioni, NIENTE prefissi tipo "Query riscritta:".
"""


_CONDENSE_USER = """Conversazione precedente:
{history}

Nuova domanda dell'utente:
{question}

Query autonoma:"""


def _resolve_condense_model() -> str:
    """Modello dedicato → fallback su vendor default."""
    from llm_wiki import config

    if RAG_HISTORY_CONDENSE_MODEL:
        return RAG_HISTORY_CONDENSE_MODEL
    vendor = (config.RAG_VENDOR or config.LLM_VENDOR or "ollama").lower()
    if vendor == "openai":
        return config.OPENAI_MODEL
    return config.OLLAMA_MODEL


def _clean_llm_output(raw: str) -> str:
    """Strip surrounding quotes / prefixes some models add despite the
    instruction. Cap to budget. Single line."""
    s = (raw or "").strip()
    # Some models prepend "Query autonoma:" / "Standalone:" etc.
    s = re.sub(
        r"^(?:query\s+autonoma|standalone(?:\s+query)?|risposta)\s*[:\-]\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    # Strip wrapping quotes/backticks/brackets.
    s = s.strip().strip("`\"'“”‘’").strip()
    # Collapse newlines (we want one line).
    s = re.sub(r"\s+", " ", s)
    if len(s) > RAG_HISTORY_CONDENSE_MAX_OUTPUT_CHARS:
        s = s[: RAG_HISTORY_CONDENSE_MAX_OUTPUT_CHARS - 1].rstrip() + "…"
    return s.strip()


def condense_question(
    question: str,
    history_turns: list[dict[str, Any]],
    *,
    enabled: bool | None = None,
    max_turns: int | None = None,
) -> CondenseResult:
    """Riscrive ``question`` in forma standalone usando ``history_turns``.

    Args:
        question: domanda corrente dell'utente.
        history_turns: turni precedenti (formato ``{role, content}``,
            chronological ordine crescente). Vuoto = skip.
        enabled: override del flag env ``RAG_HISTORY_CONDENSE_ENABLED``
            (utile per test). ``None`` = usa env.
        max_turns: override del cap turni nel prompt.

    Returns:
        :class:`CondenseResult` — ``query`` è la stringa da passare al
        retrieval. Su qualsiasi failure / skip ritorna la query originale.
    """
    original = (question or "").strip()
    if not original:
        return CondenseResult(query="", original="", skip_reason="empty_question")

    flag = enabled if enabled is not None else RAG_HISTORY_CONDENSE_ENABLED
    if not flag:
        return CondenseResult(query=original, original=original, skip_reason="disabled")

    if not history_turns:
        return CondenseResult(
            query=original, original=original, skip_reason="no_history"
        )

    if _looks_standalone(original):
        return CondenseResult(
            query=original, original=original, skip_reason="heuristic_standalone"
        )

    history_block = _format_history_for_condense(
        history_turns,
        max_turns=max_turns
        if max_turns is not None
        else RAG_HISTORY_CONDENSE_MAX_TURNS,
    )
    if not history_block:
        return CondenseResult(
            query=original, original=original, skip_reason="no_history"
        )

    # Lazy import + namespace indirection so tests can monkeypatch
    # ``llm_wiki.agents.rag_agent.generate``.
    from llm_wiki.agents import rag_agent as _pkg

    system_msg = _CONDENSE_SYSTEM.format(
        max_chars=RAG_HISTORY_CONDENSE_MAX_OUTPUT_CHARS
    )
    user_msg = _CONDENSE_USER.format(history=history_block, question=original)
    try:
        raw = _pkg.generate(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            model=_resolve_condense_model() or None,
            use_cache=True,
            # Low-temperature sampling: deterministic rewriting beats
            # creative paraphrase. Use the same options shape as
            # ``rag_sampling_options`` for vendor portability.
            options={"temperature": 0.0, "top_p": 0.9, "num_predict": 256, "seed": 0},
        )
    except Exception as exc:
        logger.warning("[condense] LLM failed (%s) — keep original query", exc)
        return CondenseResult(
            query=original, original=original, skip_reason="llm_failed"
        )

    cleaned = _clean_llm_output(raw)
    if not cleaned:
        return CondenseResult(
            query=original, original=original, skip_reason="empty_output"
        )

    # No-op detection (case-insensitive whitespace-normalised). Model
    # decided the query is already standalone — record as not-rewritten
    # to suppress UI noise.
    if cleaned.casefold().strip() == original.casefold().strip():
        return CondenseResult(
            query=original, original=original, skip_reason="model_kept_original"
        )

    logger.info("[condense] '%s' → '%s'", original[:60], cleaned[:60])
    return CondenseResult(query=cleaned, original=original, rewritten=True)


__all__ = ["CondenseResult", "condense_question"]

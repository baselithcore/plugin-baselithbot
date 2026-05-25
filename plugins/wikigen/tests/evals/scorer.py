"""Metriche di valutazione retrieval e generation per RAG.

Tre famiglie:

- **Retrieval**: ``recall_at_k``, ``mrr`` su match per ``document_id``
  (id canonico delle pagine wiki, presente nel payload Qdrant).
- **Generation grounding**: ``citation_grounding`` calcola quanto della
  risposta è ancorato a citation valide (riusa
  :mod:`llm_wiki.agents.citation_validator`).
- **LLM-as-judge** (opzionale, costoso): ``faithfulness_judge`` chiede
  al modello di valutare se la risposta è supportata dal contesto.
  Disabilitato di default — abilitalo in CLI con ``--with-judge``.

Tutte le funzioni sono pure (no I/O, no globals). Caller orchestra
loading del golden set + invocazione del retrieval/generation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetrievalScores:
    recall_at_k: float
    mrr: float
    hits_returned: int
    expected_docs: int


@dataclass
class GenerationScores:
    citation_precision: float  # citazioni valide / citazioni totali
    citation_recall: float  # sources citati / sources recuperati
    has_violations: bool
    judge_score: float | None = None  # 0..1 se faithfulness_judge eseguito


def recall_at_k(
    retrieved_doc_ids: list[str], expected_doc_ids: list[str], *, k: int
) -> RetrievalScores:
    """Frazione di doc attesi che appaiono nei primi K hit."""
    if not expected_doc_ids:
        return RetrievalScores(
            recall_at_k=0.0,
            mrr=0.0,
            hits_returned=len(retrieved_doc_ids),
            expected_docs=0,
        )
    top_k_set = set(retrieved_doc_ids[:k])
    expected_set = set(expected_doc_ids)
    hits = len(top_k_set & expected_set)
    recall = hits / len(expected_set)

    # MRR: 1 / rank del primo expected trovato (0 se nessuno)
    mrr_val = 0.0
    for rank, doc_id in enumerate(retrieved_doc_ids[:k], start=1):
        if doc_id in expected_set:
            mrr_val = 1.0 / rank
            break

    return RetrievalScores(
        recall_at_k=recall,
        mrr=mrr_val,
        hits_returned=len(retrieved_doc_ids),
        expected_docs=len(expected_set),
    )


def citation_grounding(
    *,
    answer: str,
    sources: list[dict[str, Any]],
    allowed_folders: set[str],
) -> GenerationScores:
    """Misura precision/recall delle citazioni nella risposta.

    - **Precision**: frazione di wikilink emessi che sono validi
      (folder in taxonomy + slug in sources).
    - **Recall**: frazione di sources recuperati che sono stati
      effettivamente citati nella risposta.
    """
    from llm_wiki.agents.citation_validator import validate

    report = validate(
        answer, allowed_folders=allowed_folders, sources=sources, strict_grounding=True
    )
    total = len(report.valid) + len(report.violations)
    precision = (len(report.valid) / total) if total else 1.0

    cited_ids = {f"{f}/{s}" for f, s, _ in report.valid} | {
        s for _, s, _ in report.valid
    }
    source_ids = {
        s.get("document_id") for s in sources if isinstance(s.get("document_id"), str)
    }
    recall = (
        len([sid for sid in source_ids if sid in cited_ids]) / len(source_ids)
        if source_ids
        else 0.0
    )
    return GenerationScores(
        citation_precision=precision,
        citation_recall=recall,
        has_violations=report.has_violations,
    )


_JUDGE_PROMPT = """\
Sei un valutatore RAG. Dato un CONTESTO recuperato e una RISPOSTA,
valuta quanto la risposta è SUPPORTATA esclusivamente dal contesto
(faithfulness/groundedness).

Score:
- 1.0 = ogni affermazione della risposta è verificabile nel contesto.
- 0.5 = parzialmente supportata (alcuni claim non verificabili).
- 0.0 = la risposta inventa informazioni assenti dal contesto.

Rispondi SOLO con un oggetto JSON: {"score": <float>, "reason": "<≤120 char>"}
"""


def faithfulness_judge(
    *,
    question: str,
    answer: str,
    context: str,
    model: str | None = None,
) -> float | None:
    """LLM-as-judge per faithfulness. Ritorna score 0..1 o ``None`` se
    la call fallisce (eval prosegue senza giudizio).

    Costo: 1 LLM call per (question, answer). Usa il modello di RAG
    di default se ``model`` è ``None``. Per produzione consigliato un
    modello forte (claude-haiku, gpt-4o-mini); locale modelli >=7B.
    """
    from llm_wiki.utils.llm import generate

    user_msg = (
        f"DOMANDA:\n{question}\n\nCONTESTO:\n{context[:4000]}\n\n"
        f"RISPOSTA:\n{answer[:2000]}\n\n"
        "Valuta la faithfulness."
    )
    try:
        raw = generate(
            messages=[
                {"role": "system", "content": _JUDGE_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            json_mode=True,
            use_cache=False,
        )
    except Exception as exc:
        logger.warning("[evals] judge call failed: %s", exc)
        return None
    try:
        payload = json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.warning("[evals] judge returned non-JSON: %r", raw[:120])
        return None
    score = payload.get("score")
    if isinstance(score, int | float):
        return max(0.0, min(1.0, float(score)))
    return None

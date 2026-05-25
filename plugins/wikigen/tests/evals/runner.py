"""Eval runner: golden set JSONL → retrieval + (optional) generation → report.

Golden set format (JSONL, una riga per query)::

    {
      "id": "q-001",
      "question": "Quali sono le esclusioni per il furto in abitazione?",
      "expected_doc_ids": ["concepts/esclusioni-furto", "sources/cga-art-12"],
      "page_type": null,
      "notes": "regression: bug #123"
    }

Output: lista di :class:`EvalRecord`, una per query, + aggregati
:class:`EvalSummary`. Caller (CLI) decide se stampare in TTY,
serializzare in JSON, o asserire soglie in pytest.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tests.evals.scorer import (
    GenerationScores,
    RetrievalScores,
    citation_grounding,
    faithfulness_judge,
    recall_at_k,
)

logger = logging.getLogger(__name__)


@dataclass
class GoldenQuery:
    id: str
    question: str
    expected_doc_ids: list[str]
    page_type: str | None = None
    notes: str = ""


@dataclass
class EvalRecord:
    query: GoldenQuery
    retrieval: RetrievalScores
    generation: GenerationScores | None = None
    error: str | None = None


@dataclass
class EvalSummary:
    n_queries: int
    avg_recall_at_k: float
    avg_mrr: float
    avg_citation_precision: float
    avg_citation_recall: float
    avg_judge_score: float | None
    failures: int
    records: list[EvalRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_queries": self.n_queries,
            "failures": self.failures,
            "avg_recall_at_k": round(self.avg_recall_at_k, 4),
            "avg_mrr": round(self.avg_mrr, 4),
            "avg_citation_precision": round(self.avg_citation_precision, 4),
            "avg_citation_recall": round(self.avg_citation_recall, 4),
            "avg_judge_score": (
                round(self.avg_judge_score, 4) if self.avg_judge_score is not None else None
            ),
        }


def load_golden(path: Path) -> list[GoldenQuery]:
    """Carica golden set JSONL. Ignora righe vuote/commentate (#)."""
    out: list[GoldenQuery] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            data = json.loads(line)
            out.append(
                GoldenQuery(
                    id=str(data["id"]),
                    question=str(data["question"]),
                    expected_doc_ids=list(data.get("expected_doc_ids") or []),
                    page_type=data.get("page_type"),
                    notes=str(data.get("notes") or ""),
                )
            )
    return out


def _allowed_folders() -> set[str]:
    """Folder ammessi del pack attivo (per citation grounding)."""
    try:
        from llm_wiki.domain.registry import get_pack

        pack = get_pack()
    except Exception:
        return set()
    out: set[str] = set()
    for pt in pack.page_types:
        folder = pt.folder or pt.plural or pt.id
        if folder:
            out.add(folder)
    return out


def run_evals(
    golden_path: Path,
    *,
    top_k: int = 8,
    with_generation: bool = False,
    with_judge: bool = False,
) -> EvalSummary:
    """Esegui evals su tutto il golden set.

    Args:
        golden_path: file JSONL.
        top_k: K per ``recall@k`` / ``mrr`` (deve combaciare con il
            retrieval reale che vuoi misurare).
        with_generation: se True, esegue anche RAGAgent.answer() e
            misura citation grounding.
        with_judge: se True (richiede with_generation), aggiunge LLM-as-judge
            faithfulness. Costoso: 1 LLM call/query.
    """
    from llm_wiki.agents.rag_agent import RAGAgent
    from llm_wiki.vectorstore.core import search

    golden = load_golden(golden_path)
    if not golden:
        return EvalSummary(
            n_queries=0,
            avg_recall_at_k=0.0,
            avg_mrr=0.0,
            avg_citation_precision=0.0,
            avg_citation_recall=0.0,
            avg_judge_score=None,
            failures=0,
        )

    folders = _allowed_folders() if with_generation else set()
    records: list[EvalRecord] = []

    for q in golden:
        try:
            hits = search(q.question, limit=top_k, page_type=q.page_type)
            retrieved_ids = [str((h.get("payload") or {}).get("document_id") or "") for h in hits]
            retrieved_ids = [d for d in retrieved_ids if d]
            ret_scores = recall_at_k(retrieved_ids, q.expected_doc_ids, k=top_k)

            gen_scores: GenerationScores | None = None
            if with_generation:
                agent = RAGAgent()
                result = agent.answer(q.question, limit=top_k)
                gen_scores = citation_grounding(
                    answer=result.answer,
                    sources=result.sources,
                    allowed_folders=folders,
                )
                if with_judge:
                    gen_scores.judge_score = faithfulness_judge(
                        question=q.question, answer=result.answer, context=result.context
                    )
            records.append(EvalRecord(query=q, retrieval=ret_scores, generation=gen_scores))
        except Exception as exc:
            logger.exception("[evals] query %s failed", q.id)
            records.append(
                EvalRecord(
                    query=q,
                    retrieval=RetrievalScores(0.0, 0.0, 0, len(q.expected_doc_ids)),
                    error=str(exc),
                )
            )

    return _aggregate(records)


def _aggregate(records: list[EvalRecord]) -> EvalSummary:
    n = len(records)
    failures = sum(1 for r in records if r.error)
    valid = [r for r in records if not r.error]
    avg_recall = sum(r.retrieval.recall_at_k for r in valid) / len(valid) if valid else 0.0
    avg_mrr = sum(r.retrieval.mrr for r in valid) / len(valid) if valid else 0.0

    gen_records = [r for r in valid if r.generation is not None]
    avg_prec = (
        sum(r.generation.citation_precision for r in gen_records if r.generation) / len(gen_records)
        if gen_records
        else 0.0
    )
    avg_rec = (
        sum(r.generation.citation_recall for r in gen_records if r.generation) / len(gen_records)
        if gen_records
        else 0.0
    )
    judge_records = [
        r for r in gen_records if r.generation and r.generation.judge_score is not None
    ]
    avg_judge: float | None = None
    if judge_records:
        avg_judge = sum(
            r.generation.judge_score
            for r in judge_records
            if r.generation and r.generation.judge_score is not None
        ) / len(judge_records)

    return EvalSummary(
        n_queries=n,
        avg_recall_at_k=avg_recall,
        avg_mrr=avg_mrr,
        avg_citation_precision=avg_prec,
        avg_citation_recall=avg_rec,
        avg_judge_score=avg_judge,
        failures=failures,
        records=records,
    )

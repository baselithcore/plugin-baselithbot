"""``wiki-wl evals`` — esegui suite di valutazione retrieval/generation.

Subcomandi:

- ``run``  esegue il golden set e stampa metriche aggregate. Usa
  ``--with-generation`` per aggiungere citation grounding (richiede LLM
  attivo); ``--with-judge`` per aggiungere LLM-as-judge faithfulness
  (1 LLM call/query in più, costoso).

Esempi::

    wiki-wl evals run --golden tests/evals/golden_set.example.jsonl
    wiki-wl evals run --golden ./gold.jsonl --top-k 8 --with-generation
    wiki-wl evals run --golden ./gold.jsonl --with-generation --with-judge --json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

evals_app = typer.Typer(
    help="Eval suite per qualità RAG (retrieval + generation grounding).",
    no_args_is_help=True,
)


@evals_app.command("run")
def run(
    golden: Path = typer.Option(
        ...,
        "--golden",
        "-g",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Golden set JSONL.",
    ),
    top_k: int = typer.Option(8, "--top-k", "-k", help="K per recall@k / mrr."),
    with_generation: bool = typer.Option(
        False,
        "--with-generation",
        help="Esegui anche RAGAgent.answer() per misurare citation grounding.",
    ),
    with_judge: bool = typer.Option(
        False,
        "--with-judge",
        help="Aggiungi LLM-as-judge faithfulness (1 LLM call/query). Implica --with-generation.",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output JSON machine-readable invece del report TTY."
    ),
    show_records: bool = typer.Option(
        False, "--show-records", help="Stampa anche il dettaglio per-query nel report TTY."
    ),
) -> None:
    """Esegui golden set ed emetti report aggregato."""
    from tests.evals.runner import run_evals

    if with_judge and not with_generation:
        with_generation = True  # judge richiede answer

    summary = run_evals(
        golden,
        top_k=top_k,
        with_generation=with_generation,
        with_judge=with_judge,
    )

    if json_output:
        payload = {
            "summary": summary.to_dict(),
            "records": [
                {
                    "id": r.query.id,
                    "question": r.query.question,
                    "recall_at_k": r.retrieval.recall_at_k,
                    "mrr": r.retrieval.mrr,
                    "citation_precision": (
                        r.generation.citation_precision if r.generation else None
                    ),
                    "citation_recall": (r.generation.citation_recall if r.generation else None),
                    "judge_score": (r.generation.judge_score if r.generation else None),
                    "error": r.error,
                }
                for r in summary.records
            ],
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return

    typer.echo(f"\nGolden set: {golden} ({summary.n_queries} query)")
    typer.echo(f"Top-K: {top_k}  Failures: {summary.failures}\n")
    typer.echo("== Retrieval ==")
    typer.echo(f"  recall@{top_k}: {summary.avg_recall_at_k:.3f}")
    typer.echo(f"  MRR:        {summary.avg_mrr:.3f}")
    if with_generation:
        typer.echo("\n== Generation ==")
        typer.echo(f"  citation precision: {summary.avg_citation_precision:.3f}")
        typer.echo(f"  citation recall:    {summary.avg_citation_recall:.3f}")
        if summary.avg_judge_score is not None:
            typer.echo(f"  faithfulness judge: {summary.avg_judge_score:.3f}")

    if show_records:
        typer.echo("\n== Records ==")
        for r in summary.records:
            tag = " [ERR]" if r.error else ""
            typer.echo(
                f"  {r.query.id}{tag}: recall={r.retrieval.recall_at_k:.2f} mrr={r.retrieval.mrr:.2f}"
            )
            if r.error:
                typer.echo(f"    error: {r.error}")

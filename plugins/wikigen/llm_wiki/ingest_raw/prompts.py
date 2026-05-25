"""Domain-agnostic façade over the active pack's ingest prompts.

The reference project hardcoded prompts as Python string constants. Here
prompts live as Jinja2 templates under
``domains/<APP_DOMAIN>/prompts/ingest/`` and are rendered through the
:class:`PromptRegistry`.

The functions below mirror the reference signatures so the orchestrator,
generator and critic modules keep their call sites unchanged. Each call
returns a :class:`PromptBundle` ready to feed the LLM client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_wiki.domain.prompts import render


@dataclass
class PromptBundle:
    system: str
    user: str
    json_mode: bool = False
    json_schema: dict[str, Any] | None = None

    def as_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
        ]


# --- classify ---------------------------------------------------------------


def classify_bundle(*, metadata_hints: dict[str, Any], first_pages_md: str) -> PromptBundle:
    return PromptBundle(
        system=render("ingest/classify_system.j2"),
        user=render(
            "ingest/classify_user.j2",
            metadata_hints=metadata_hints,
            first_pages_md=first_pages_md,
        ),
        json_mode=True,
    )


# --- plan -------------------------------------------------------------------


def plan_bundle(
    *,
    classification: dict[str, Any],
    outline: str,
    existing_pages: list[str],
    body_excerpt: str = "",
    verbatim_atoms: str = "",
) -> PromptBundle:
    return PromptBundle(
        system=render("ingest/plan_system.j2"),
        user=render(
            "ingest/plan_user.j2",
            classification=classification,
            outline=outline,
            existing_pages=existing_pages,
            body_excerpt=body_excerpt,
            verbatim_atoms=verbatim_atoms,
        ),
        json_mode=True,
    )


# --- classify+plan batched --------------------------------------------------


def classify_and_plan_bundle(
    *,
    metadata_hints: dict[str, Any],
    outline: str,
    existing_pages: list[str],
    body_excerpt: str = "",
    verbatim_atoms: str = "",
) -> PromptBundle:
    """Concatena i template per pack di ``classify`` e ``plan`` in un'unica
    PromptBundle. Niente nuovi file ``.j2`` per ogni pack: il system e
    l'user sono composti a runtime dai template esistenti.

    ``body_excerpt`` (raw markdown head) e ``verbatim_atoms`` (snippets
    salienti dell'intero documento) sono passati a entrambi i template
    user: senza di essi il planner riceve solo l'outline dei heading e,
    su documenti con pochi/zero heading markdown (whitepaper, methodology
    in prosa), emette ``derived_pages: []`` perché non vede contenuto da
    decomporre.

    Tradeoff: il plan non riceve la classificazione "consolidata" come
    dict; deve dedurla nello stesso step. Il modello produce due rami
    JSON (``classification`` + ``plan``) coerenti tra loro grazie allo
    schema combinato. Risparmia 1 round-trip LLM (~30-90s su Ollama).
    """
    classify_user = render(
        "ingest/classify_user.j2",
        metadata_hints=metadata_hints,
        first_pages_md=body_excerpt or outline,
    )
    plan_user = render(
        "ingest/plan_user.j2",
        classification={"_hint": "produci tu i campi coerenti col documento"},
        outline=outline,
        existing_pages=existing_pages,
        body_excerpt=body_excerpt,
        verbatim_atoms=verbatim_atoms,
    )
    system = (
        render("ingest/classify_system.j2")
        + "\n\n---\n\n"
        + render("ingest/plan_system.j2")
        + "\n\nIMPORTANTE: produci un unico JSON con i campi `classification` e "
        "`plan` — entrambi obbligatori, coerenti tra loro."
    )
    user = (
        "## STEP 1 — CLASSIFICA IL DOCUMENTO\n\n"
        + classify_user
        + "\n\n## STEP 2 — PIANIFICA LE PAGINE WIKI\n\n"
        + "(usa la classificazione che produrrai sopra come input mentale)\n\n"
        + plan_user
    )
    return PromptBundle(system=system, user=user, json_mode=True)


# --- source page ------------------------------------------------------------


def source_page_bundle(
    *,
    plan: dict[str, Any],
    classification: dict[str, Any],
    source_path: str,
    outline: str,
    examples_blocks: list[str],
    today_iso: str,
    verbatim_atoms: str = "",
) -> PromptBundle:
    """Build the LLM bundle for a ``source`` page.

    ``verbatim_atoms`` is the deterministic dump of code fences /
    tables / callouts / CLI snippets pulled from the FULL document
    (see ``planner.extract_verbatim_atoms``). Optional for backward
    compatibility — empty string keeps the legacy outline-only
    behaviour, but callers SHOULD pass it to preserve technical
    signal that the heading outline alone discards.
    """
    return PromptBundle(
        system=render("ingest/source_page_system.j2"),
        user=render(
            "ingest/source_page_user.j2",
            plan=plan,
            classification=classification,
            source_path=source_path,
            outline=outline,
            examples_block="\n\n".join(examples_blocks) if examples_blocks else "(nessuno)",
            today_iso=today_iso,
            verbatim_atoms=verbatim_atoms,
        ),
    )


# --- garanzia / concept page ------------------------------------------------


def garanzia_page_bundle(
    *,
    plan_entry: dict[str, Any],
    source_path: str,
    section_markdown: str,
    tables_json: list[dict[str, Any]],
    examples_blocks: list[str],
    today_iso: str,
    plan_context: dict[str, Any],
) -> PromptBundle:
    return PromptBundle(
        system=render("ingest/garanzia_page_system.j2"),
        user=render(
            "ingest/garanzia_page_user.j2",
            plan_entry=plan_entry,
            plan_context=plan_context,
            source_slug=_slug_from_path(source_path),
            today_iso=today_iso,
            section_markdown=section_markdown,
            tables_json=tables_json,
            examples_block="\n\n".join(examples_blocks) if examples_blocks else "(nessuno)",
        ),
    )


# --- entity page ------------------------------------------------------------


def entity_page_bundle(
    *,
    plan_entry: dict[str, Any],
    source_path: str,
    context_snippet: str,
    today_iso: str,
    verbatim_atoms: str = "",
) -> PromptBundle:
    """Build the LLM bundle for a derived ``entity``/``concept``/``topic`` page.

    ``verbatim_atoms`` complements the keyword-windowed
    ``context_snippet`` with code/CLI/table atoms that fall outside
    the window. Backward-compatible default ``""``.
    """
    return PromptBundle(
        system=render("ingest/entity_page_system.j2"),
        user=render(
            "ingest/entity_page_user.j2",
            plan_entry=plan_entry,
            source_slug=_slug_from_path(source_path),
            today_iso=today_iso,
            context_snippet=context_snippet,
            verbatim_atoms=verbatim_atoms,
        ),
    )


# --- refine -----------------------------------------------------------------


def refine_bundle(*, current_markdown: str, lint_feedback: str) -> PromptBundle:
    return PromptBundle(
        system=render("ingest/refine_system.j2"),
        user=render(
            "ingest/refine_user.j2",
            current_markdown=current_markdown,
            lint_feedback=lint_feedback,
        ),
    )


# --- helpers ----------------------------------------------------------------


def _slug_from_path(path: str) -> str:
    """Convert ``wiki/sources/foo.md`` into the wikilink slug ``sources/foo``."""
    p = path
    if p.endswith(".md"):
        p = p[:-3]
    if p.startswith("wiki/"):
        p = p[len("wiki/") :]
    return p

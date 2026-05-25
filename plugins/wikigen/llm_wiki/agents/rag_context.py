"""Context-builder helpers per :class:`RAGAgent`.

Tre funzioni pure che serializzano in markdown il contesto LLM:

- :func:`build_context` — hits Qdrant → blocchi con header anchor-first.
- :func:`build_memories_block` — memorie utente → bullet list etichettata.
- :func:`build_history_block` — turni precedenti → dialogo.

Domain-agnostic: nessuna stringa pack-specific. Estratti da
``rag_agent.py`` per rispettare il budget 500 LOC/file.
"""

from __future__ import annotations

import re
from typing import Any

_CODE_FENCE_RE = re.compile(r"^```([^\n`]*)\n([\s\S]*?)^```", re.MULTILINE)
_CLI_TOKENS = ("kubectl ", "docker ", "terraform ", "git ", "helm ", "curl ", "npm ")

# page_type → doc_register fallback. Usato solo se il payload non porta
# già `doc_register` (chunk pre-feature o entity/concept page non passate
# dal classifier ingest). Mappa deterministica, niente LLM call.
_PAGE_TYPE_REGISTER_FALLBACK: dict[str, str] = {
    "runbook": "operational",
    "procedure": "operational",
    "procedura": "operational",
    "howto": "operational",
    "manual": "operational",
    "manuale": "operational",
    "spec": "operational",
    "api": "operational",
    "concept": "conceptual",
    "topic": "conceptual",
    "synthesis": "conceptual",
    "overview": "conceptual",
    "entity": "conceptual",
    # `source` e `case_study` restano ambigui per natura (la fonte può
    # essere sia un whitepaper che un runbook): no fallback per evitare
    # boost erroneo di registro.
}


def _infer_register_from_page_type(page_type: str | None) -> str:
    """Fallback deterministico ``page_type → register`` quando il payload
    non porta ``doc_register``. Ritorna stringa vuota se la mappa non
    matcha (segnale neutro: il modello tace, niente filler).
    """
    if not page_type:
        return ""
    return _PAGE_TYPE_REGISTER_FALLBACK.get(page_type.strip().lower(), "")


def _code_density_hint(text: str) -> str:
    """Annotate chunk with code-fence inventory so the answering LLM picks
    up the signal "snippet pertinenti presenti → quotali verbatim".

    Returns empty string when the chunk has no code/CLI signal. The
    runtime ``system.j2`` rules already constrain the model to quote
    only code that's verbatim in CONTEXT; this hint flips the default
    from "ignore unless asked" to "surface when relevant".
    """
    fences = _CODE_FENCE_RE.findall(text)
    if not fences:
        # Cheap CLI detector — bash one-liners often live inline.
        if any(tok in text for tok in _CLI_TOKENS):
            return "\nSnippet: comandi CLI presenti — riportali verbatim quando pertinenti alla domanda."
        return ""
    langs = sorted({(lang.strip() or "plain") for lang, _ in fences})
    lang_str = ", ".join(langs) if langs else "plain"
    return (
        f"\nSnippet: {len(fences)} blocco/i di codice presenti (lingue: {lang_str}). "
        "Quando rispondi a domande operative pertinenti, riproducili **verbatim** "
        "(stessa fence-lang, indentazione, placeholder)."
    )


_FOLLOW_THE_LINK_HINT = (
    "[FOLLOW-THE-LINK] Chunk recuperato via rinvio (integra come norma rinviata, "
    "non come fonte indipendente)."
)
_PARENT_SECTION_HINT = (
    "[PARENT-SECTION] Chunk fratello della stessa sezione del top hit "
    "(integra come continuazione narrativa, non come match indipendente)."
)
_HIERARCHICAL_HINT = (
    "[HIERARCHICAL] Blocco parent servito al posto del child matched "
    "(il match vettoriale ha trovato un sotto-frammento; il parent contiene "
    "il contesto narrativo completo)."
)
_GRAPH_ENTITY_HINT = (
    "[GRAPH-ENTITY] Chunk recuperato via Knowledge Graph cross-chapter "
    "(non per similarità vettoriale diretta con la query)."
)
_GRAPH_COMPARATIVE_HINT = (
    "[GRAPH-COMPARATIVE] Chunk lungo il path entità A↔entità B della "
    "domanda comparativa (ponte concettuale graphify shortest-path)."
)


def build_context(hits: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Wiki context dai hits Qdrant. Domain-agnostic — il payload viene
    propagato verbatim, frontend/pack decide quali campi rendere.

    Provenance puntuale: ogni chunk header espone `Pagina:` + `Sezione:` +
    `Cita come:` con wikilink anchored (`[[folder/slug#anchor]]`). Il modello
    è istruito da ``system.j2`` a usare quel wikilink verbatim — eliminando
    citazioni generiche tipo "[1]" / "vedi documentazione".

    Quando ``HIERARCHICAL_RETRIEVAL_ENABLED=true`` e gli hits contengono
    ``parent_id`` + ``parent_text``, i child che condividono lo stesso parent
    vengono collassati in un unico blocco con ``parent_text`` al posto del
    child_text — il LLM riceve il contesto narrativo completo della sezione.
    """
    from llm_wiki.config import HIERARCHICAL_RETRIEVAL_ENABLED

    if HIERARCHICAL_RETRIEVAL_ENABLED and hits:
        from llm_wiki.vectorstore.hierarchical import collapse_hits_by_parent

        hits = collapse_hits_by_parent(hits)

    blocks: list[str] = []
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()

    for h in hits:
        payload = h.get("payload", {}) or {}
        doc_id = payload.get("document_id", "")
        title = payload.get("title", doc_id)
        text = payload.get("text") or payload.get("raw_text") or ""
        if not text:
            continue

        header_extra = ""
        if h.get("via_rinvio"):
            rinvio_art = h.get("rinvio_articolo") or "n/d"
            header_extra = f"\n{_FOLLOW_THE_LINK_HINT} Articolo rinviato: {rinvio_art}."
        elif h.get("via_parent_section"):
            parent_h = h.get("parent_section_heading") or payload.get("section_heading") or "n/d"
            header_extra = f"\n{_PARENT_SECTION_HINT} Sezione: «{parent_h}»."
        elif h.get("hierarchical_collapsed"):
            n_children = int(h.get("merged_child_count") or 1)
            header_extra = (
                f"\n{_HIERARCHICAL_HINT} Child collassati: {n_children}."
                if n_children > 1
                else f"\n{_HIERARCHICAL_HINT}"
            )
        elif h.get("graph_expanded"):
            # Graphify principle #6: "why matched" esplicito. Tier
            # EXTRACTED/INFERRED/AMBIGUOUS preserva la trasparenza della
            # confidence cascade (no inferred-as-extracted spoofing).
            ent_name = h.get("via_graph_entity_name") or h.get("via_graph_entity") or "n/d"
            tier = h.get("via_graph_tier") or ""
            conf = h.get("via_graph_confidence")
            overlap = int(h.get("via_graph_overlap") or 0)
            if h.get("via_graph_comparative_path"):
                base_hint = _GRAPH_COMPARATIVE_HINT
            else:
                base_hint = _GRAPH_ENTITY_HINT
            parts = [f"Entità: «{ent_name}»"]
            if tier:
                parts.append(f"tier={tier}")
            if isinstance(conf, int | float) and conf > 0:
                parts.append(f"conf={float(conf):.2f}")
            if overlap >= 2:
                parts.append(f"overlap={overlap}")
            header_extra = f"\n{base_hint} " + " · ".join(parts) + "."

        section_heading = payload.get("section_heading") or ""
        section_path = payload.get("section_path") or []
        section_anchor = payload.get("section_anchor") or ""
        # Wikilink Obsidian-native: heading verbatim al click apre la
        # pagina al heading esatto. L'anchor slug è esposto come riga
        # aggiuntiva (portabile MkDocs/GH) e validato side-channel da
        # `citation_validator` quando `CITATION_ANCHOR_VALIDATION_ENABLED`.
        cite_target = f"{doc_id}#{section_heading}" if section_heading else doc_id

        section_lines = ""
        if section_path:
            breadcrumb = " > ".join(str(p) for p in section_path)
            section_lines = f"\nSezione: {breadcrumb}"
        section_lines += f"\nCita come: [[{cite_target}]]"
        if section_anchor and section_anchor != section_heading.lower():
            section_lines += f"  (anchor slug: `{section_anchor}`)"

        # Registro documentale (operational/conceptual/mixed) — signal
        # esplicito che il modello legge prima di rispondere. Iniettato a
        # ingest time, vedi `ingest_raw/register.py`. Fallback deterministico
        # da `page_type` per i chunk privi del campo (pre-feature / entity).
        from llm_wiki.ingest_raw.register import register_hint

        register_line = ""
        register_value = (payload.get("doc_register") or "").strip().lower()
        register_inferred = False
        if not register_value:
            register_value = _infer_register_from_page_type(payload.get("page_type"))
            register_inferred = bool(register_value)
        if register_value:
            hint = register_hint(register_value)
            suffix = " *(inferito da page_type)*" if register_inferred else ""
            register_line = f"\nRegistro: **{register_value}**{suffix}"
            if hint:
                register_line += f" — {hint}"

        code_line = _code_density_hint(text)
        blocks.append(
            f"### {title}\nPagina: [[{doc_id}]]{section_lines}{register_line}{code_line}\n"
            f"Score: {h.get('score', 0):.3f}{header_extra}\n\n{text}"
        )

        if doc_id not in seen:
            seen.add(doc_id)
            sources.append(
                {
                    "document_id": doc_id,
                    "title": title,
                    "score": float(h.get("score") or 0),
                    "relative_path": payload.get("relative_path"),
                    "page_type": payload.get("page_type"),
                    "subtype": payload.get("subtype"),
                    "section_heading": section_heading,
                    "section_path": list(section_path),
                    "section_anchor": section_anchor,
                    "via_rinvio": bool(h.get("via_rinvio")),
                    "article_ref": h.get("rinvio_articolo"),
                    # Provenance per click-to-source: raw file originale +
                    # numero pagine. Solo presenti per chunk derivati da
                    # source page (ingest pipeline li popola in frontmatter).
                    # Entity/concept page sintetizzate non li hanno.
                    "source_file": payload.get("source_file"),
                    "source_pages_count": payload.get("source_pages_count"),
                    "extra": {
                        k: v
                        for k, v in payload.items()
                        if k
                        not in {
                            "document_id",
                            "title",
                            "text",
                            "raw_text",
                            "relative_path",
                            "page_type",
                            "subtype",
                            "section_heading",
                            "section_path",
                            "section_anchor",
                            "source_file",
                            "source_pages_count",
                        }
                    },
                }
            )

    return "\n\n---\n\n".join(blocks), sources


def build_memories_block(memories: list[dict[str, Any]]) -> str:
    """Serializza memorie utente in markdown digeribile dal LLM.

    Header esplicito ``### Memoria personale dell'utente`` per evitare
    confusione con la wiki — il modello deve capire che sono fatti
    dichiarati dall'utente, non sorgenti autoritative.
    """
    if not memories:
        return ""
    lines = ["### Memoria personale dell'utente"]
    for m in memories:
        kind = m.get("kind", "note")
        key = m.get("key")
        value = (m.get("value") or "").strip()
        sim = m.get("similarity")
        prefix = f"[{kind}"
        if key:
            prefix += f":{key}"
        prefix += "]"
        sim_part = f" (sim={sim:.2f})" if isinstance(sim, int | float) else ""
        lines.append(f"- {prefix}{sim_part} {value}")
    return "\n".join(lines)


def build_history_block(turns: list[dict[str, Any]]) -> str:
    """Serializza turni precedenti come dialog. Usato come var
    ``history`` dal template ``user.j2``.

    Per-turn truncation governata da ``RAG_HISTORY_TURN_MAX_CHARS``
    (env, default 800). Difende il context window in chat lunghe."""
    if not turns:
        return ""
    from llm_wiki.config import RAG_HISTORY_TURN_MAX_CHARS

    max_chars = RAG_HISTORY_TURN_MAX_CHARS
    lines = ["### Conversazione precedente"]
    for t in turns:
        role = t.get("role", "user").capitalize()
        content = (t.get("content") or "").strip()
        if not content:
            continue
        if len(content) > max_chars:
            content = content[: max_chars - 1].rstrip() + "…"
        lines.append(f"**{role}**: {content}")
    return "\n\n".join(lines)


__all__ = [
    "build_context",
    "build_history_block",
    "build_memories_block",
]

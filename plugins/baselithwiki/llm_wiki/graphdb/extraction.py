"""Entity + relation extraction from wiki pages (graphify-inspired).

Single LLM call per page, JSON-schema-constrained. Output is normalized
into typed records and pushed to :class:`KnowledgeGraphStore`. Confidence
scores map to graphify 3-tier system (EXTRACTED / INFERRED / AMBIGUOUS).

Design
------
- Prompt sourced from the active Domain Pack:
  ``<pack>/prompts/graph/extract.j2``. If missing, falls back to a built-in
  baseline that uses the pack's :class:`GraphSpec` to enumerate vocabulary.
  This keeps engine functional even for packs that haven't authored the
  template yet.
- Extraction is **best-effort**: failures are logged + swallowed. The wiki
  page write succeeds even if the graph layer is unavailable or the LLM
  errors out. Graph layer is enrichment, not a hard dependency.
- Re-extraction is idempotent: store.delete_page_extractions(page_id) wipes
  prior MENTIONS / DEFINED_IN / page-attributed relations before re-writing.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field

from llm_wiki import config as _config
from llm_wiki.config import GRAPH_EXTRACT_ENABLED
from llm_wiki.domain.pack import DomainPack, GraphSpec
from llm_wiki.domain.prompts import PromptNotFoundError, PromptRegistry
from llm_wiki.graphdb.store import KnowledgeGraphStore, canonical_entity_id

logger = logging.getLogger(__name__)

# Hard cap: pages > N chars are truncated before prompting. Saves tokens +
# avoids context overflow on Ollama with default num_ctx. Most wiki pages
# fit easily; the truncated tail is rare and the LLM still sees the head.
_MAX_PAGE_CHARS = 8000

# Cap entities/relations per extraction. Prevents pathological pages from
# blowing up the graph (saw ~120 fake entities on a 50-page PDF dump).
_MAX_ENTITIES = 30
_MAX_RELATIONS = 60


class ExtractedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    kind: str = Field(..., min_length=1)
    aliases: list[str] = Field(default_factory=list, max_length=10)
    # ``confidence`` opzionale per tolleranza con modelli small (qwen 7b,
    # llama3 8b) che spesso omettono il campo. Default 0.6 = INFERRED tier:
    # entità mantenuta ma flaggata come "implicita" dal RAG. Modelli grandi
    # (gpt-oss:20b, GPT-4o) emettono sempre confidence → default mai usato.
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class ExtractedRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    src: str = Field(
        ...,
        min_length=1,
        description="Entity name (must match an entity in this batch).",
    )
    dst: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    # Stesso trattamento di ExtractedEntity.confidence: opzionale con
    # fallback INFERRED-tier per tolleranza su modelli small.
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    evidence: str = Field(default="", max_length=400)


class ExtractionPayload(BaseModel):
    """Output schema fed to ``generate_structured()`` as JSON-schema."""

    model_config = ConfigDict(extra="forbid")

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)


def _resolve_model() -> str:
    """Pick model for graph extraction. Explicit GRAPH_EXTRACT_MODEL wins,
    else fall back to the ingest model. Keeps a single warm Ollama model
    by default — no extra cold-load cost.
    """
    if _config.GRAPH_EXTRACT_MODEL:
        return _config.GRAPH_EXTRACT_MODEL
    return (
        _config.INGEST_OPENAI_MODEL
        if _config.INGEST_VENDOR == "openai"
        else _config.INGEST_OLLAMA_MODEL
    )


def _baseline_prompt(spec: GraphSpec, *, page_title: str, page_body: str) -> str:
    """Inline fallback prompt when pack lacks ``prompts/graph/extract.j2``.

    Italian — engine default language for all packs. Uses the pack's
    GraphSpec to enumerate vocab.
    """
    et_lines = "\n".join(
        f"- `{e.id}` ({e.label}): {e.description or ''} "
        f"esempi: {', '.join(e.examples) if e.examples else 'n/a'}"
        for e in spec.entity_types
    )
    rt_lines = "\n".join(
        f"- `{r.id}` ({r.label}): {r.description or ''}" for r in spec.relation_types
    )
    hints = (
        f"\n\nGuida specifica:\n{spec.extraction_hints}"
        if spec.extraction_hints
        else ""
    )
    return (
        "Sei un estrattore di knowledge graph. Analizza la pagina wiki e produci "
        "entità e relazioni in JSON conforme allo schema.\n\n"
        "**Tipi di entità ammessi** (campo `kind`):\n"
        f"{et_lines}\n\n"
        "**Tipi di relazione ammessi** (campo `kind`, MAIUSCOLO):\n"
        f"{rt_lines}\n\n"
        "Regole:\n"
        "1. `confidence` ∈ [0,1]. Usa ≥0.85 quando la pagina afferma esplicitamente "
        "il fatto; 0.5–0.85 quando è implicito ma supportato; <0.5 solo se davvero "
        "ambiguo (sarà filtrato dal RAG).\n"
        "2. Le `relations.src` e `relations.dst` DEVONO essere `name` di entità "
        "presenti in `entities`. Niente entità fantasma.\n"
        "3. `evidence` è una citazione letterale ≤400 caratteri dalla pagina che "
        "giustifica la relazione (lascia vuoto solo se davvero non c'è).\n"
        f"4. Massimo {_MAX_ENTITIES} entità, {_MAX_RELATIONS} relazioni.\n"
        "5. Non inventare. Se la pagina è povera di contenuto strutturato, "
        "restituisci liste vuote — meglio nulla che rumore."
        f"{hints}\n\n"
        f"=== PAGINA: {page_title} ===\n"
        f"{page_body[:_MAX_PAGE_CHARS]}\n"
        "=== FINE PAGINA ===\n\n"
        "Rispondi SOLO con JSON valido conforme allo schema."
    )


def _render_prompt(
    pack: DomainPack,
    registry: PromptRegistry | None,
    *,
    page_title: str,
    page_body: str,
) -> str:
    """Try the pack's template, fall back to baseline."""
    if registry is not None:
        try:
            return registry.render(
                "graph/extract.j2",
                graph_spec=pack.graph,
                page_title=page_title,
                page_body=page_body[:_MAX_PAGE_CHARS],
            )
        except PromptNotFoundError:
            logger.debug(
                "[graph.extract] pack %s lacks prompts/graph/extract.j2; using baseline",
                pack.name,
            )
    return _baseline_prompt(pack.graph, page_title=page_title, page_body=page_body)


def _validate_against_spec(
    payload: ExtractionPayload, spec: GraphSpec
) -> ExtractionPayload:
    """Drop entities/relations whose ``kind`` is not in the pack spec.

    The LLM may hallucinate kinds despite the prompt; we coerce to the
    declared vocabulary instead of trusting it blindly. Logged at debug.
    """
    entity_kinds = {e.id for e in spec.entity_types}
    relation_kinds = {r.id for r in spec.relation_types}

    # If pack omitted the spec entirely, default ontology is used by
    # DomainPack default_factory — entity_kinds is non-empty.
    if not entity_kinds:
        return payload

    valid_entities: list[ExtractedEntity] = []
    valid_names: set[str] = set()
    for e in payload.entities[:_MAX_ENTITIES]:
        kind_norm = e.kind.strip().lower()
        if kind_norm not in entity_kinds:
            logger.debug(
                "[graph.extract] dropping entity kind=%s name=%s", e.kind, e.name
            )
            continue
        valid_entities.append(
            ExtractedEntity(
                name=e.name.strip(),
                kind=kind_norm,
                aliases=[a.strip() for a in e.aliases if a.strip()],
                confidence=e.confidence,
            )
        )
        valid_names.add(e.name.strip().lower())

    valid_relations: list[ExtractedRelation] = []
    for r in payload.relations[:_MAX_RELATIONS]:
        kind_norm = r.kind.strip().upper()
        if relation_kinds and kind_norm not in relation_kinds:
            logger.debug("[graph.extract] dropping relation kind=%s", r.kind)
            continue
        if (
            r.src.strip().lower() not in valid_names
            or r.dst.strip().lower() not in valid_names
        ):
            logger.debug(
                "[graph.extract] dropping phantom relation src=%s dst=%s", r.src, r.dst
            )
            continue
        valid_relations.append(
            ExtractedRelation(
                src=r.src.strip(),
                dst=r.dst.strip(),
                kind=kind_norm,
                confidence=r.confidence,
                evidence=r.evidence.strip(),
            )
        )

    return ExtractionPayload(entities=valid_entities, relations=valid_relations)


def extract_payload_from_page(
    *,
    page_title: str,
    page_body: str,
    pack: DomainPack,
    registry: PromptRegistry | None,
) -> ExtractionPayload:
    """Run the LLM extraction + spec validation for one page WITHOUT
    touching the store. The expensive part (single ``generate_structured``
    LLM call) is pure w.r.t. the graph DB, so this is safe to fan out across
    worker threads. Persist the returned payload on a single thread via
    :func:`persist_extraction` to avoid concurrent MERGE races.

    Best-effort: any LLM failure returns an empty payload.
    """
    if not GRAPH_EXTRACT_ENABLED:
        return ExtractionPayload()
    if not page_body or not page_body.strip():
        return ExtractionPayload()

    # Lazy import: keep CLI cold-start light (ingest_raw pulls openai/ollama).
    from llm_wiki.ingest_raw.llm_client import generate_structured

    prompt = _render_prompt(pack, registry, page_title=page_title, page_body=page_body)
    messages = [
        {
            "role": "system",
            "content": "Estrai knowledge graph dalla pagina wiki. JSON only.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        raw = generate_structured(
            ExtractionPayload,
            messages=messages,
            model=_resolve_model(),
            max_retries=2,
            temperature=0.05,
        )
    except Exception as exc:
        logger.warning("[graph.extract] LLM call failed: %s", exc)
        return ExtractionPayload()

    return _validate_against_spec(raw, pack.graph)


def persist_extraction(
    payload: ExtractionPayload,
    *,
    page_id: str,
    page_type: str,
    store: KnowledgeGraphStore,
) -> None:
    """Persist a validated payload to the KG store. Mutates shared graph
    state via MERGE — call SERIALLY, never from concurrent threads."""
    if not store.enabled:
        return
    _persist(payload, page_id=page_id, page_type=page_type, store=store)


def extract_from_page(
    *,
    page_id: str,
    page_title: str,
    page_body: str,
    page_type: str,
    pack: DomainPack,
    registry: PromptRegistry | None,
    store: KnowledgeGraphStore,
) -> ExtractionPayload:
    """Run extraction, normalize, push to store. Returns the validated
    payload (useful for callers that want to log counts).

    Equivalent to :func:`extract_payload_from_page` followed by
    :func:`persist_extraction` — kept as the single-call entry point.
    Best-effort: any exception is logged and an empty payload is returned.
    """
    if not GRAPH_EXTRACT_ENABLED:
        return ExtractionPayload()
    if not store.enabled:
        return ExtractionPayload()

    validated = extract_payload_from_page(
        page_title=page_title, page_body=page_body, pack=pack, registry=registry
    )
    persist_extraction(validated, page_id=page_id, page_type=page_type, store=store)
    logger.info(
        "[graph.extract] page=%s entities=%d relations=%d",
        page_id,
        len(validated.entities),
        len(validated.relations),
    )
    return validated


def _persist(
    payload: ExtractionPayload,
    *,
    page_id: str,
    page_type: str,
    store: KnowledgeGraphStore,
) -> None:
    """Wipe previous extractions for this page, then upsert fresh nodes
    and edges. Each MENTIONS edge inherits the entity's confidence — when
    the page is an entity_page (canonical), also writes DEFINED_IN.
    """
    if not store.enabled:
        return
    store.delete_page_extractions(page_id)

    name_to_id: dict[str, str] = {}
    is_canonical_page = page_type in {"concept", "entity", "topic"}

    for ent in payload.entities:
        eid = store.upsert_entity(ent.name, ent.kind, aliases=ent.aliases)
        name_to_id[ent.name.lower()] = eid
        store.link_mention(
            page_id,
            eid,
            confidence=ent.confidence,
            canonical=is_canonical_page,
        )

    for rel in payload.relations:
        src_id = name_to_id.get(rel.src.lower())
        dst_id = name_to_id.get(rel.dst.lower())
        if not src_id or not dst_id:
            # Defensive: _validate_against_spec already filters, but the
            # name lowercasing could theoretically miss a unicode edge case.
            continue
        store.upsert_relation(
            src_id,
            dst_id,
            rel.kind,
            confidence=rel.confidence,
            evidence=rel.evidence,
            page_id=page_id,
        )


__all__ = [
    "ExtractedEntity",
    "ExtractedRelation",
    "ExtractionPayload",
    "extract_from_page",
    "extract_payload_from_page",
    "persist_extraction",
]


# Reference unused import to avoid Pyright noise — canonical_entity_id is
# part of the module's public dependency surface (callers of extract may
# inspect entity ids derived the same way).
_ = canonical_entity_id

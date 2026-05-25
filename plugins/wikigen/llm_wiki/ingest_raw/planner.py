"""Planner: classify document + propose page list.

Two phases driven by the active Domain Pack:

1. :func:`classify_document` — LLM classifies the source. The accepted
   ``source_type`` enum is built from ``pack.subtypes['source']`` so the
   model is constrained to the current vertical.
2. :func:`plan_document` — given classification + extracted outline,
   produces an :class:`IngestPlan` whose ``page_type`` enum is built from
   ``pack.page_types``.

Best practice applied: outline is condensed deterministically before
hitting the LLM (regex over headings) so the model works on already-shrunk
input.
"""

from __future__ import annotations

import logging
import re
from datetime import date as Date
from pathlib import Path

from llm_wiki import config as _config
from llm_wiki.config import WIKI_DIR
from llm_wiki.domain.registry import get_pack
from llm_wiki.ingest_raw.extractor import ExtractedDocument
from llm_wiki.ingest_raw.llm_client import generate_structured
from llm_wiki.ingest_raw.prompts import (
    classify_and_plan_bundle,
    classify_bundle,
    plan_bundle,
)
from llm_wiki.ingest_raw.schemas import (
    Classification,
    IngestPlan,
    build_classification_schema,
    build_classify_and_plan_schema,
    build_plan_schema,
)

logger = logging.getLogger(__name__)


def classify_document(doc: ExtractedDocument, *, model: str | None = None) -> Classification:
    """Classify the source document using the active pack's subtype enum."""
    pack = get_pack()
    schema = build_classification_schema(pack)
    bundle = classify_bundle(metadata_hints=doc.metadata, first_pages_md=doc.markdown[:3500])
    cls = generate_structured(schema, messages=bundle.as_messages(), model=model)
    logger.info("classify: %s | ed=%s | modello=%s", cls.source_type, cls.edizione, cls.modello)
    return cls


def plan_document(
    doc: ExtractedDocument,
    classification: Classification,
    *,
    model: str | None = None,
) -> IngestPlan:
    """Propose an :class:`IngestPlan` constrained to the pack's page types."""
    pack = get_pack()
    schema = build_plan_schema(pack)
    outline = extract_outline(doc.markdown)
    body_excerpt = doc.markdown[:5000]
    atoms = extract_verbatim_atoms(doc.markdown)
    bundle = plan_bundle(
        classification=classification.model_dump(mode="json"),
        outline=outline,
        existing_pages=_list_existing_pages(),
        body_excerpt=body_excerpt,
        verbatim_atoms=atoms,
    )
    plan = generate_structured(schema, messages=bundle.as_messages(), model=model)
    plan = _normalize_plan(plan, source_path=str(doc.source_path), classification=classification)
    plan = _cap_derived_pages(plan, doc=doc)
    plan.source_pages_count = doc.n_pages
    logger.info(
        "plan: source=%s, derived=%d pages",
        plan.source_page.target_path,
        len(plan.derived_pages),
    )
    return plan


def classify_and_plan_document(
    doc: ExtractedDocument,
    *,
    model: str | None = None,
) -> tuple[Classification, IngestPlan]:
    """Versione batched: classify + plan in una sola call LLM.

    Risparmia 1 round-trip rispetto a ``classify_document`` +
    ``plan_document`` (~30-90s su Ollama, ~3-8s su OpenAI). Lo schema
    combinato vincola entrambi i rami con gli enum del pack.

    Tradeoff: prompt più lungo (single-shot vede outline + esempi
    classificazione + lista esistenti tutti insieme). Su modelli piccoli
    o context window stretti la qualità del plan può degradare; gating
    via ``INGEST_BATCH_CLASSIFY_PLAN`` permette opt-in selettivo.
    """
    pack = get_pack()
    schema = build_classify_and_plan_schema(pack)
    outline = extract_outline(doc.markdown)
    body_excerpt = doc.markdown[:5000]
    atoms = extract_verbatim_atoms(doc.markdown)
    bundle = classify_and_plan_bundle(
        metadata_hints=doc.metadata,
        outline=outline,
        existing_pages=_list_existing_pages(),
        body_excerpt=body_excerpt,
        verbatim_atoms=atoms,
    )
    out = generate_structured(schema, messages=bundle.as_messages(), model=model)
    cls, plan = out.classification, out.plan
    logger.info(
        "classify+plan: source_type=%s, derived=%d pages",
        cls.source_type,
        len(plan.derived_pages),
    )
    plan = _normalize_plan(plan, source_path=str(doc.source_path), classification=cls)
    plan = _cap_derived_pages(plan, doc=doc)
    plan.source_pages_count = doc.n_pages
    return cls, plan


def _cap_derived_pages(plan: IngestPlan, *, doc: ExtractedDocument) -> IngestPlan:
    pages = max(1, doc.n_pages)
    tables = len(doc.tables)
    cap = max(5, pages * 3 + tables * 2)
    if len(plan.derived_pages) > cap:
        logger.warning(
            "plan: capping derived_pages %d → %d (PDF pages=%d tables=%d)",
            len(plan.derived_pages),
            cap,
            pages,
            tables,
        )
        plan.derived_pages = plan.derived_pages[:cap]
    return plan


_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)


def extract_outline(markdown: str, *, max_chars: int = 6000) -> str:
    out: list[str] = []
    for m in _HEADING_RE.finditer(markdown):
        level = len(m.group(1))
        title = m.group(2).strip()
        out.append(f"{'#' * level} {title}")
        if sum(len(x) for x in out) > max_chars:
            break
    return "\n".join(out)


# Pattern di atomi verbatim. Estratti deterministicamente dall'intero
# markdown (NON solo dai primi N char) e iniettati nel prompt di
# generazione source/entity. Senza questo passo, l'LLM riceve solo
# l'outline dei heading e perde silenziosamente code fence, comandi
# CLI, snippet di configurazione, payload JSON/YAML, tabelle —
# materiale che su pack tecnici È il valore alto-livello del documento.
_FENCE_RE = re.compile(r"^```([^\n`]*)\n([\s\S]*?)^```", re.MULTILINE)
_TABLE_RE = re.compile(
    r"(?:^\|[^\n]*\|\s*\n)(?:^\|[\s\-:|]+\|\s*\n)(?:^\|[^\n]*\|\s*\n?)+",
    re.MULTILINE,
)
_CALLOUT_RE = re.compile(
    r"(?:^>\s*\[![A-Za-z]+\][^\n]*\n)(?:^>[^\n]*\n?)*",
    re.MULTILINE,
)
_CLI_LINE_RE = re.compile(
    # ``$`` (bash/zsh prompt) or ``PS C:\>`` (PowerShell prompt). Markdown
    # blockquote ``> ...`` is intentionally excluded — it collides with
    # admonition callouts and ordinary quoted prose, producing false
    # positives that pollute the verbatim digest with non-CLI material.
    r"^(?:\$\s+|PS\s+\S+>\s*)\S[^\n]*$",
    re.MULTILINE,
)
_CLI_TOKENS = (
    "kubectl ",
    "docker ",
    "terraform ",
    "git ",
    "helm ",
    "ansible ",
    "aws ",
    "gcloud ",
    "az ",
    "psql ",
    "curl ",
    "npm ",
    "yarn ",
    "pip ",
    "uv ",
    "make ",
    "systemctl ",
    "journalctl ",
    "ssh ",
    "rsync ",
)

# Multilingual step / phase markers. Catches procedural structure that lives
# in narrative prose (NOT in heading levels and NOT in code fences) — the
# typical pattern of whitepapers, methodologies, runbook-as-prose docs:
# "Fase 1: Criteri di valutazione" or "**Phase 2: Pilot**". Without this
# atom kind the planner's outline (headings only) and the verbatim atoms
# (code/CLI/tables) miss the document's actionable structure entirely.
#
# Domain-agnostic: tokens cover IT/EN/ES/FR/DE/NL. Keep the list short and
# obvious — false positives are tolerable (a stray "Phase 3" sentence
# fragment quoted verbatim is far cheaper than losing the whole section).
_STEP_MARKER_RE = re.compile(
    r"^[\s>*_-]*\**\s*"  # optional list/quote/bold prefix
    r"(?:Fase|Phase|Step|Stage|Stadio|Étape|Etape|Etapa|Paso|Stap|Schritt|Stufe)\b"
    r"\s*\d+",
    re.MULTILINE | re.IGNORECASE,
)

# Ordered list block: ≥3 consecutive numbered items at the start of their
# line. Captures procedural enumerations the LLM otherwise reorders or
# truncates ("ecco i passaggi: 1. … 2. … 3. … 4. …" → kept verbatim).
_ORDERED_LIST_RE = re.compile(
    r"(?:^[ \t]*\d{1,2}\.\s+\S[^\n]*\n){3,}",
    re.MULTILINE,
)


def _extract_step_blocks(markdown: str, *, per_block_cap: int = 1200) -> list[tuple[int, str]]:
    """Return ``(start_offset, block_text)`` for each multilingual step
    marker found in ``markdown``.

    A block starts at the marker line and ends at the earliest of:
    next step-marker line, next markdown heading, two consecutive blank
    lines, ``per_block_cap`` chars. Trailing whitespace stripped.
    """
    starts = [m.start() for m in _STEP_MARKER_RE.finditer(markdown)]
    if not starts:
        return []
    blocks: list[tuple[int, str]] = []
    n = len(markdown)
    for i, start in enumerate(starts):
        hard_stop = starts[i + 1] if i + 1 < len(starts) else n
        # Walk forward looking for soft boundaries.
        end = min(hard_stop, start + per_block_cap)
        cursor = start
        blank_run = 0
        while cursor < end:
            line_end = markdown.find("\n", cursor)
            if line_end == -1:
                line_end = n
            line = markdown[cursor:line_end]
            stripped = line.strip()
            if cursor > start and stripped.startswith("#"):
                end = cursor
                break
            if not stripped:
                blank_run += 1
                if blank_run >= 2:
                    end = cursor
                    break
            else:
                blank_run = 0
            cursor = line_end + 1
        text = markdown[start:end].rstrip()
        if text:
            blocks.append((start, text))
    return blocks


def extract_verbatim_atoms(markdown: str, *, max_chars: int | None = None) -> str:
    """Estrai atomi verbatim (code fence, tabelle, callout, CLI, fasi
    procedurali, liste ordinate) preservando l'ordine.

    Necessario perché ``extract_outline`` espone solo i heading: la
    pipeline di ingest passa quell'outline al generatore source-page,
    quindi il LLM non vede MAI il corpo del documento e inventa o
    omette snippet/comandi/config/fasi. Questo helper integra l'outline
    con gli atomi salienti, preservandoli interi (mai troncare a metà
    fence) fino al budget ``max_chars``.

    Atom kinds (priority by source order):

    - ``code`` — fenced code blocks (language tag preserved)
    - ``table`` — markdown pipe tables
    - ``callout`` — Obsidian admonition callouts (``> [!warning] …``)
    - ``cli`` — shell prompt lines + recognized CLI verbs
    - ``step`` — multilingual step/phase markers ("Fase 1: …",
      "Phase 2: …") with their following paragraph until the next
      marker / heading / blank-line boundary. Catches the macro-
      operational structure of whitepapers and methodologies that
      live in narrative prose, not in heading levels.
    - ``ordered_list`` — runs of ≥3 numbered items at line start.

    Budget defaults to ``INGEST_VERBATIM_MAX_CHARS`` (env, default 6000).
    Ordering: stabile per posizione nel sorgente — preserva contesto
    narrativo tra atomi vicini. Dedup: skip atomi identici (frequente
    in PDF estratti con OCR ripetuto). Selezione: priorità a interi
    atomi entro budget; un atomo che ecceda da solo il budget viene
    incluso troncato con marker ``...[truncated]``.
    """
    if max_chars is None:
        budget = int(getattr(_config, "INGEST_VERBATIM_MAX_CHARS", 6000))
    else:
        budget = int(max_chars)
    if not markdown or budget <= 0:
        return ""

    spans: list[tuple[int, str, str]] = []  # (start_offset, kind, text)

    for m in _FENCE_RE.finditer(markdown):
        spans.append((m.start(), "code", m.group(0)))
    for m in _TABLE_RE.finditer(markdown):
        spans.append((m.start(), "table", m.group(0).rstrip()))
    for m in _CALLOUT_RE.finditer(markdown):
        spans.append((m.start(), "callout", m.group(0).rstrip()))
    for m in _CLI_LINE_RE.finditer(markdown):
        spans.append((m.start(), "cli", m.group(0)))
    for token in _CLI_TOKENS:
        for m in re.finditer(rf"^[^\n#`>|]*{re.escape(token)}[^\n]+$", markdown, re.MULTILINE):
            spans.append((m.start(), "cli", m.group(0).strip()))
    for start, text in _extract_step_blocks(markdown):
        spans.append((start, "step", text))
    for m in _ORDERED_LIST_RE.finditer(markdown):
        spans.append((m.start(), "ordered_list", m.group(0).rstrip()))

    if not spans:
        return ""

    spans.sort(key=lambda s: s[0])

    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for _, kind, text in spans:
        key = text.strip()
        if not key or key in seen:
            continue
        # CLI lines often appear *inside* code fences or callout blocks
        # because the regex above runs over the full markdown without
        # awareness of block context. Skip a CLI atom when its text is
        # already contained within a previously kept code/callout atom —
        # those provide richer framing for the same instruction.
        if kind == "cli" and any(key in t for k, t in deduped if k in {"code", "callout"}):
            continue
        seen.add(key)
        deduped.append((kind, text))

    out: list[str] = []
    used = 0
    for kind, text in deduped:
        block = f"<!-- atom:{kind} -->\n{text}"
        if used + len(block) + 2 > budget:
            if not out:
                truncated = block[: budget - len("\n...[truncated]")]
                out.append(truncated + "\n...[truncated]")
            break
        out.append(block)
        used += len(block) + 2

    return "\n\n".join(out)


_EXISTING_PAGES_CAP = 200
_existing_pages_cache: list[str] | None = None


def reset_existing_pages_cache() -> None:
    """Invalidare cache dopo write di nuove pagine. Chiamata da orchestrator."""
    global _existing_pages_cache
    _existing_pages_cache = None


def _list_existing_pages() -> list[str]:
    """Restituisce fino a ``_EXISTING_PAGES_CAP`` pagine, le più recenti per primo.

    Su vault grandi (500+ pagine) la lista intera occupa ~25KB del prompt
    di plan, dilatando la latenza LLM senza migliorare la qualità: il
    planner usa questa lista solo per evitare duplicati di nomi, e i
    duplicati nascono tipicamente da ingest recenti dello stesso autore o
    edizione. Le pagine più vecchie raramente competono.

    Cache process-lifetime con invalidate esplicito (vedi
    ``reset_existing_pages_cache``): rglob+stat su WIKI_DIR cumulativo
    cresce con la grandezza del vault e veniva ripetuto a ogni ingest
    nel wizard multi-PDF. Invalidazione mirata da orchestrator dopo
    ogni write evita stallo a dati obsoleti.
    """
    global _existing_pages_cache
    if _existing_pages_cache is not None:
        return _existing_pages_cache
    if not WIKI_DIR.exists():
        _existing_pages_cache = []
        return _existing_pages_cache
    paths = list(WIKI_DIR.rglob("*.md"))
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    _existing_pages_cache = [
        p.relative_to(WIKI_DIR.parent).as_posix() for p in paths[:_EXISTING_PAGES_CAP]
    ]
    return _existing_pages_cache


def _normalize_plan(
    plan: IngestPlan, *, source_path: str, classification: Classification
) -> IngestPlan:
    """Post-LLM enforcement: anchor source slug to filename, kebabise paths."""
    pack = get_pack()
    sources_pt = pack.page_type("source")
    sources_folder = (sources_pt.folder if sources_pt else None) or "sources"

    # Iniezione deterministica: il LLM non conosce il path del PDF, lo
    # sappiamo qui. Senza questo step il frontmatter source_file resta
    # vuoto e il linter solleva ERROR.
    if not plan.source_file:
        plan.source_file = source_path

    slug = slug_from_raw(source_path)
    plan.source_page.target_path = f"wiki/{sources_folder}/{slug}.md"

    if plan.edizione is None and classification.edizione:
        plan.edizione = classification.edizione
    if plan.edizione_iso is None and classification.edizione_iso:
        plan.edizione_iso = classification.edizione_iso
    if not plan.source_type and classification.source_type:
        plan.source_type = classification.source_type

    for p in plan.derived_pages:
        if not p.target_path.startswith("wiki/"):
            p.target_path = f"wiki/{p.target_path.lstrip('/')}"
        # Force the folder to the pack-declared folder for `page_type`. The
        # `page_type` field is JSON-Schema-constrained against the pack
        # enum, but `target_path` is a free string — the LLM happily
        # invents intuitive folder names from PDF content (CV → `people/`,
        # `companies/`, `roles/`) which scatters pages outside the
        # scaffolded taxonomy. Pin the folder here so the vault layout
        # matches `pack.page_types`.
        pt = pack.page_type(p.page_type)
        if pt and pt.folder:
            parts = p.target_path.split("/")
            basename = parts[-1] if parts else ""
            p.target_path = f"wiki/{pt.folder}/{basename}"
        p.target_path = _kebabize_path(p.target_path)
    plan.source_page.target_path = _kebabize_path(plan.source_page.target_path)
    return plan


def slug_from_raw(raw_path: str) -> str:
    """Normalize raw filename → URL-safe slug.

    Trailing-dash trap: a previous version applied ``.strip("-")`` BEFORE
    the 80-char truncation, so an 81-char input ending in ``-N`` re-
    introduced a dangling dash after the slice. That stale dash broke
    equality checks against source-page slugs (the planner truncates +
    re-strips so its slugs are always dash-free). Order matters: cap
    first, then re-strip — idempotent + slice-safe.
    """
    stem = Path(raw_path).stem.lower()
    stem = re.sub(r"[+_\s]+", "-", stem)
    stem = re.sub(r"[^a-z0-9\-]+", "", stem)
    stem = re.sub(r"-+", "-", stem).strip("-")
    return stem[:80].strip("-") or "source"


def _kebabize_path(path: str) -> str:
    parts = path.split("/")
    if not parts[-1].endswith(".md"):
        parts[-1] = parts[-1] + ".md"
    stem = parts[-1][:-3]
    stem = re.sub(r"[+_\s]+", "-", stem.lower())
    stem = re.sub(r"[^a-z0-9\-/]+", "", stem)
    stem = re.sub(r"-+", "-", stem).strip("-")
    parts[-1] = f"{stem}.md"
    return "/".join(parts)


_ = Date  # keep typing import silenced

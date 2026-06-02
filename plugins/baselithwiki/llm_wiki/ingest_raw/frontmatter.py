"""Iniezione/repair frontmatter + stub sezioni obbligatorie.

Estratto da ``orchestrator.py`` per rispettare il budget 500 LOC. Logica
puramente deterministica: nessun LLM, nessun I/O di rete.

Use cases:

- Inietta frontmatter mancante o ripara campi obbligatori (``type``,
  ``source_file``, ``ingested``, ``source_hash``) usando default derivati
  dall'``IngestPlan``. Evita round-trip LLM al critic per fix triviali.
- Aggiunge stub a sezioni obbligatorie del page-type (vedi
  ``SEZIONI_SOURCE`` / ``SEZIONI_GARANZIA``); pre-popola ``## Fonti`` con
  wikilink alla source page così il check ``citations.fonti.empty`` non
  alza ERROR.

I pack possono customizzare i default frontmatter via hook
``frontmatter_defaults`` nel modulo ``domains/<pack>/strategies.py``.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-not-found]

from llm_wiki.domain.registry import get_pack
from llm_wiki.ingest_raw.lint_constants import SEZIONI_GARANZIA, SEZIONI_SOURCE
from llm_wiki.ingest_raw.register import infer_doc_register
from llm_wiki.ingest_raw.schemas import IngestPlan, PagePlan

logger = logging.getLogger(__name__)


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_OPEN_FENCE_RE = re.compile(r"^```(?:markdown|md)\s*$")
_CLOSE_FENCE_RE = re.compile(r"^```\s*$")


def strip_markdown_wrapper(md: str) -> str:
    """Drop an outer ```markdown … ``` fence wrapping the whole page.

    Some LLMs return the page body inside a ``markdown`` code fence
    despite the prompt asking for raw markdown. Walk lines so nested
    code fences (``sh``, ``json``, …) survive intact.
    """
    lines = md.split("\n")
    start = 0
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    if start >= len(lines) or not _OPEN_FENCE_RE.match(lines[start].strip()):
        return md
    end = len(lines) - 1
    while end > start and not _CLOSE_FENCE_RE.match(lines[end].strip()):
        end -= 1
    if end <= start:
        return md
    head = lines[:start]
    inner = lines[start + 1 : end]
    tail = lines[end + 1 :]
    return "\n".join(head + inner + tail)


def slug_from_target(target_path: str) -> str:
    """Slug interno: rimuove ``wiki/`` prefix e ``.md`` suffix."""
    p = target_path
    if p.endswith(".md"):
        p = p[:-3]
    if p.startswith("wiki/"):
        p = p[len("wiki/") :]
    return p


def ensure_frontmatter(
    md: str,
    *,
    entry: PagePlan,
    plan: IngestPlan,
    today: date | None,
    source_hash: str | None = None,
) -> str:
    """Inietta o ripara il blocco frontmatter usando i default del pack.

    LLM locali (llama3.1:8b su prompt lunghi) talvolta omettono il blocco
    ``---`` o mancano campi obbligatori. Li ripristiniamo deterministicamente
    dal frontmatter schema del pack — non distruttivo: i campi prodotti
    correttamente dal modello vengono preservati.
    """
    today_iso = (today or date.today()).isoformat()
    defaults = frontmatter_defaults(
        entry=entry, plan=plan, today_iso=today_iso, source_hash=source_hash
    )

    m = _FRONTMATTER_RE.match(md)
    if not m:
        return render_frontmatter(defaults) + md.lstrip("\n")

    try:
        parsed = yaml.safe_load(m.group(1)) or {}
    except Exception:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}

    merged = dict(defaults)
    for k, v in parsed.items():
        if v is None:
            continue
        merged[k] = v
    merged["type"] = defaults["type"]
    if defaults.get("subtype"):
        merged["subtype"] = defaults["subtype"]

    body = md[m.end() :]
    return render_frontmatter(merged) + body


def frontmatter_defaults(
    *,
    entry: PagePlan,
    plan: IngestPlan,
    today_iso: str,
    source_hash: str | None = None,
) -> dict[str, Any]:
    """Default sensati guidati dagli hook del pack.

    Il set base copre i campi universali. Le strategy del pack possono
    sovrascrivere via ``frontmatter_defaults`` (funzione nel modulo
    ``strategies``) per extra domain-specific (es. ``richiede-logica``
    insurance, ``corte`` legal).
    """
    base: dict[str, Any] = {
        "title": entry.title,
        "type": entry.page_type,
        "tags": [],
        "aliases": [],
        "created": today_iso,
        "updated": today_iso,
        "sources": 1,
    }
    if entry.subtype:
        base["subtype"] = entry.subtype

    # `type: source` richiede source_file/source_type/ingested per il linter.
    # Il LLM frequentemente li omette su prompt lunghi; iniettiamo
    # deterministicamente dall'IngestPlan così il critic non spreca round-trip
    # per riparare campi che già conosciamo.
    if entry.page_type == "source":
        raw_name = Path(plan.source_file).name if plan.source_file else ""
        base["source_file"] = (
            f"raw/{raw_name}" if raw_name else (plan.source_file or "")
        )
        if plan.source_type:
            base["source_type"] = plan.source_type
        base["ingested"] = today_iso
        if source_hash:
            base["source_hash"] = source_hash
        # Numero pagine del documento sorgente (PDF/DOCX/PPTX): iniettato a
        # ingest time, propagato a Qdrant payload via `payload.update(meta)`.
        # Future click-to-source UI leggerà questo per rendere "Pagina N/M".
        if plan.source_pages_count is not None and plan.source_pages_count > 0:
            base["source_pages_count"] = int(plan.source_pages_count)

    # `doc_register` ∈ {operational, conceptual, mixed, unknown} deriva
    # deterministicamente dal source_type via `register.infer_doc_register`.
    # Applicato a TUTTE le pagine generate dallo stesso source (non solo
    # source) così che il RAG agent veda il registro su qualunque chunk
    # recuperi — vedi `rag_agent._build_context`. Inietta il signal a
    # monte (frontmatter) anziché ricalcolarlo al retrieval time: una
    # singola fonte autorevole per query e UI futura.
    register = infer_doc_register(plan.source_type)
    if register and register != "unknown":
        base["doc_register"] = register

    try:
        pack = get_pack()
        extra = _call_optional(pack, "frontmatter_defaults", entry=entry, plan=plan)
        if isinstance(extra, dict):
            base.update(extra)
    except Exception as exc:
        logger.debug("[frontmatter] pack defaults skipped: %s", exc)

    return base


def _call_optional(pack: Any, attr: str, **kwargs: Any) -> Any:
    """Invoca un hook nel modulo ``strategies`` del pack, se presente."""
    import importlib

    if pack.root is None:
        return None
    module_name = f"domains.{pack.name}.strategies"
    try:
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None
    fn = getattr(mod, attr, None)
    if fn is None:
        return None
    return fn(**kwargs)


def render_frontmatter(fm: dict[str, Any]) -> str:
    body = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{body}\n---\n\n"


def ensure_required_sections(
    md: str,
    *,
    entry: PagePlan,
    plan: IngestPlan | None = None,
) -> str:
    """Aggiunge stub per sezioni obbligatorie mancanti.

    Il linter richiede un set fisso di sezioni per page-type (vedi
    ``SEZIONI_SOURCE`` / ``SEZIONI_GARANZIA``). LLM locali su prompt
    lunghi spesso ne saltano alcune — ogni mancante triggera un round-
    trip LLM al critic (~minuti) per contenuto stub-pabile
    deterministicamente. Aggiungiamo sezioni vuote con marker
    ``Da completare``; iterazioni successive del critic possono ancora
    espanderle, ma escono a iter 1 invece di iter MAX_ITER per errori
    strutturali triviali.

    Special-case ``## Fonti``: il linter alza ERROR
    (``citations.fonti.empty``) se la sezione esiste senza wikilink.
    Pre-riempiamo lo stub con il wikilink alla source page derivata dal
    ``plan`` — così lo skeleton passa il check senza altri round-trip.
    """
    if entry.page_type == "source":
        required = SEZIONI_SOURCE
    elif entry.page_type == "concept" and entry.subtype in {
        "garanzia-assicurativa",
        "pack-opzionale",
    }:
        required = SEZIONI_GARANZIA
    else:
        return md

    fm_match = re.match(r"^---\n.*?\n---\n", md, re.DOTALL)
    body_start = fm_match.end() if fm_match else 0
    head = md[:body_start]
    body = md[body_start:]

    source_slug = slug_from_target(plan.source_page.target_path) if plan else None

    body_lower = body.lower()
    appended: list[str] = []
    for section in required:
        text = section.lstrip("# ").strip().lower()
        pat = re.compile(
            rf"^#{{2,6}}\s+{re.escape(text)}\b", re.MULTILINE | re.IGNORECASE
        )
        if pat.search(body_lower):
            continue
        if section == "## Fonti" and source_slug:
            stub = f"\n\n{section}\n\n- [[{source_slug}]] — _Aggiungere riferimento articolo._\n"
        else:
            stub = f"\n\n{section}\n\n_Da completare manualmente._\n"
        appended.append(stub)

    if not appended:
        return md
    return head + body.rstrip() + "".join(appended) + "\n"

"""Validatore di citazioni wikilink nelle risposte RAG.

Estrae i wikilink Obsidian ``[[<folder>/<slug>]]`` dal testo generato
dal LLM e verifica che:

1. ``<folder>`` appartenga ai folder configurati nel Domain Pack
   (``pack.page_types[*].folder``). Folder fuori taxonomy = sempre
   hallucination — il prompt baseline elenca esplicitamente i folder
   ammessi.
2. ``<slug>`` (opzionale, controllato solo se
   ``CITATION_STRICT_GROUNDING=true``) corrisponda a un
   ``document_id`` presente nei sources recuperati per la query. Bar
   stringente: nessun wikilink "extra" verso pagine del vault non
   recuperate, perché il modello non ha letto quelle pagine in questa
   chiamata.

Output: :class:`CitationReport` con lista di violazioni + lista di
citazioni valide. Caller (`rag_agent`) decide se loggare warning,
emettere evento al frontend, o triggerare un repair-loop LLM.

Repair (opzionale, ``CITATION_REPAIR_ENABLED``): rigenera la risposta
con un messaggio di feedback che enumera le fonti valide ammesse + le
violazioni rilevate. Costa una LLM call in più; default OFF.

Design note: pure function. Niente I/O, niente accesso al pack —
quest'ultimo arriva come parametro per testabilità (no monkeypatch
sul registry per i test).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Wikilink Obsidian: [[folder/slug]] o [[folder/slug|alias]] o
# [[folder/slug#section]]. Folder = slug ASCII; slug = qualsiasi
# carattere non `]` o `|` o `#` (Obsidian slug può contenere accenti).
# Catturiamo il segmento `#anchor` per validazione opzionale (gated da
# `CITATION_ANCHOR_VALIDATION_ENABLED`); fuori da quella modalità l'anchor
# viene ignorato (backward-compat con il vecchio comportamento).
_WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+?)(?:#([^\]\|]*))?(?:\|[^\]]*)?\]\]")

# Normalizzazione anchor per confronto vs `section_anchor` payload: stesso
# trattamento di `slug_anchor` (lowercase, spazi→hyphen, drop non
# alfanumerici). Duplicato locale per evitare l'import di chunking dentro
# il path RAG (citation_validator è agents/, chunking è vectorstore/).
_ANCHOR_NORMALIZE = re.compile(r"[^a-z0-9\-_]+")


def _slug_anchor(heading: str) -> str:
    if not heading:
        return ""
    lowered = heading.strip().lower().replace(" ", "-")
    return _ANCHOR_NORMALIZE.sub("", lowered).strip("-")


@dataclass
class CitationViolation:
    raw: str  # wikilink così come appare nel testo
    folder: str
    slug: str
    reason: (
        str  # 'unknown_folder' | 'slug_not_in_sources' | 'unknown_anchor' | 'malformed'
    )
    anchor: str = ""


@dataclass
class CitationReport:
    # (folder, slug, anchor) — anchor stringa vuota quando non presente
    # nel wikilink o quando la validazione anchor è disabilitata.
    valid: list[tuple[str, str, str]] = field(default_factory=list)
    violations: list[CitationViolation] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return bool(self.violations)

    def summary(self) -> str:
        if not self.violations:
            return f"{len(self.valid)} citazioni valide"
        return (
            f"{len(self.valid)} valide · {len(self.violations)} violazioni: "
            + ", ".join(f"{v.raw}({v.reason})" for v in self.violations[:5])
        )


def _allowed_source_ids(sources: list[dict[str, Any]]) -> set[str]:
    """document_id presenti negli hit recuperati per la query."""
    out: set[str] = set()
    for s in sources:
        doc_id = s.get("document_id")
        if isinstance(doc_id, str) and doc_id:
            out.add(doc_id)
    return out


def _allowed_anchors_for(sources: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Indicizza per ``document_id`` (sia "folder/slug" che "slug" nudo) gli
    anchor leciti — slug normalizzato di `section_anchor` e `section_heading`
    di tutti i chunk recuperati per quel doc. Tollerante: se la sorgente
    espone un `section_anchor` già normalizzato, viene usato così com'è.
    """
    out: dict[str, set[str]] = {}
    for s in sources:
        doc_id = s.get("document_id")
        if not isinstance(doc_id, str) or not doc_id:
            continue
        anchors: set[str] = out.setdefault(doc_id, set())
        # Slug del solo basename per accettare cite "[[slug#anchor]]" senza folder
        bare = doc_id.split("/", 1)[1] if "/" in doc_id else doc_id
        if bare:
            out.setdefault(bare, set()).update(anchors)
        sec_anchor = s.get("section_anchor") or ""
        sec_heading = s.get("section_heading") or ""
        if sec_anchor:
            anchors.add(str(sec_anchor).lower())
        if sec_heading:
            anchors.add(_slug_anchor(str(sec_heading)))
    return out


def validate(
    answer: str,
    *,
    allowed_folders: set[str],
    sources: list[dict[str, Any]],
    strict_grounding: bool,
    validate_anchors: bool = False,
) -> CitationReport:
    """Estrai i wikilink dalla risposta e classifica ognuno.

    Args:
        answer: testo generato dall'LLM.
        allowed_folders: folder ammessi (``pack.page_types[*].folder``).
        sources: lista hit recuperati (per controllo grounding strict).
        strict_grounding: se True, ogni slug deve corrispondere a un
            ``document_id`` presente nei ``sources``.
        validate_anchors: se True, valida la parte ``#anchor`` (quando
            presente) contro ``section_anchor`` / ``section_heading``
            slug-normalizzato dei chunk recuperati per quel
            ``document_id``. Default False (zero regressione: comportamento
            storico è "anchor presente ma non controllato").

    Returns:
        :class:`CitationReport` con valid + violations. ``valid`` è una
        lista di tuple ``(folder, slug, anchor)`` — anchor stringa vuota
        quando il wikilink non porta ``#section`` o quando
        ``validate_anchors=False``.
    """
    report = CitationReport()
    if not answer:
        return report

    allowed_ids = _allowed_source_ids(sources) if strict_grounding else set()
    allowed_anchors = _allowed_anchors_for(sources) if validate_anchors else {}

    for match in _WIKILINK_RE.finditer(answer):
        raw = match.group(0)
        target = match.group(1).strip()
        anchor_raw = (match.group(2) or "").strip()
        anchor_norm = _slug_anchor(anchor_raw) if anchor_raw else ""
        if "/" not in target:
            report.violations.append(
                CitationViolation(
                    raw=raw,
                    folder="",
                    slug=target,
                    reason="malformed",
                    anchor=anchor_raw,
                )
            )
            continue
        folder, _, slug = target.partition("/")
        folder = folder.strip()
        slug = slug.strip()
        if folder not in allowed_folders:
            report.violations.append(
                CitationViolation(
                    raw=raw,
                    folder=folder,
                    slug=slug,
                    reason="unknown_folder",
                    anchor=anchor_raw,
                )
            )
            continue
        if strict_grounding:
            # document_id può essere "folder/slug" oppure solo "slug" a
            # seconda dell'indexer. Accetta entrambi.
            full = f"{folder}/{slug}"
            if full not in allowed_ids and slug not in allowed_ids:
                report.violations.append(
                    CitationViolation(
                        raw=raw,
                        folder=folder,
                        slug=slug,
                        reason="slug_not_in_sources",
                        anchor=anchor_raw,
                    )
                )
                continue
        if validate_anchors and anchor_raw:
            # Cerca anchor sia per "folder/slug" sia per "slug" nudo.
            full = f"{folder}/{slug}"
            valid_set = allowed_anchors.get(full) or allowed_anchors.get(slug) or set()
            if anchor_norm and anchor_norm not in valid_set:
                report.violations.append(
                    CitationViolation(
                        raw=raw,
                        folder=folder,
                        slug=slug,
                        reason="unknown_anchor",
                        anchor=anchor_raw,
                    )
                )
                continue
        report.valid.append((folder, slug, anchor_norm))

    return report


def build_repair_feedback(report: CitationReport, sources: list[dict[str, Any]]) -> str:
    """Costruisci il messaggio user di feedback per il repair-loop LLM.

    Elenca esplicitamente le fonti ammesse (recuperate) + le violazioni
    riscontrate. Il messaggio è in italiano (il pack è italiano-only).
    """
    lines = [
        "La risposta precedente contiene citazioni non valide. Rigenera correggendo:"
    ]
    if report.violations:
        lines.append("")
        lines.append("**Violazioni:**")
        for v in report.violations[:10]:
            lines.append(f"- `{v.raw}` → {v.reason}")
    if sources:
        lines.append("")
        lines.append("**Fonti ammesse per questa risposta** (cita SOLO queste):")
        for s in sources:
            doc_id = s.get("document_id") or ""
            title = s.get("title") or doc_id
            page_type = s.get("page_type") or "?"
            if doc_id:
                lines.append(f"- `[[{doc_id}]]` — {title} (page_type={page_type})")
    lines.append("")
    lines.append(
        "Riscrivi la risposta usando esclusivamente i wikilink elencati sopra. "
        "Mantieni il contenuto, sostituisci solo le citazioni errate."
    )
    return "\n".join(lines)

"""Hierarchical (parent-child) chunking.

Strategia "small-to-big" embedded-vs-served:

- **Child** (~400 char): unità di matching vettoriale. Più piccola del
  chunk standard → embedding più focalizzato, recall più alto su query
  specifiche. È il testo che viene effettivamente embeddato in Qdrant.
- **Parent** (~1500-2000 char): unità di servizio al LLM. Più grande →
  preserva contesto narrativo (intero capitolo / H2 section). NON
  embeddato direttamente: viene denormalizzato nel payload di ogni child
  e fornito al modello al posto del child al generation time.

Razionale: la query "casi d'uso" matcha un singolo paragrafo di esempio,
ma il LLM ha bisogno di vedere TUTTA la sezione "Casi d'uso" (con i 3
case study sotto) per rispondere senza inventare. Con chunk piatti il
modello vede solo il paragrafo matched; con hierarchical riceve il
contesto del padre (capitolo intero).

Differenza vs Parent-Section retrieval (già shipato in expansions.py):
- Parent-Section: fetch a runtime via Qdrant scroll dei sibling chunk
  della stessa sezione. Funziona con payload corrente, zero reindex.
- Hierarchical: pre-computato a ingest time, parent_text denormalizzato
  nel payload. Più efficiente a runtime (no I/O extra), ma richiede
  reindex. I due meccanismi sono compatibili — hierarchical superato
  contiene già il segnale di parent-section.

Backward-compatibility: chunk indicizzati prima della feature non hanno
``parent_text`` nel payload — il caller in ``build_context`` deve
gestire il fallback (usa il chunk standard).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from llm_wiki.vectorstore.chunking import (
    _find_atomic_blocks,
    chunk_point_id,
    slug_anchor,
)

_NL = "\n"
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class HierarchicalChunk:
    """Una coppia child↔parent per indicizzazione gerarchica.

    ``child_text`` è ciò che viene embeddato. ``parent_text`` è ciò che
    viene servito al LLM in generation. ``parent_id`` è uno slug stabile
    derivato da ``document_id + section_anchor + parent_window_idx``.

    ``section_heading_fine`` è il heading più profondo (H3+) sotto cui
    ricade il child; ``section_anchor_fine`` è il suo slug normalizzato.
    Permette citazioni anchor-first precise anche quando il parent_window
    contiene più sotto-sezioni H3+ all'interno di un parent H1/H2.
    Fallback al heading di ``section_path[-1]`` quando il child non è
    sotto un heading più profondo del parent window.
    """

    child_text: str
    parent_text: str
    parent_id: str
    section_path: list[str]
    chunk_index: int
    section_heading_fine: str = ""
    section_anchor_fine: str = ""


def _split_into_section_blocks(text: str, max_level: int = 2) -> list[tuple[str, list[str]]]:
    """Spezza il testo in blocchi-sezione delimitati da heading ≤ max_level.

    Ritorna tuple ``(block_text, breadcrumb)``. Default max_level=2 → split
    su H1/H2; H3+ rimangono dentro al loro parent. Se il documento non ha
    heading, l'intero testo è un unico blocco con breadcrumb vuoto.
    """
    lines = text.split(_NL)
    blocks: list[tuple[int, int, list[str]]] = []  # (start_line, end_line, breadcrumb_at_start)
    stack: list[tuple[int, str]] = []
    cur_start = 0
    cur_path: list[str] = []

    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        if level > max_level:
            continue
        # Chiude blocco precedente
        if i > cur_start:
            blocks.append((cur_start, i, list(cur_path)))
        # Aggiorna stack heading
        stack = [(lv, ti) for (lv, ti) in stack if lv < level]
        stack.append((level, m.group(2).strip()))
        cur_path = [ti for _, ti in stack]
        cur_start = i

    # Coda
    if cur_start < len(lines):
        blocks.append((cur_start, len(lines), list(cur_path)))

    out: list[tuple[str, list[str]]] = []
    for start, end, path in blocks:
        body = _NL.join(lines[start:end]).strip()
        if body:
            out.append((body, path))
    return out


def _split_parent_window(block: str, max_size: int) -> list[str]:
    """Se il blocco-sezione è più grande di max_size, lo spezza in
    sotto-finestre rispettando paragrafi (doppio newline) e — in
    fallback — singoli newline. Mai dentro un atomic block."""
    if len(block) <= max_size:
        return [block]

    lines = block.split(_NL)
    atomic = _find_atomic_blocks(lines)
    atomic_set: set[int] = set()
    for start, end in atomic:
        for i in range(start, end):
            atomic_set.add(i)

    # Tentativo split a doppio newline (paragrafi) — ma solo se non taglia atomic.
    windows: list[str] = []
    current: list[str] = []
    current_len = 0

    def _flush() -> None:
        nonlocal current, current_len
        if current:
            joined = _NL.join(current).strip()
            if joined:
                windows.append(joined)
            current = []
            current_len = 0

    in_atomic_run = False
    for i, line in enumerate(lines):
        in_atomic = i in atomic_set
        # Non spezzare DENTRO un atomic block: accumula intera atomic run.
        if in_atomic:
            current.append(line)
            current_len += len(line) + 1
            in_atomic_run = True
            continue
        if in_atomic_run and not in_atomic:
            in_atomic_run = False
        # Punto candidato di split: riga vuota dopo blocco non-atomic, sopra max_size.
        if current_len >= max_size and line.strip() == "":
            _flush()
            continue
        current.append(line)
        current_len += len(line) + 1

    _flush()
    if not windows:
        # Atomic gigante (es. tabellone): emetti as-is, oversize accepted.
        windows = [block]
    return windows


def _split_child_chunks(parent_window: str, child_size: int, child_overlap: int) -> list[str]:
    """Spezza un parent_window in child chunk preservando atomic blocks.

    Strategia: itera per paragrafo (doppio newline). Se il paragrafo è
    atomic (tabella, code fence, callout), lo emette come child intero
    (anche oversize). Altrimenti accumula paragrafi fino a child_size,
    con overlap del prefisso ultimo paragrafo della finestra precedente.
    """
    if len(parent_window) <= child_size:
        return [parent_window.strip()]

    paragraphs = re.split(r"\n\s*\n", parent_window)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    children: list[str] = []
    buf: list[str] = []
    buf_len = 0
    last_para = ""

    for para in paragraphs:
        # Atomic: tabella, code fence, callout — un child indipendente.
        is_atomic = (
            para.startswith("|")
            or para.startswith("```")
            or para.startswith(">")
            or "\n|" in para[:5]
        )
        if is_atomic:
            if buf:
                children.append("\n\n".join(buf))
                buf = []
                buf_len = 0
            children.append(para)
            last_para = para
            continue

        if buf_len + len(para) > child_size and buf:
            children.append("\n\n".join(buf))
            # Overlap: porta avanti il paragrafo precedente se è breve
            if child_overlap > 0 and last_para and len(last_para) <= child_overlap:
                buf = [last_para, para]
                buf_len = len(last_para) + len(para)
            else:
                buf = [para]
                buf_len = len(para)
        else:
            buf.append(para)
            buf_len += len(para) + 2
        last_para = para

    if buf:
        children.append("\n\n".join(buf))

    return [c for c in children if c.strip()]


def chunk_markdown_hierarchical(
    text: str,
    *,
    parent_size: int = 1800,
    child_size: int = 400,
    child_overlap: int = 60,
    max_heading_level_parent: int = 2,
) -> list[HierarchicalChunk]:
    """Spezza il markdown in coppie (child, parent).

    Algoritmo:

    1. Spezza il testo in blocchi-sezione su heading ≤ max_heading_level_parent
       (default H1/H2). Sezioni più piccole del default vengono unite al loro
       parent naturale via breadcrumb.
    2. Ogni blocco-sezione, se > parent_size, viene split in più "parent
       windows" preservando atomic blocks. Sotto parent_size, resta unico
       parent.
    3. Ogni parent window viene split in child chunk di ~child_size con
       overlap del paragrafo precedente.
    4. Per ogni child: ``HierarchicalChunk(child_text, parent_text=window,
       parent_id, section_path)``.

    ``parent_id`` è derivato da ``slug_anchor(section_heading) +
    parent_window_idx`` — stabile fra re-ingest dello stesso documento.

    Returns:
        Lista non vuota di ``HierarchicalChunk``. Lista vuota se ``text``
        è vuoto o solo whitespace.
    """
    if not text or not text.strip():
        return []

    section_blocks = _split_into_section_blocks(text, max_level=max_heading_level_parent)
    if not section_blocks:
        section_blocks = [(text.strip(), [])]

    raw_out: list[HierarchicalChunk] = []

    for block, breadcrumb in section_blocks:
        section_heading = breadcrumb[-1] if breadcrumb else ""
        anchor_base = slug_anchor(section_heading) or "preamble"

        parent_windows = _split_parent_window(block, parent_size)
        for pw_idx, parent_window in enumerate(parent_windows):
            # parent_id locale al doc: caller deve prependere document_id
            local_parent_id = f"{anchor_base}:{pw_idx}"
            children = _split_child_chunks(parent_window, child_size, child_overlap)
            if not children:
                continue
            # Indice heading interni al parent_window (H3+): per ogni child
            # cerchiamo l'heading immediatamente precedente al suo offset.
            window_index = _heading_index_for_window(parent_window)
            for child in children:
                fine_heading, fine_anchor = _resolve_child_heading(
                    parent_window, child, window_index, section_heading
                )
                raw_out.append(
                    HierarchicalChunk(
                        child_text=child.strip(),
                        parent_text=parent_window.strip(),
                        parent_id=local_parent_id,
                        section_path=list(breadcrumb),
                        chunk_index=-1,  # placeholder, reindex post-filter
                        section_heading_fine=fine_heading,
                        section_anchor_fine=fine_anchor,
                    )
                )

    # Filtra child troppo brevi, poi assegna chunk_index contiguo.
    filtered = [c for c in raw_out if len(c.child_text) >= 20]
    return [
        HierarchicalChunk(
            child_text=c.child_text,
            parent_text=c.parent_text,
            parent_id=c.parent_id,
            section_path=c.section_path,
            chunk_index=i,
            section_heading_fine=c.section_heading_fine,
            section_anchor_fine=c.section_anchor_fine,
        )
        for i, c in enumerate(filtered)
    ]


def _heading_index_for_window(parent_window: str) -> list[tuple[int, str]]:
    """Indice ``(offset_char, heading_text)`` degli heading interni al
    parent_window. Tipicamente heading H3+ (H1/H2 sono stati usati per
    splittare blocchi-sezione a monte) ma il match è inclusivo: cattura
    qualunque riga ``# ... ###### …``. Per child che precedono ogni heading
    interno, il caller usa il ``fallback_heading`` del breadcrumb.
    """
    out: list[tuple[int, str]] = []
    offset = 0
    for line in parent_window.split(_NL):
        m = _HEADING_RE.match(line)
        if m:
            out.append((offset, m.group(2).strip()))
        offset += len(line) + 1
    return out


def _resolve_child_heading(
    parent_window: str,
    child_text: str,
    window_index: list[tuple[int, str]],
    fallback_heading: str,
) -> tuple[str, str]:
    """Per un child, ritorna ``(heading_fine, anchor_fine)`` cercando
    l'heading immediatamente precedente al suo offset nel parent_window.
    Fallback al heading del parent_window quando il child precede ogni
    heading interno (o il window non ha heading interni).
    """
    if not window_index:
        return fallback_heading, slug_anchor(fallback_heading)
    body = child_text.strip()
    needle = body[:80] if body else ""
    if not needle:
        return fallback_heading, slug_anchor(fallback_heading)
    try:
        idx = parent_window.index(needle)
    except ValueError:
        return fallback_heading, slug_anchor(fallback_heading)
    found = fallback_heading
    for off, heading in window_index:
        if off > idx:
            break
        found = heading
    return found, slug_anchor(found)


def build_parent_id(document_id: str, local_parent_id: str) -> str:
    """Compone l'id globale del parent: ``<document_id>::<local>``.

    Caller dell'indexer applica questa funzione prima di scrivere su
    Qdrant per evitare collisioni cross-documento.
    """
    return f"{document_id}::{local_parent_id}"


def child_point_id(document_id: str, chunk_index: int) -> str:
    """Stable UUID v5 per il child (riusa ``chunk_point_id`` dal modulo
    chunking standard). Esposto qui per chiarire l'API hierarchical."""
    return chunk_point_id(document_id, chunk_index)


def collapse_hits_by_parent(
    hits: list[dict[str, Any]],
    *,
    keep_first_score: bool = True,
) -> list[dict[str, Any]]:
    """Collassa hit child che condividono lo stesso ``parent_id``.

    Dedup: se 3 child dello stesso parent matchano la query, ritorna UN
    hit consolidato con ``parent_text`` come testo principale. Lo score
    è quello del child best-ranked (``keep_first_score=True``) — la
    rilevanza del migliore prevale, evitando inflazione dovuta alla
    presenza di più children del medesimo parent.

    Hit senza ``parent_id`` (legacy, pre-hierarchical) o senza
    ``parent_text`` rimangono invariati e passano attraverso.

    Caller pattern: invoca PRIMA di build_context quando
    ``HIERARCHICAL_RETRIEVAL_ENABLED=true``.
    """
    if not hits:
        return hits

    by_parent: dict[str, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []

    for h in hits:
        payload = h.get("payload") or {}
        parent_id = payload.get("parent_id")
        parent_text = payload.get("parent_text")
        if not parent_id or not parent_text:
            out.append(h)
            continue

        key = str(parent_id)
        if key in by_parent:
            # Già visto: aggiorna lo score se questo child è migliore
            existing = by_parent[key]
            if not keep_first_score and (h.get("score") or 0) > (existing.get("score") or 0):
                existing["score"] = h.get("score")
            existing.setdefault("merged_child_count", 1)
            existing["merged_child_count"] = int(existing["merged_child_count"]) + 1
            continue

        # Prima occorrenza del parent: emetti hit con text=parent_text.
        # Conserviamo il child originale per audit e l'embed per debug.
        merged = dict(h)
        merged_payload = dict(payload)
        merged_payload["child_text"] = payload.get("text") or payload.get("raw_text") or ""
        merged_payload["text"] = parent_text
        merged_payload["raw_text"] = parent_text
        merged["payload"] = merged_payload
        merged["hierarchical_collapsed"] = True
        merged["merged_child_count"] = 1
        by_parent[key] = merged
        out.append(merged)

    return out


__all__ = [
    "HierarchicalChunk",
    "build_parent_id",
    "child_point_id",
    "chunk_markdown_hierarchical",
    "collapse_hits_by_parent",
]

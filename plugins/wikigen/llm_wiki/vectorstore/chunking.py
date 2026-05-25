"""Chunking markdown-aware per pagine wiki.

Le pagine wiki hanno struttura:
- frontmatter YAML in testa
- heading Obsidian (`##`, `###`)
- callout (`> [!tip]`) e tabelle che NON vanno spezzati
- wikilink `[[target]]` che trasportiamo nel payload come metadata di discovery

Strategia: split principale per heading di secondo livello, fallback per
paragrafi. Ogni chunk eredita una header sintetica (titolo pagina + breadcrumb)
che aiuta embedding retrieval su query decontestualizzate.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

try:
    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter,  # type: ignore[import-not-found]
    )
except ImportError:  # pragma: no cover
    RecursiveCharacterTextSplitter = None  # type: ignore[assignment, misc]

from llm_wiki.config import CHUNK_OVERLAP, CHUNK_SIZE

_NL = "\n"
_NL2 = "\n\n"

# Separatori ordinati per autorevolezza decrescente: rispettano la struttura
# markdown e preservano blocchi tecnici (tabelle, callout).
_SEPARATORS = [
    _NL + "## ",
    _NL + "### ",
    _NL + "#### ",
    _NL2,
    _NL,
    ". ",
    " ",
]

if RecursiveCharacterTextSplitter is not None:
    _splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=_SEPARATORS,
        keep_separator=True,
    )
else:

    class _FallbackSplitter:
        def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

        def split_text(self, text: str) -> list[str]:
            step = max(1, self.chunk_size - self.chunk_overlap)
            return [text[i : i + self.chunk_size] for i in range(0, len(text), step)]

    _splitter = _FallbackSplitter(CHUNK_SIZE, CHUNK_OVERLAP)  # type: ignore[assignment]


_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def extract_wikilinks(text: str) -> list[str]:
    """Estrae i target dei wikilink `[[target]]` / `[[target|alias]]` / `[[target#anchor]]`.

    Normalizza strippando estensione e spazi.
    """
    seen: list[str] = []
    for match in _WIKILINK.finditer(text):
        target = match.group(1).strip()
        if target.endswith(".md"):
            target = target[:-3]
        target = target.strip().strip("/")
        if target and target not in seen:
            seen.append(target)
    return seen


# Riferimenti ad articoli nel formato contrattuale italiano:
#   "art. 5", "art. 5.1.7", "art. 2.4 lett. b", "articolo 1913", "artt. 1882 ss."
# Catturiamo numero + eventuale lettera. Il comma-lettera viene normalizzato
# come `num.letter` per matching esatto in payload (es. "2.4.b").
_ARTICOLO_REF = re.compile(
    r"art(?:icolo|icoli|\.|t\.)\s*" r"(\d+(?:[\.\-]\d+)*)" r"(?:\s*(?:lett\.?|lettera)\s*([a-z]))?",
    re.IGNORECASE,
)


def extract_article_refs(text: str) -> list[str]:
    """Estrae riferimenti ad articoli da un chunk di testo wiki.

    Riconosce le forme contrattuali italiane: `art. 5`, `art. 5.1.7`,
    `art. 2.4 lett. b`, `articolo 1913`, `artt. 1882`. Normalizza in stringhe
    `"5"`, `"5.1.7"`, `"2.4.b"`. Dedup preservando l'ordine di apparizione.

    Scopo: popolare `articoli_citati` nel payload dei chunk, per abilitare il
    follow-the-link retrieval (vedi `core.py::_expand_with_rinvii`). Il
    dispatcher scarta articoli "nudi" come `art. 1` senza contesto se vuoi
    ridurre rumore; la lista ritornata include tutto — filtering applicativo
    spetta al caller.
    """
    seen: list[str] = []
    for match in _ARTICOLO_REF.finditer(text):
        num = match.group(1)
        letter = match.group(2)
        key = f"{num}.{letter.lower()}" if letter else num
        if key not in seen:
            seen.append(key)
    return seen


# Table-aware chunker: prima del split standard, identifichiamo blocchi atomici
# (tabelle markdown, callout Obsidian, fenced code — incluso il YAML gemello di
# tabelle strutturate) e li emettiamo come chunk INSCINDIBILI. Le tabelle oltre
# CHUNK_SIZE restano in un unico chunk over-size: preferiamo il sovradimensionamento
# alla perdita di coerenza riga/colonna, che produrrebbe allucinazioni sui limiti.
_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
_CALLOUT_LINE = re.compile(r"^\s*>\s?")
_FENCE = re.compile(r"^\s*```")


def _find_atomic_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Scansiona le righe e ritorna range `[start, end)` di blocchi atomici.

    Atomic = tabella markdown (linee contigue `|...|`), callout Obsidian
    (linee contigue che iniziano con `>`), fenced code block (dal primo
    ` ``` ` al successivo). I range non si sovrappongono e sono ordinati.
    """
    blocks: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # Fenced code block: ```...```
        if _FENCE.match(line):
            start = i
            i += 1
            while i < n and not _FENCE.match(lines[i]):
                i += 1
            if i < n:
                i += 1  # includi la fence di chiusura
            blocks.append((start, i))
            continue
        # Tabella markdown: righe contigue che iniziano/finiscono con `|`.
        if _TABLE_LINE.match(line):
            start = i
            while i < n and _TABLE_LINE.match(lines[i]):
                i += 1
            # Minimum 2 linee per qualificarsi come tabella (header + separator o header + row)
            if i - start >= 2:
                blocks.append((start, i))
                continue
            # Single `|` line: probabilmente non è tabella, non proteggere
        # Callout Obsidian: linee contigue che iniziano con `>`.
        if _CALLOUT_LINE.match(line):
            start = i
            while i < n and (_CALLOUT_LINE.match(lines[i]) or lines[i].strip() == ""):
                # Consente righe vuote all'interno di un callout Obsidian
                # (es. `> [!rule]` + `>` + `> - item`). Termina quando finisce
                # la sequenza e la riga successiva non è callout.
                if lines[i].strip() == "" and (i + 1 >= n or not _CALLOUT_LINE.match(lines[i + 1])):
                    break
                i += 1
            if i > start:
                blocks.append((start, i))
                continue
        i += 1
    return blocks


def chunk_markdown(text: str) -> list[str]:
    """Split markdown preservando heading e **blocchi atomici**.

    Blocchi atomici (tabelle, callout, fenced code / YAML) non vengono mai
    spezzati; le sezioni di testo fra un blocco atomico e l'altro passano per
    il `_splitter` standard. Chunk vuoti / troppo corti (< 20 char) filtrati.
    """
    lines = text.split(_NL)
    atomic_ranges = _find_atomic_blocks(lines)

    chunks: list[str] = []
    cursor = 0
    for start, end in atomic_ranges:
        if cursor < start:
            non_atomic = _NL.join(lines[cursor:start])
            if non_atomic.strip():
                chunks.extend(_splitter.split_text(non_atomic))
        atomic = _NL.join(lines[start:end])
        if atomic.strip():
            chunks.append(atomic)
        cursor = end
    if cursor < len(lines):
        tail = _NL.join(lines[cursor:])
        if tail.strip():
            chunks.extend(_splitter.split_text(tail))

    return [c.strip() for c in chunks if len(c.strip()) >= 20]


def chunk_point_id(document_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk_index}"))


# --- section provenance ----------------------------------------------------
#
# Per ogni chunk vogliamo associare il "breadcrumb" dei heading markdown sotto
# cui ricade. Questo permette al RAG di produrre wikilink puntuali nel formato
# Obsidian `[[folder/slug#Heading]]` invece di citazioni generiche
# `[[folder/slug]]`. Stessa pagina, chunk diversi → ancore diverse →
# verificabilità della citazione molto più alta lato utente.

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_ANCHOR_NORMALIZE = re.compile(r"[^a-z0-9\-_]+")


def slug_anchor(heading: str) -> str:
    """Versione slug-safe del heading (per anchor di wikilink stile MkDocs/GH).

    Obsidian accetta anche l'heading verbatim; emettiamo lo slug come fallback
    portabile fra parser markdown diversi. Lowercase, spazi → hyphen,
    rimozione di caratteri non alfanumerici. Vuoto in input → vuoto in output.
    """
    if not heading:
        return ""
    lowered = heading.strip().lower()
    lowered = lowered.replace(" ", "-")
    lowered = _ANCHOR_NORMALIZE.sub("", lowered)
    return lowered.strip("-")


def build_section_index(text: str) -> list[tuple[int, list[str]]]:
    """Costruisci un indice ``(line_start_offset, breadcrumb)`` riga per riga.

    Walka le linee di ``text`` tenendo uno stack di heading attivi
    (livello → titolo). A ogni riga registra l'offset di inizio (in caratteri
    sul testo originale) e la lista dei titoli ancora in scope. Usata dal
    chunker per associare ogni chunk al suo breadcrumb di sezione.
    """
    lines = text.split(_NL)
    stack: list[tuple[int, str]] = []  # (level, title)
    out: list[tuple[int, list[str]]] = []
    offset = 0
    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            # Pop di tutti gli heading ≥ livello corrente (entriamo in una nuova sezione).
            stack = [(lv, ti) for (lv, ti) in stack if lv < level]
            stack.append((level, title))
        out.append((offset, [t for _, t in stack]))
        offset += len(line) + 1  # +1 per il newline
    return out


def section_paths_for_chunks(text: str, chunks: list[str]) -> list[list[str]]:
    """Per ogni chunk, ritorna il breadcrumb di heading sotto cui si trova.

    Strategia:
    1. costruisce un indice riga→breadcrumb sul testo originale;
    2. per ciascun chunk individua l'offset cercando una sotto-stringa
       prefisso (le prime ~80 char strip), perché lo splitter può aver
       compresso whitespace marginale;
    3. fallback se non trovato: usa la prima riga heading interna al chunk
       (capita per chunk che iniziano con `## …`), altrimenti breadcrumb vuoto.

    Output allineato per indice a ``chunks``. Mai None: chunk senza sezione →
    lista vuota.
    """
    if not chunks:
        return []
    section_index = build_section_index(text)
    # Costruzione greedy: per ricerche multiple, scansione lineare basta
    # (ogni chunk ~poche centinaia di caratteri, page tipica ~10-50 chunk).
    out: list[list[str]] = []
    for chunk in chunks:
        body = chunk.strip()
        if not body:
            out.append([])
            continue
        needle = body[:80]
        try:
            idx = text.index(needle)
        except ValueError:
            # Fallback: heading interno al chunk
            m_inside = re.search(r"^(#{1,6})\s+(.+)$", body, re.MULTILINE)
            if m_inside:
                out.append([m_inside.group(2).strip()])
            else:
                out.append([])
            continue
        # Trova l'ultima entry con offset ≤ idx
        path: list[str] = []
        for off, p in section_index:
            if off > idx:
                break
            path = p
        out.append(path)
    return out


# Section-pair cross-referencing: molte pagine garanzia hanno "## Cosa copre" e
# "## Cosa NON copre" (o equivalenti). Il chunker testuale separa quasi sempre le
# due sezioni, producendo chunk che recuperati da soli possono far credere a una
# copertura illimitata. Mappiamo ogni marker di sezione alla sua "sorella" e,
# quando rileviamo uno dei marker nel chunk, iniettiamo un footer che rimanda
# alla sorella nella stessa pagina. Il footer viaggia nell'embedding dense e aiuta
# il reranker a tenere insieme i due chunk complementari.
_SECTION_PAIR: dict[str, str] = {
    "## cosa copre": "## Cosa NON copre",
    "## cosa non copre": "## Cosa copre",
    "## oggetto dell'assicurazione": "## Esclusioni",
    "## esclusioni": "## Cosa copre / Oggetto dell'assicurazione",
    "## delimitazioni": "## Cosa copre / Oggetto dell'assicurazione",
    "### esclusioni principali": "### Cosa copre",
    "### cosa copre": "### Esclusioni / Delimitazioni",
}


def _detect_pair_hint(chunk: str, relative_path: str | None) -> str | None:
    """Rileva marker di sezione pair-critiche e produce un footer di cross-reference.

    Return una riga di footer da appendere al chunk, o None se non applicabile.
    Il footer ha forma wiki, così embedding dense e BM25 lo usano come segnale.
    """
    lower = chunk.lower()
    for marker, partner in _SECTION_PAIR.items():
        if marker in lower:
            if relative_path:
                stem = relative_path
                if stem.endswith(".md"):
                    stem = stem[:-3]
                return (
                    f"[Riferimento interno] Questa sezione è **complementare** a «{partner}» "
                    f"della stessa pagina [[{stem}]]. Una risposta completa richiede di consultarle entrambe."
                )
            return (
                f"[Riferimento interno] Questa sezione è complementare a «{partner}» "
                "della stessa pagina. Consultare entrambe per una risposta completa."
            )
    return None


def prepare_chunk_text(chunk: str, metadata: dict[str, Any]) -> str:
    """Arricchisce il chunk con header semantico + footer di cross-reference.

    Formato:
        TITOLO (categoria · tags)
        File: wiki/<relative_path>
        ---
        <chunk body>
        ---
        [Riferimento interno] ... (solo per sezioni pair-critiche: cosa copre / cosa non copre)
    """
    header: list[str] = []

    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        header.append(title.strip())

    category = metadata.get("category")
    if isinstance(category, str) and category.strip():
        header.append(f"Categoria: {category.strip()}")

    tags = metadata.get("tags")
    if isinstance(tags, list) and tags:
        header.append("Tag: " + ", ".join(str(t) for t in tags[:6]))

    rel = metadata.get("relative_path")
    if isinstance(rel, str) and rel.strip():
        header.append(f"File: {rel.strip()}")

    head = _NL.join(header).strip()
    body = chunk.strip()

    pair_hint = _detect_pair_hint(
        chunk,
        metadata.get("relative_path") if isinstance(metadata.get("relative_path"), str) else None,
    )
    footer = f"\n---\n{pair_hint}" if pair_hint else ""

    if not head:
        return body + footer
    return f"{head}\n---\n{body}{footer}"

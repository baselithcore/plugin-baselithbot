"""Query→page_type inference (heuristic, zero LLM call).

Scopo: detectare l'archetipo lessicale di una query utente (definitional /
example-seeking / procedural / overview) e mapparlo a uno dei
``page_type`` declarati dal Domain Pack attivo, così da poter applicare
un filtro permissivo al retrieval Qdrant. Difesa contro query specifiche
che ritornano top-K saturati da chunk di tipo non pertinente
(es. domanda "casi d'uso" → top-K pieno di concept page invece di source
page con esempi).

Inferenza heuristica (regex IT + EN), confidence-tier:

- ``strict``  — pattern lessicale inequivocabile (es. "cos'è X",
                "esempi di X"). Sicuro applicare hard filter.
- ``soft``    — segnale presente ma ambiguo (es. solo "definizione" nel
                mezzo della frase). Caller dovrebbe applicare boost,
                non filtro.
- ``none``    — nessun segnale identificato. No-op.

Mapping a page_type:

- Definitional → page_type con id ∈ {concept, entity} o label/plural
  che contiene "concet" / "entit" / "definizion".
- Example     → page_type con id ∈ {source, case_study, example} o
  label/plural che contiene "fonte" / "source" / "caso" / "esempio".
- Procedural  → page_type con id ∈ {source, runbook, procedure} o
  label/plural che contiene "fonte" / "source" / "procedur" / "runbook".

Il caller (``core.search``) decide cosa fare: dual-retrieval con RRF,
boost di score post-hybrid, o hard filter. Questo modulo è puro
classifier — niente I/O, niente side effect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from llm_wiki.domain.pack import DomainPack, PageType

QueryArchetype = Literal[
    "definitional", "example", "procedural", "overview", "comparative", "unknown"
]
Confidence = Literal["strict", "soft", "none"]


# Pattern strict: query che inizia con (o contiene chiaramente) il marker.
# Confidence "strict" → sicuro applicare hard filter.
_DEFINITIONAL_STRICT = re.compile(
    r"^\s*(?:"
    r"cos['’]?\s*è\s+"
    r"|che\s+cos['’]?\s*è\s+"
    r"|che\s+cosa\s+(?:è|significa|vuol\s+dire|s'intende\s+per)\s+"
    r"|cosa\s+(?:è|significa|vuol\s+dire|s'intende\s+per)\s+"
    r"|definizione\s+di\s+"
    r"|definisci\s+"
    r"|spiega\s+(?:il\s+significato\s+di|cosa\s+significa)\s+"
    r"|what\s+is\s+(?:a\s+|an\s+|the\s+)?"
    r"|define\s+(?:a\s+|an\s+|the\s+)?"
    r"|meaning\s+of\s+"
    r")",
    re.IGNORECASE,
)

_EXAMPLE_STRICT = re.compile(
    r"^\s*(?:"
    r"(?:quali\s+sono\s+(?:gli|alcuni|i)\s+)?esempi\s+(?:di|d['’])\s+"
    r"|(?:dammi|fai|fammi|mostrami|fornisci)\s+(?:un\s+|degli\s+)?esempi[o]?\s+"
    r"|(?:quali\s+sono\s+i\s+)?casi\s+(?:d['’]\s*uso|studio|reali)"
    r"|case\s+stud(?:y|ies)"
    r"|use\s+cases?"
    r"|examples?\s+of\s+"
    r"|esempi\s+pratici\s+di\s+"
    r")",
    re.IGNORECASE,
)

_PROCEDURAL_STRICT = re.compile(
    r"^\s*(?:"
    r"come\s+(?:faccio|si\s+fa|fare|configuro|configurare|installo|installare|"
    r"eseguo|eseguire|deployo|deployare|avvio|avviare|creo|creare)\s+"
    r"|procedura\s+per\s+"
    r"|passi\s+per\s+"
    r"|step(?:s)?\s+per\s+"
    r"|tutorial\s+(?:per|su)\s+"
    r"|how\s+(?:do\s+i|to)\s+"
    r"|step[-\s]by[-\s]step\s+"
    r")",
    re.IGNORECASE,
)

# Comparative: cross-chapter linking via Knowledge Graph (graphify
# principle #4 "query as traversal"). Detect quando l'utente sta
# comparando, contrastando, o cercando relazioni fra ≥ 2 entità.
# Strict: marker lessicale chiaramente comparativo.
_COMPARATIVE_STRICT = re.compile(
    r"(?:"
    r"\b(?:compara|confronta|paragona|metti\s+a\s+confronto)\b"
    r"|\bdifferenz[ae]\s+(?:tra|fra)\b"
    r"|\b(?:rispetto\s+a|in\s+confronto\s+a|paragonato\s+a)\b"
    r"|\b(?:vs\.?|versus)\b"
    r"|\bsimilarit(?:à|a)\s+(?:tra|fra)\b"
    r"|\b(?:relazione|legame|nesso|collegamento)\s+(?:tra|fra)\b"
    r"|\bcompare\b"
    r"|\bdifference[s]?\s+between\b"
    r"|\b(?:as\s+opposed\s+to|compared\s+to|versus|vs)\b"
    r")",
    re.IGNORECASE,
)
# Soft: query con "e" o "o" tra due termini che POTREBBERO essere
# entità: l'identificazione vera passa per il KG lookup nel caller.
_COMPARATIVE_SOFT = re.compile(
    r"\b(?:\w+)\s+(?:e|o|and|or)\s+(?:\w+)\b.*\?$",
    re.IGNORECASE,
)

# Pattern soft: marker presente ma non al fronte (= meno determinante).
_DEFINITIONAL_SOFT = re.compile(
    r"\b(?:definizione|significato|cosa\s+significa|what\s+is)\b", re.IGNORECASE
)
_EXAMPLE_SOFT = re.compile(
    r"\b(?:esempi|esempio|caso\s+d['’]\s*uso|case\s+study|use\s+case|examples?)\b",
    re.IGNORECASE,
)
_PROCEDURAL_SOFT = re.compile(
    r"\b(?:come\s+fare|comando|tutorial|procedura|step\s+by\s+step|how\s+to)\b",
    re.IGNORECASE,
)


# Heuristic mapping da archetipo a "famiglia" di page_type. Per ogni
# archetype una lista ordinata di pattern (id-exact, sostringa nel label
# o nel plural). Il primo match nella lista vince — ordine = priorità.
_ARCHETYPE_PAGE_TYPE_HINTS: dict[QueryArchetype, list[str]] = {
    "definitional": ["concept", "entity", "concetto", "entità", "definizion"],
    "example": ["case_study", "example", "esempio", "caso", "source", "fonte"],
    "procedural": ["runbook", "procedure", "procedura", "source", "fonte"],
    "overview": ["topic", "tema"],
    # Comparative: niente hint page_type — il caller usa il graph layer
    # per il routing (shortest_path + entity overlap), non un filter Qdrant.
    "comparative": [],
    "unknown": [],
}


@dataclass(frozen=True)
class QueryFilterInference:
    """Esito dell'inferenza pre-retrieval su una query."""

    archetype: QueryArchetype
    confidence: Confidence
    page_type_id: str | None  # id risolto sul pack attivo; None se nessun match
    matched_pattern: str  # diagnostico per logging (es. "definitional_strict")


def detect_archetype(query: str) -> tuple[QueryArchetype, Confidence, str]:
    """Classifica la query come (archetype, confidence, matched_pattern).

    Strict batte soft. In caso di match strict multipli, ordine di
    priorità: definitional > example > procedural > overview. Empiricamente
    una stessa query raramente colpisce due strict, ma se accade è
    perché contiene entrambi i marker (es. "esempi di come configurare X"
    → example wins, perché l'intent dominante è cercare esempi).
    """
    q = (query or "").strip()
    if not q:
        return ("unknown", "none", "")

    # Comparative ha priorità sui markers strict di altri archetipi:
    # "compara X e Y" è inequivocabilmente comparativo anche se X/Y
    # sono concetti definitionali.
    if _COMPARATIVE_STRICT.search(q):
        return ("comparative", "strict", "comparative_strict")
    if _DEFINITIONAL_STRICT.search(q):
        return ("definitional", "strict", "definitional_strict")
    if _EXAMPLE_STRICT.search(q):
        return ("example", "strict", "example_strict")
    if _PROCEDURAL_STRICT.search(q):
        return ("procedural", "strict", "procedural_strict")

    # Soft fallback
    if _DEFINITIONAL_SOFT.search(q):
        return ("definitional", "soft", "definitional_soft")
    if _EXAMPLE_SOFT.search(q):
        return ("example", "soft", "example_soft")
    if _PROCEDURAL_SOFT.search(q):
        return ("procedural", "soft", "procedural_soft")
    # NB: comparative_soft NON è attivato qui perché la regex matcha
    # troppe query (qualunque "X e Y?" è ambiguamente comparativo).
    # Il caller può invocarlo esplicitamente quando ha bisogno di
    # massimo recall comparativo (es. agentic RAG plan-and-execute).

    return ("unknown", "none", "")


def spot_entities_in_query(query: str, *, limit: int = 5) -> list[str]:
    """Identifica entità del KG citate nella query (substring match
    case-insensitive su entity name + aliases). Ritorna ``canonical_entity_id``
    in ordine di apparizione, dedupliccati.

    Coerente con graphify principle "deduplication via canonical id":
    "Unipol" e "Unipol Assicurazioni" collassano sullo stesso id.
    Best-effort: KG offline / store mancante → lista vuota.

    Usato dal RAG quando archetype=comparative per pilotare
    ``expand_with_entity_graph(query_entities=...)`` → shortest-path boost.
    """
    q = (query or "").strip()
    if not q:
        return []
    try:
        from llm_wiki.graphdb.store import get_kg_store
    except Exception:
        return []
    store = get_kg_store()
    if not store.enabled:
        return []
    # Recupera tutti gli entity name/aliases. Su grafi piccoli (<10k ent)
    # questa è un'unica query. Per scale up serve invertire la lookup
    # (full-text index su entity name) — future PR.
    try:
        # Cypher minimalista: nessun filtro lato server (cattura aliases).
        rows = store._rows(  # noqa: SLF001
            store._g.query(  # noqa: SLF001
                "MATCH (e:Entity) RETURN e.id, e.name, e.aliases LIMIT 5000"
            )
        )
    except Exception:
        return []
    q_lower = q.lower()
    out: list[str] = []
    seen: set[str] = set()
    # Match più lungo prima: "unipol assicurazioni" prima di "unipol".
    candidates: list[tuple[int, str, str]] = []  # (len_desc, surface, canonical_id)
    for r in rows:
        if not r or len(r) < 2:
            continue
        eid_raw = r[0]
        if isinstance(eid_raw, list | tuple) and len(eid_raw) >= 2:
            eid = eid_raw[1]
        else:
            eid = eid_raw
        if not isinstance(eid, str) or not eid:
            continue
        name_raw = r[1]
        if isinstance(name_raw, list | tuple) and len(name_raw) >= 2:
            name = name_raw[1]
        else:
            name = name_raw
        if not isinstance(name, str):
            name = ""
        aliases_raw = r[2] if len(r) > 2 else ""
        if isinstance(aliases_raw, list | tuple) and len(aliases_raw) >= 2:
            aliases_raw = aliases_raw[1]
        aliases = [a for a in str(aliases_raw or "").split(",") if a]
        for surface in [name, *aliases]:
            s = (surface or "").strip()
            if not s:
                continue
            candidates.append((-len(s), s.lower(), eid))
    candidates.sort()
    for _, surface, eid in candidates:
        if eid in seen:
            continue
        # Word boundary semplice per evitare match parziali.
        boundary = re.compile(r"(?<!\w)" + re.escape(surface) + r"(?!\w)", re.IGNORECASE)
        if boundary.search(q_lower):
            out.append(eid)
            seen.add(eid)
            if len(out) >= limit:
                break
    return out


def _page_type_matches_hint(pt: PageType, hint: str) -> bool:
    """Match permissivo: id esatto, oppure hint contenuto in
    label/plural/folder (lowercase)."""
    if pt.id == hint:
        return True
    h = hint.lower()
    for candidate in (pt.label, pt.plural, pt.folder):
        if candidate and h in candidate.lower():
            return True
    return False


def resolve_page_type(archetype: QueryArchetype, pack: DomainPack | None) -> str | None:
    """Mappa l'archetipo a un ``page_type.id`` esistente nel pack.

    Ritorna ``None`` se il pack è ``None``, se l'archetipo è ``unknown``,
    o se nessun page_type del pack matcha gli hint dell'archetipo.
    """
    if pack is None or archetype == "unknown":
        return None
    hints = _ARCHETYPE_PAGE_TYPE_HINTS.get(archetype, [])
    if not hints:
        return None
    for hint in hints:
        for pt in pack.page_types:
            if _page_type_matches_hint(pt, hint):
                return pt.id
    return None


def infer(query: str, pack: DomainPack | None) -> QueryFilterInference:
    """Routine end-to-end: query+pack → inference.

    Caller pattern raccomandato:

    .. code-block:: python

        inf = infer(query, pack)
        if inf.page_type_id and inf.confidence == "strict":
            # safe: hard filter o dual retrieval con boost forte
            ...
        elif inf.page_type_id and inf.confidence == "soft":
            # boost permissivo (score nudge), MAI hard filter
            ...
    """
    archetype, confidence, matched = detect_archetype(query)
    pt_id = resolve_page_type(archetype, pack) if archetype != "unknown" else None
    return QueryFilterInference(
        archetype=archetype,
        confidence=confidence,
        page_type_id=pt_id,
        matched_pattern=matched,
    )


__all__ = [
    "Confidence",
    "QueryArchetype",
    "QueryFilterInference",
    "detect_archetype",
    "infer",
    "resolve_page_type",
    "spot_entities_in_query",
]

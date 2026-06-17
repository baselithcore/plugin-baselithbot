"""Prompt templates and JSON-parsing utilities for the agentic RAG agent.

Extracted from :mod:`llm_wiki.agents.agentic_rag` to stay within the
500-LOC file cap. All symbols are re-exported by the parent module so
existing imports remain unaffected.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

# Planner: estrae aspetti latenti da una domanda composita.
# Esempio: "cos'è il RAG e quali sono i casi d'uso?" → due aspetti
# (definizione, esempi). Atomic queries → un solo sub_query (= identità).
_PLANNER_SYSTEM = """Sei un planner di retrieval per un sistema RAG agentico.
Data una domanda dell'utente, decidi se è composita o atomica:

- ATOMICA: copre UN solo aspetto (es. "cos'è il chunking?"). Sub_queries = [domanda originale].
- COMPOSITA: copre 2+ aspetti distinti (es. "cos'è X e come si implementa Y?",
  "definizione + esempi", "rischi + mitigazioni"). Sub_queries = una per aspetto.

Regole:
- Sub_queries in italiano, in forma interrogativa, ognuna atomica.
- Massimo {max_subs} sub_queries.
- Le sub_queries devono essere DISTINTE per intento di retrieval (definizione vs
  procedura vs esempio vs confronto). NON paraphrase della stessa domanda.
- Se la domanda chiede esplicitamente "come/implementazione/procedura" + "cos'è/definizione",
  produci ALMENO due sub_queries: una concettuale ("cos'è X?") e una operativa
  ("come si implementa X?"/"quali sono i passi per X?").
- **Memoria conversazionale**: quando viene fornita una "Conversazione precedente",
  ogni sub_query DEVE essere AUTONOMA — risolvi pronomi ("quello/it/this"),
  riferimenti ellittici ("e per la v3?"), continuazioni ("approfondiscilo")
  inserendo l'entità esplicita dallo storico. Il retrieval è cieco al dialog —
  una sub_query con "quello" recupera nulla.

Output: SOLO un oggetto JSON {{"sub_queries": ["...", "..."], "rationale": "breve"}},
niente preambolo."""

# Reflector: dato il set di hits recuperati, decide se mancano aspetti.
# Tipico: domanda chiede definizione+pratica, hits ritornano solo concept page.
# Reflector propone "come implementare X" come query addizionale.
_REFLECTOR_SYSTEM = """Sei un reflector di un sistema RAG agentico. Hai eseguito le
ricerche iniziali e ottenuto il seguente riepilogo di titoli/sezioni recuperate.

Domanda originale: {question}

Riepilogo evidenze recuperate:
{evidence_summary}

Compito: valuta se l'evidenza copre TUTTI gli aspetti della domanda originale.
Specialmente: se la domanda chiede definizione E procedura (o teoria E pratica,
o concetto E esempi), verifica che entrambi siano presenti nell'evidenza.

- Se SÌ (copertura adeguata): output {{"missing_aspects": [], "extra_queries": []}}.
- Se NO (aspetti scoperti): identifica al massimo 2 aspetti mancanti, e per
  ognuno proponi UNA sub_query specifica che li recupera.

Regole:
- ``extra_queries`` in italiano, forma interrogativa, atomiche.
- NON ripetere query già esplorate (le hai già nelle evidenze).
- Se l'evidenza è completa, ritorna liste vuote. Falso-positivo (ricerche
  extra non necessarie) costa latenza; falso-negativo (aspetto perso)
  costa accuratezza. Preferisci falso-positivo.

Output: SOLO JSON {{"missing_aspects": ["..."], "extra_queries": ["..."]}},
niente preambolo."""

# ---------------------------------------------------------------------------
# JSON parsing utilities
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(raw: str) -> str:
    cleaned = _FENCE_RE.sub("", raw or "").strip()
    first = cleaned.find("{")
    if first > 0:
        cleaned = cleaned[first:]
    return cleaned


def _parse_json_safe(raw: str, *, key: str) -> list[str]:
    """Estrae ``key`` come lista di string dal JSON. Tollera fence,
    preambolo. Ritorna lista vuota su errore."""
    cleaned = _strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.debug("[agentic] JSON parse failed for key=%s: %r", key, cleaned[:120])
        return []
    items = data.get(key) if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [str(x).strip() for x in items if isinstance(x, str) and x.strip()]


# ---------------------------------------------------------------------------
# Evidence summary helper
# ---------------------------------------------------------------------------


def _evidence_summary(hits: list[dict[str, Any]], *, max_lines: int = 12) -> str:
    """Riepilogo testuale degli hits per il reflector. Una riga per hit:
    titolo, page_type, doc_register, sezione."""
    if not hits:
        return "(nessuna evidenza recuperata)"
    lines: list[str] = []
    seen: set[str] = set()
    for h in hits:
        payload = h.get("payload") or {}
        doc_id = str(payload.get("document_id") or "")
        if doc_id in seen:
            continue
        seen.add(doc_id)
        title = payload.get("title") or doc_id
        page_type = payload.get("page_type") or "?"
        register = payload.get("doc_register") or "?"
        section = payload.get("section_heading") or ""
        section_part = f" — sezione «{section}»" if section else ""
        lines.append(
            f"- {title} (page_type={page_type}, registro={register}){section_part}"
        )
        if len(lines) >= max_lines:
            break
    return "\n".join(lines)


__all__ = [
    "_PLANNER_SYSTEM",
    "_REFLECTOR_SYSTEM",
    "_FENCE_RE",
    "_strip_fences",
    "_parse_json_safe",
    "_evidence_summary",
]

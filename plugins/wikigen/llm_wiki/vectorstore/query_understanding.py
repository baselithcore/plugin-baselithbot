"""Query understanding pre-retrieval: HyDE + decomposition.

Due tecniche opzionali (default OFF, costo LLM extra) che aumentano il
recall su domande complesse o lessicalmente distanti dal corpus:

- **HyDE** (Hypothetical Document Embeddings, Gao et al. 2022).
  L'LLM genera un *pseudo-documento* che ipoteticamente risponde alla
  query nel registro/lessico atteso del corpus. La pseudo-risposta è
  poi aggiunta alla lista delle query da embeddare → il vettore dense
  cattura concetti che la sola domanda non ha. Particolarmente utile
  quando l'utente chiede in linguaggio divulgativo contro un corpus
  in registro tecnico/contrattuale.
- **Decomposition**. L'LLM scompone una domanda multi-slot in 2-N
  sotto-domande indipendenti, ciascuna più focalizzata su un singolo
  ambito. Ogni sotto-domanda passa per il pipeline di retrieval
  separatamente e i risultati vengono uniti via RRF in
  :mod:`llm_wiki.vectorstore.core`.

Entrambe le funzioni sono **best-effort**: se l'LLM fallisce o restituisce
output non parsabile, ritornano il fallback identità (query originale).
Mai sollevano eccezioni — il retrieval prosegue anche senza l'arricchimento.

Costo (latenza tipica per un singolo step LLM):
- OpenAI gpt-4o-mini: 200-500 ms
- Ollama llama3.2:latest: 1-3 s
- Ollama qwen2.5:7b-instruct: 2-5 s

Default OFF: il guadagno di recall (10-25% su query complesse) raramente
giustifica il raddoppio della latenza chat. Abilita selettivamente in
deploy dove la copertura conta più del time-to-first-token.
"""

from __future__ import annotations

import json
import logging
import re

from llm_wiki.config import (
    HYDE_ENABLED,
    HYDE_MAX_TOKENS,
    QUERY_DECOMPOSITION_ENABLED,
    QUERY_DECOMPOSITION_MAX_SUBS,
)
from llm_wiki.utils.llm import generate

logger = logging.getLogger(__name__)


_HYDE_SYSTEM = (
    "Sei un assistente che, data una domanda, scrive un BREVE paragrafo "
    "ipotetico (massimo 4-6 frasi) che potrebbe comparire in un documento "
    "che risponda alla domanda. Usa il registro tecnico-professionale "
    "tipico del dominio implicato (giuridico, clinico, contrattuale, "
    "ecc.). Non aggiungere disclaimer, non rispondere all'utente — "
    "scrivi SOLO il paragrafo ipotetico, nessun preambolo."
)


def hyde_pseudo(query: str) -> str | None:
    """Genera uno pseudo-documento HyDE per la query. ``None`` se disabilitato
    o se l'LLM fallisce.

    Output sanitizzato: rimuove eventuali wrapper "Risposta:", code fence,
    bullet inutili. Tagliato a ``HYDE_MAX_TOKENS * 4`` caratteri (proxy
    grezzo: 1 token ≈ 4 char ITA).
    """
    if not HYDE_ENABLED or not query.strip():
        return None
    try:
        raw = generate(
            messages=[
                {"role": "system", "content": _HYDE_SYSTEM},
                {"role": "user", "content": query.strip()},
            ],
            use_cache=True,
        )
    except Exception as exc:
        logger.warning("[hyde] generation failed: %s", exc)
        return None
    cleaned = _strip_wrappers(raw)
    if not cleaned:
        return None
    cap = max(50, HYDE_MAX_TOKENS) * 4
    return cleaned[:cap]


_DECOMPOSE_SYSTEM = (
    "Sei un assistente che decompone domande complesse in sotto-domande "
    "indipendenti e atomiche. Ogni sotto-domanda copre UN solo aspetto "
    "della domanda originale e può essere risposta indipendentemente.\n\n"
    "Regole:\n"
    "- Se la domanda è già atomica (un solo aspetto), restituisci una "
    "lista con SOLO la domanda originale.\n"
    "- Massimo {max_subs} sotto-domande.\n"
    "- Le sotto-domande sono in italiano, in forma interrogativa.\n"
    '- Output: SOLO un oggetto JSON {{"sub_questions": [...]}}, niente preambolo.'
)


def decompose_query(query: str) -> list[str]:
    """Scompone la query in sotto-query atomiche.

    Returns:
        Lista non vuota. Se decomposition è disabilitata, fallisce, o la
        domanda è già atomica, ritorna ``[query]`` (caller lo tratta
        come no-op).
    """
    if not QUERY_DECOMPOSITION_ENABLED or not query.strip():
        return [query]
    system_msg = _DECOMPOSE_SYSTEM.format(max_subs=QUERY_DECOMPOSITION_MAX_SUBS)
    try:
        raw = generate(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": query.strip()},
            ],
            json_mode=True,
            use_cache=True,
        )
    except Exception as exc:
        logger.warning("[decompose] generation failed: %s", exc)
        return [query]
    subs = _extract_sub_questions(raw)
    if not subs:
        return [query]
    # Cap + dedup case-insensitive preservando ordine
    seen: set[str] = set()
    out: list[str] = []
    for s in subs[:QUERY_DECOMPOSITION_MAX_SUBS]:
        key = s.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(s.strip())
    if not out:
        return [query]
    # Garanzia minima: includi sempre l'originale, così il segnale
    # diretto della query utente non si perde dietro le riformulazioni.
    if query.strip().lower() not in {o.lower() for o in out}:
        out.insert(0, query.strip())
    return out


_FENCE_RE = re.compile(r"^```(?:json|markdown)?\s*|\s*```$", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)


def _strip_wrappers(text: str) -> str:
    """Rimuove fence, bullet leading, prefissi 'Risposta:' / 'Pseudo:'."""
    s = _FENCE_RE.sub("", text or "").strip()
    s = re.sub(r"^(risposta|pseudo[- ]?documento|paragrafo)\s*:\s*", "", s, flags=re.IGNORECASE)
    s = _BULLET_RE.sub("", s)
    return s.strip()


def _extract_sub_questions(raw: str) -> list[str]:
    """Estrae ``sub_questions`` dal JSON. Tollera fence + JSON malformato."""
    cleaned = _FENCE_RE.sub("", raw or "").strip()
    first = cleaned.find("{")
    if first > 0:
        cleaned = cleaned[first:]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    items = data.get("sub_questions") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [str(x) for x in items if isinstance(x, str) and x.strip()]

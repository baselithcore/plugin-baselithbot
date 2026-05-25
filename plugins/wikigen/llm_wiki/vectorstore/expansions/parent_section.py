"""Small-to-big retrieval: append sibling chunks within the same section."""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client.models import (  # type: ignore[import-not-found]
    FieldCondition,
    Filter,
    MatchValue,
)

from llm_wiki.config import COLLECTION_NAME
from llm_wiki.vectorstore.parallel import parallel_map

logger = logging.getLogger(__name__)


def expand_to_parent_section(
    hits: list[dict[str, Any]],
    *,
    max_extra: int | None = None,
    per_hit_cap: int | None = None,
) -> list[dict[str, Any]]:
    """Small-to-big retrieval: per ogni hit, allega sibling chunks della
    **stessa sezione** dello stesso documento.

    Motivazione: il retrieval matcha il singolo chunk semanticamente più
    vicino alla query, ma le sezioni di una pagina wiki (es. "## Casi d'uso"
    con 3 case study sotto) sono spesso unità logiche. Senza espansione, il
    LLM vede solo il chunk col titolo della sezione e perde gli esempi —
    o, peggio, inventa esempi parametrici per riempire il gap. Allegando i
    sibling restituiamo la sezione completa al modello, riducendo
    hallucination strutturali da decontestualizzazione.

    Strategia:
        1. Per ogni hit con ``section_heading`` non vuoto, scroll Qdrant
           filtrando ``document_id`` + ``section_heading``.
        2. Esclude i point id già presenti negli ``hits`` correnti.
        3. Sibling marcati ``via_parent_section=True`` con score 0.0
           (saranno integrati nel context — non competono sul ranking).
        4. Tetto globale ``max_extra``, tetto per hit ``per_hit_cap``.
        5. Output ordinato per ``(document_id, chunk_index)`` per
           preservare l'ordine narrativo del documento sorgente.

    Fallback-safe: errore Qdrant → ritorna ``hits`` invariato.
    """
    from llm_wiki.config import (
        PARENT_RETRIEVAL_ENABLED,
        PARENT_RETRIEVAL_MAX_EXTRA,
        PARENT_RETRIEVAL_PER_HIT_CAP,
    )

    if not PARENT_RETRIEVAL_ENABLED or not hits:
        return hits

    eff_max = max_extra if max_extra is not None else PARENT_RETRIEVAL_MAX_EXTRA
    eff_cap = per_hit_cap if per_hit_cap is not None else PARENT_RETRIEVAL_PER_HIT_CAP
    if eff_max <= 0 or eff_cap <= 0:
        return hits

    # Lazy lookup via package namespace so tests can monkeypatch
    # ``expansions.get_qdrant`` and intercept the Qdrant client.
    from llm_wiki.vectorstore import expansions as _pkg

    client = _pkg.get_qdrant()
    if not client:
        return hits

    seen_ids: set[str] = set()
    for h in hits:
        pid = h.get("point_id") or h.get("id")
        if pid is not None:
            seen_ids.add(str(pid))

    explored: set[tuple[str, str]] = set()
    tasks: list[tuple[str, str]] = []
    for hit in hits:
        if hit.get("hierarchical_collapsed"):
            continue
        payload = hit.get("payload") or {}
        doc_id = payload.get("document_id")
        section_heading = (
            payload.get("parent_section_heading")
            or payload.get("section_heading")
            or ""
        ).strip()
        if not doc_id or not section_heading:
            continue
        key = (str(doc_id), section_heading)
        if key in explored:
            continue
        explored.add(key)
        tasks.append(key)

    if not tasks:
        return hits

    def _scroll(task: tuple[str, str]) -> tuple[tuple[str, str], list[Any]]:
        doc_id, section_heading = task
        try:
            results, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id", match=MatchValue(value=doc_id)
                        ),
                    ],
                    should=[
                        FieldCondition(
                            key="section_heading",
                            match=MatchValue(value=section_heading),
                        ),
                        FieldCondition(
                            key="parent_section_heading",
                            match=MatchValue(value=section_heading),
                        ),
                    ],
                ),
                limit=eff_cap + 5,
                with_payload=True,
            )
            return task, list(results)
        except Exception:
            return task, []

    scroll_results = parallel_map(_scroll, tasks)

    extras: list[dict[str, Any]] = []
    for (_doc_id, section_heading), results in scroll_results:
        if len(extras) >= eff_max:
            break
        local_added = 0
        for pt in results:
            if local_added >= eff_cap or len(extras) >= eff_max:
                break
            pid = str(pt.id)
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            extras.append(
                {
                    "id": pid,
                    "point_id": pid,
                    "payload": dict(pt.payload or {}),
                    "score": 0.0,
                    "via_parent_section": True,
                    "parent_section_heading": section_heading,
                }
            )
            local_added += 1

    if not extras:
        return hits

    extras.sort(
        key=lambda h: (
            str((h.get("payload") or {}).get("document_id") or ""),
            int((h.get("payload") or {}).get("chunk_index") or 0),
        )
    )
    logger.info(
        "[parent-section] +%d sibling chunks da %d sezioni", len(extras), len(explored)
    )
    return hits + extras

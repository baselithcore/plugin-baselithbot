"""Follow-the-link retrieval (cited-article expansion within same doc)."""

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


def expand_with_rinvii(
    hits: list[dict[str, Any]],
    *,
    max_extra: int = 5,
    per_hit_cap: int = 2,
) -> list[dict[str, Any]]:
    """Follow-the-link retrieval: espande gli hits con chunk rinviati.

    Per ogni top-k hit, legge `articoli_citati` nel payload. Per ogni articolo
    citato, fa scroll Qdrant su chunk dello **stesso documento** che hanno lo
    stesso articolo nel campo `articoli_citati`. I chunk aggiuntivi sono
    marcati `via_rinvio: true` nel dict hit e appesi in coda alla lista, così
    il reranker/LLM può integrarli in risposta.

    Scelte:
    - Scope = stesso `document_id`. Follow cross-documento è rumoroso; meglio
      rinviare alla pagina destinazione nella risposta.
    - `max_extra` tetto globale, `per_hit_cap` tetto per singolo hit top-k.
    - Non distinguiamo rinvio vs definizione nel chunk sorgente: accettiamo
      over-retrieval, il reranker + SYSTEM_PROMPT filtrano.
    - Fallback silenzioso: in caso di errore Qdrant, ritorna `hits` invariato.
    """
    if not hits or max_extra <= 0:
        return hits

    # Lazy lookup via package namespace so tests can
    # ``monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", …)``.
    from llm_wiki.vectorstore import expansions as _pkg

    client = _pkg.get_qdrant()
    if not client:
        return hits

    seen_ids: set[Any] = set()
    for h in hits:
        pid = h.get("point_id") or h.get("id")
        if pid is not None:
            seen_ids.add(str(pid))

    followed: set[tuple[str, str]] = set()
    tasks: list[tuple[str, str]] = []
    for hit in hits:
        if len(tasks) >= max_extra * 2:
            break
        payload = hit.get("payload") or {}
        doc_id = payload.get("document_id")
        if not doc_id:
            continue
        articles = payload.get("articoli_citati") or []
        if not isinstance(articles, list) or not articles:
            continue
        local_planned = 0
        for article in articles:
            if local_planned >= per_hit_cap:
                break
            key = (str(doc_id), str(article))
            if key in followed:
                continue
            followed.add(key)
            tasks.append(key)
            local_planned += 1

    if not tasks:
        return hits

    def _scroll(task: tuple[str, str]) -> tuple[tuple[str, str], list[Any]]:
        doc_id, article = task
        try:
            results, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="document_id", match=MatchValue(value=doc_id)),
                        FieldCondition(key="articoli_citati", match=MatchValue(value=article)),
                    ]
                ),
                limit=2,
                with_payload=True,
            )
            return task, list(results)
        except Exception:
            return task, []

    scroll_results = parallel_map(_scroll, tasks)

    extras: list[dict[str, Any]] = []
    for (_doc_id, article), results in scroll_results:
        if len(extras) >= max_extra:
            break
        for pt in results:
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
                    "via_rinvio": True,
                    "rinvio_articolo": article,
                }
            )
            if len(extras) >= max_extra:
                break

    if extras:
        logger.info("[rinvii] follow-the-link: +%d chunk aggiuntivi", len(extras))
    return hits + extras

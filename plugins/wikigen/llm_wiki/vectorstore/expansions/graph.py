"""Graph-backed expansions: light wikilink annotate + full entity-graph fan-out."""

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


def expand_with_graph(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Allega contesto grafo (vicini via wikilinks) se graph attivo.

    Modalità *light*: annota ogni hit con la lista di pagine adiacenti via
    ``LINKS_TO`` / ``MENTIONED_IN``. Non aggiunge nuovi hit. Per espansione
    full (graphify-style entity-driven), vedi :func:`expand_with_entity_graph`.
    """
    try:
        from llm_wiki.graphdb.core import get_graph_db

        graph = get_graph_db()
    except Exception:
        return hits

    if not graph or not graph.is_enabled():
        return hits

    for hit in hits:
        doc_id = hit.get("payload", {}).get("document_id")
        if not doc_id:
            continue
        try:
            neighbors = graph.query(
                "MATCH (p:Page {id: $id})-[r:LINKS_TO|MENTIONED_IN]-(n:Page) "
                "RETURN type(r) AS rel, n.id AS target, n.title AS title LIMIT 6",
                {"id": doc_id},
            )
            if neighbors:
                hit.setdefault("payload", {})["graph_context"] = neighbors
        except Exception:
            continue

    return hits


def expand_with_entity_graph(
    hits: list[dict[str, Any]],
    *,
    hops: int | None = None,
    max_extra: int | None = None,
    confidence_min: float | None = None,
    query_entities: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Graphify-style RAG expansion via entity neighborhood.

    Algoritmo:
        1. Da ogni hit top-K → ``document_id`` → entità menzionate
           (filtrate per ``confidence ≥ confidence_min``).
        2. Per ogni entità, espandi a k-hop tramite edge :R (relazioni
           pack-declared) → entità vicine.
        3. Per ogni entità vicina, recupera pagine che la menzionano
           (Page-MENTIONS-Entity).
        4. Per ogni nuova pagina (≠ top-K), scroll Qdrant del chunk che
           menziona davvero un'entità candidate (filtro
           ``entities_mentioned`` se presente nel payload — Wave A);
           fallback al primo chunk del doc per backward-compat.

    Wave B (cross-chapter linking + comparative deep):
        - **Overlap boost** (``via_graph_overlap``): chunk del doc esteso
          che menziona ≥ 2 entità seed riceve score 0.05 × overlap, signal
          per il reranker che è un match comparativo.
        - **Surface entità + tier** (graphify principle #6 "why matched"):
          ogni hit aggiunge ``via_graph_entity`` (canonical id), ``
          via_graph_entity_name``, ``via_graph_tier``
          (EXTRACTED/INFERRED/AMBIGUOUS) per esplicabilità.
        - **Comparative shortest-path** (graphify principle #4): quando
          ``query_entities`` contiene ≥ 2 entità identificate nella
          domanda, calcola ``shortest_path`` fra coppie e include i doc
          delle entità lungo il path. Boost 0.10 per chunk che
          menzionano un'entità del path.

    Gating:
        - ``GRAPH_RAG_ENABLED`` env (default False). Senza flag = no-op.
        - ``hops`` ∈ [1,3], default ``GRAPH_RAG_HOPS``.
        - ``max_extra`` cap pagine aggiuntive (default
          ``GRAPH_RAG_MAX_EXTRA_PAGES``).
        - ``confidence_min`` soglia su mention/relation (default
          ``GRAPH_CONFIDENCE_MIN``).

    Fallback-safe: qualunque errore (graph offline, Cypher fallito,
    networkx mancante) → ritorna ``hits`` invariato.
    """
    from llm_wiki.config import (
        GRAPH_CONFIDENCE_MIN,
        GRAPH_RAG_ENABLED,
        GRAPH_RAG_HOPS,
        GRAPH_RAG_MAX_EXTRA_PAGES,
    )

    if not GRAPH_RAG_ENABLED or not hits:
        return hits

    eff_hops = max(1, min(3, hops if hops is not None else GRAPH_RAG_HOPS))
    eff_extra = max_extra if max_extra is not None else GRAPH_RAG_MAX_EXTRA_PAGES
    eff_conf = confidence_min if confidence_min is not None else GRAPH_CONFIDENCE_MIN
    if eff_extra <= 0:
        return hits

    try:
        from llm_wiki.graphdb.store import get_kg_store

        store = get_kg_store()
    except Exception:
        return hits
    if not store.enabled:
        return hits

    seed_doc_ids: list[str] = []
    seen_docs: set[str] = set()
    for h in hits:
        did = (h.get("payload") or {}).get("document_id")
        if did and did not in seen_docs:
            seen_docs.add(did)
            seed_doc_ids.append(did)
    if not seed_doc_ids:
        return hits

    # Step 1: entità menzionate dai seed.
    seed_entity_ids: list[str] = []
    try:
        cypher = (
            "MATCH (p:Page)-[m:MENTIONS]->(e:Entity) "
            "WHERE p.id IN $ids AND m.confidence >= $conf "
            "RETURN DISTINCT e.id LIMIT 50"
        )
        rows = store._rows(  # noqa: SLF001
            store._g.query(cypher, {"ids": seed_doc_ids, "conf": eff_conf})  # noqa: SLF001
        )
        for row in rows:
            if not row:
                continue
            eid = row[0]
            if isinstance(eid, list | tuple) and len(eid) >= 2:
                eid = eid[1]
            if isinstance(eid, str) and eid:
                seed_entity_ids.append(eid)
    except Exception:
        return hits

    if not seed_entity_ids:
        return hits

    # Step 2: k-hop neighbors of seed entities (deduped).
    neighbor_ids: set[str] = set()
    for eid in seed_entity_ids[:20]:
        try:
            for n in store.neighbors(eid, hops=eff_hops, confidence_min=eff_conf, limit=10):
                neighbor_ids.add(n.id)
        except Exception:
            continue
    candidate_entity_ids = set(seed_entity_ids) | neighbor_ids

    # Wave B3: shortest-path comparative ("query as traversal"). Top 3 pairs.
    path_entity_ids: set[str] = set()
    if query_entities and len(query_entities) >= 2:
        qe = [e for e in query_entities if e]
        pairs = [(qe[i], qe[j]) for i in range(len(qe)) for j in range(i + 1, len(qe))][:3]
        for src, dst in pairs:
            try:
                path = store.shortest_path(src, dst, max_hops=4)
            except Exception:
                continue
            for eid in path:
                if eid:
                    path_entity_ids.add(eid)
        if path_entity_ids:
            logger.info(
                "[graph.rag] comparative path: %d entità su %d coppie",
                len(path_entity_ids),
                len(pairs),
            )
            candidate_entity_ids |= path_entity_ids

    # Step 3: pages mentioning candidate entities, excluding the seeds.
    candidate_docs = store.pages_for_entities(
        candidate_entity_ids,
        confidence_min=eff_conf,
        limit=eff_extra * 4,
    )
    new_doc_ids = [d for d in candidate_docs if d not in seen_docs][:eff_extra]
    if not new_doc_ids:
        return hits

    # Step 4: chunk-level entity-aware fetch (Wave A) + fallback first-chunk.
    from llm_wiki.vectorstore import expansions as _pkg

    client = _pkg.get_qdrant()
    if not client:
        return hits

    candidate_list = list(candidate_entity_ids)

    def _scroll(did: str) -> list[Any]:
        try:
            if candidate_list:
                results, _ = client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="document_id", match=MatchValue(value=did))],
                        should=[
                            FieldCondition(key="entities_mentioned", match=MatchValue(value=eid))
                            for eid in candidate_list[:25]
                        ],
                    ),
                    limit=2,
                    with_payload=True,
                )
                if results:
                    return list(results)
            results, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=did))]
                ),
                limit=1,
                with_payload=True,
            )
            return list(results)
        except Exception:
            return []

    per_doc_results = parallel_map(_scroll, new_doc_ids)

    # Entity meta index (id → name) for "why matched" surface.
    entity_meta: dict[str, tuple[str, str, float]] = {}
    for eid in candidate_list[:50]:
        try:
            ent = store.get_entity(eid)
        except Exception:
            ent = None
        if ent:
            entity_meta[eid] = (ent.name, "", 0.0)

    extras: list[dict[str, Any]] = []
    for results in per_doc_results:
        for pt in results:
            payload = dict(pt.payload or {})
            chunk_entities = payload.get("entities_mentioned") or []
            tiers_payload = payload.get("entity_tiers") or {}
            confs_payload = payload.get("entity_confidences") or {}
            overlap_ids: list[str] = []
            for cid in chunk_entities:
                if cid in candidate_entity_ids:
                    overlap_ids.append(cid)
            overlap_n = len(overlap_ids)
            primary: str | None = None
            for cid in overlap_ids:
                if cid in path_entity_ids:
                    primary = cid
                    break
            if not primary:
                for cid in overlap_ids:
                    if cid in seed_entity_ids:
                        primary = cid
                        break
            if not primary and overlap_ids:
                primary = overlap_ids[0]
            score = 0.0
            if overlap_n >= 2:
                score += 0.05 * min(overlap_n, 4)
            if primary and primary in path_entity_ids:
                score += 0.10
            extra: dict[str, Any] = {
                "id": str(pt.id),
                "point_id": str(pt.id),
                "payload": payload,
                "score": score,
                "graph_expanded": True,
                "via_graph_overlap": overlap_n,
            }
            if primary:
                extra["via_graph_entity"] = primary
                name, _, _ = entity_meta.get(primary, ("", "", 0.0))
                if name:
                    extra["via_graph_entity_name"] = name
                tier_val = ""
                if isinstance(tiers_payload, dict):
                    tier_val = str(tiers_payload.get(primary) or "")
                if tier_val:
                    extra["via_graph_tier"] = tier_val
                conf_val = 0.0
                if isinstance(confs_payload, dict):
                    try:
                        conf_val = float(confs_payload.get(primary) or 0.0)
                    except Exception:
                        conf_val = 0.0
                if conf_val:
                    extra["via_graph_confidence"] = conf_val
                if primary in path_entity_ids:
                    extra["via_graph_comparative_path"] = True
            extras.append(extra)

    if extras:
        comparative_n = sum(1 for e in extras if e.get("via_graph_comparative_path"))
        logger.info(
            "[graph.rag] expansion: +%d pages via entity graph (comparative=%d, path_entities=%d)",
            len(extras),
            comparative_n,
            len(path_entity_ids),
        )
    return hits + extras

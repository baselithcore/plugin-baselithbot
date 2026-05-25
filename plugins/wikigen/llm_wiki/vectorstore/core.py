"""Pipeline di retrieval pubblica.

Orchestrazione a 6 stadi (query expansion → hybrid → fusion → rerank →
graph → rinvii → mix-edizioni audit). L'indicizzazione vive in
:mod:`llm_wiki.vectorstore.indexer`; le espansioni di hits in
:mod:`llm_wiki.vectorstore.expansions`. Re-esportiamo le entry-point
storiche per non rompere callers esterni.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from qdrant_client.models import (  # type: ignore[import-not-found]
    FieldCondition,
    Filter,
    MatchValue,
)

from llm_wiki.config import RETRIEVAL_TOP_K
from llm_wiki.vectorstore.expansions import (
    annotate_mix_edizioni,
    expand_to_parent_section,
    expand_with_rinvii,
    merge_hits_rrf,
)
from llm_wiki.vectorstore.expansions import (
    expand_with_entity_graph as _expand_with_entity_graph,
)
from llm_wiki.vectorstore.expansions import (
    expand_with_graph as _expand_with_graph,
)
from llm_wiki.vectorstore.hybrid import hybrid_search
from llm_wiki.vectorstore.indexer import index_page, index_pages_batched
from llm_wiki.vectorstore.mmr import diversify as mmr_diversify
from llm_wiki.vectorstore.parallel import parallel_map
from llm_wiki.vectorstore.query_classifier import infer as infer_query_filter
from llm_wiki.vectorstore.query_expansion import expand as expand_query
from llm_wiki.vectorstore.query_understanding import decompose_query, hyde_pseudo
from llm_wiki.vectorstore.reranker import prefetch_limit, rerank

# Backwards-compatibility re-exports — callers historically import these
# from ``llm_wiki.vectorstore.core``.
__all__ = [
    "index_page",
    "index_pages_batched",
    "search",
    "search_async",
]

logger = logging.getLogger(__name__)


def search(
    query: str,
    *,
    limit: int = RETRIEVAL_TOP_K,
    page_type: str | None = None,
    expand_with_graph: bool = False,
    rerank_enabled: bool = True,
    expand_query_variants: int = 4,
    prefer_vigente: bool = True,
    follow_rinvii: bool = True,
) -> list[dict[str, Any]]:
    """Pipeline di retrieval a 4 stadi (sync, CPU/GPU-bound).

    1. **Query expansion** domain-specific (sinonimi assicurativi/legali
       italiani) → N query varianti incluso l'originale.
    2. **Hybrid retrieval** (dense + sparse ± ColBERT) per ogni variante
       → `limit * RERANKER_INPUT_MULT` candidati ciascuna → fusione RRF.
    3. **Cross-encoder rerank** → top `limit` (se reranker attivo).
       Il reranker vede la query ORIGINALE (non espansa) per massimizzare
       il segnale dell'intento utente.
    4. **Graph expansion** opzionale (vicini via wikilinks).

    Args:
        query: domanda utente in linguaggio naturale.
        limit: numero di hit finali da restituire.
        page_type: filtro per tipo di pagina wiki (source/entity/concept/topic/synthesis).
        expand_with_graph: abilita graph traversal su wikilinks.
        rerank_enabled: abilita cross-encoder rerank.
        expand_query_variants: max varianti di query da generare (default 4).
            Metti a 0 per disabilitare l'espansione.
        prefer_vigente: se True (default), filtra in retrieval le fonti con
            `stato` o `edizione-stato` esplicitamente `superata`/`abrogata`.
            Fonti senza campo di stato vengono incluse (modalità permissiva:
            molte pagine concept non hanno versioning). Post-retrieval, gli
            hit vengono annotati con `edizione_audit` che segnala se il set
            di risultati mescola edizioni diverse — l'agente RAG segnala il
            mix all'utente.

    NB: chiamalo via `await asyncio.to_thread(search, ...)` in handler async
    (FastAPI) per non bloccare l'event loop — vedi `search_async()`.
    """
    t0 = time.perf_counter()

    must: list[Any] = []
    must_not: list[Any] = []
    if page_type:
        must.append(FieldCondition(key="page_type", match=MatchValue(value=page_type)))
    if prefer_vigente:
        # Escludi hit con stato esplicitamente superato/abrogato. Fonti senza
        # campo di stato (la maggior parte delle pagine concept) restano incluse.
        for state_key in ("stato", "edizione-stato"):
            for dead_state in ("superata", "abrogata"):
                must_not.append(
                    FieldCondition(key=state_key, match=MatchValue(value=dead_state))
                )
    qfilter: Filter | None = None
    if must or must_not:
        qfilter = Filter(must=must or None, must_not=must_not or None)

    # Stage 0: decomposition (no-op se disabilitato → [query])
    sub_queries = decompose_query(query)
    if len(sub_queries) > 1:
        logger.info("[decompose] '%s' → %d sotto-domande", query[:40], len(sub_queries))

    # Stage 0.5: HyDE pseudo-doc per ogni sotto-query (no-op se disabilitato)
    hyde_extras: list[str] = []
    for sq in sub_queries:
        pseudo = hyde_pseudo(sq)
        if pseudo:
            hyde_extras.append(pseudo)
    if hyde_extras:
        logger.info("[hyde] aggiunti %d pseudo-doc al pool query", len(hyde_extras))

    # Stage 1: query expansion (domain-specific) per ogni sotto-query
    queries: list[str] = []
    seen_q: set[str] = set()
    for sq in [*sub_queries, *hyde_extras]:
        variants = (
            expand_query(sq, max_variants=expand_query_variants)
            if expand_query_variants > 0
            else [sq]
        )
        for v in variants:
            key = v.strip().lower()
            if key and key not in seen_q:
                seen_q.add(key)
                queries.append(v)
    if len(queries) > 1:
        logger.info(
            "[query-expansion] '%s' → %d varianti totali", query[:40], len(queries)
        )

    # Stage 1.5: query→page_type inference (heuristic, zero LLM call).
    # Quando il caller non ha già passato un page_type esplicito e l'env è
    # ON, classifico la query originale per archetipo lessicale
    # (definitional/example/procedural). Se inferisco un page_type valido
    # sul pack attivo, aggiungo una variante filtrata al pool RRF.
    # Effetto: SOFT boost dei chunk del page_type pertinente (la variante
    # filtrata mette in alto i chunk matched), SENZA escludere match in
    # altri page_type (la variante unfiltered preserva il recall).
    inferred_qfilter: Filter | None = None
    if not page_type:
        from llm_wiki.config import (
            QUERY_FILTER_INFERENCE_ENABLED,
            QUERY_FILTER_INFERENCE_STRICT_ONLY,
        )

        if QUERY_FILTER_INFERENCE_ENABLED:
            try:
                from llm_wiki.domain.registry import get_pack

                pack_for_infer = get_pack()
            except Exception:
                pack_for_infer = None
            inf = infer_query_filter(query, pack_for_infer)
            apply_inferred = inf.page_type_id and (
                inf.confidence == "strict" or not QUERY_FILTER_INFERENCE_STRICT_ONLY
            )
            if apply_inferred:
                logger.info(
                    "[query-classifier] '%s' → %s (page_type=%s, conf=%s)",
                    query[:40],
                    inf.archetype,
                    inf.page_type_id,
                    inf.confidence,
                )
                assert inf.page_type_id is not None
                inferred_must = list(must) + [
                    FieldCondition(
                        key="page_type", match=MatchValue(value=inf.page_type_id)
                    )
                ]
                inferred_qfilter = Filter(
                    must=inferred_must or None, must_not=must_not or None
                )
            elif inf.archetype != "unknown" and inf.confidence != "none":
                # Diagnostica: archetype riconosciuto ma nessun page_type del
                # pack matcha (mappa heuristica del classifier non copre il
                # vocabolario del pack). Senza log, tuning blindo.
                logger.info(
                    "[query-classifier] '%s' archetype=%s conf=%s — nessun page_type del pack matcha (no-op)",
                    query[:40],
                    inf.archetype,
                    inf.confidence,
                )

    # Stage 2: hybrid retrieval per ciascuna variante + fusione RRF.
    # Parallelizzato via thread pool in modalità server/gRPC: ogni
    # ``hybrid_search`` è una chiamata Qdrant indipendente (~50-200ms cad.) →
    # N×serial diventano O(1) wall-clock sotto i limiti del pool. In modalità
    # embedded il client non è thread-safe → fallback serial trasparente.
    stage_limit = prefetch_limit(limit) if rerank_enabled else limit
    search_tasks: list[tuple[str, Filter | None]] = []
    for q in queries:
        search_tasks.append((q, qfilter))
        if inferred_qfilter is not None:
            # Variante filtrata sulla query originale: stesso embedding, ma
            # restituisce solo chunk del page_type inferito. Posta accanto
            # → ranking RRF la usa come boost selettivo dei match pertinenti.
            search_tasks.append((q, inferred_qfilter))

    def _run_one(task: tuple[str, Filter | None]) -> list[dict[str, Any]]:
        q_text, f = task
        try:
            return hybrid_search(q_text, limit=stage_limit, qfilter=f)
        except Exception as exc:
            # Fallback-safe: un branch fallito non deve buttare giù la query.
            logger.warning("[search] variante '%s…' fallita (%s)", q_text[:40], exc)
            return []

    per_query_hits = parallel_map(_run_one, search_tasks)
    hits = merge_hits_rrf(per_query_hits, limit=stage_limit)
    t_retr = time.perf_counter()

    # Stage 3: cross-encoder rerank → top_k (con la query ORIGINALE)
    if rerank_enabled and hits:
        # Tieni più candidati del top_k finale: MMR ne seleziona limit
        # diversificati. Con MMR off coincide con il behavior precedente.
        hits = rerank(query, hits, top_k=max(limit * 2, limit))
    else:
        hits = hits[: max(limit * 2, limit)]
    t_rr = time.perf_counter()

    # Stage 3b: MMR diversification → top_k finali. No-op se MMR_ENABLED=false
    # o se len(hits) <= limit (niente da diversificare).
    hits = mmr_diversify(hits, top_k=limit)
    t_mmr = time.perf_counter()

    # Stage 3c-pre: collapse hierarchical (child → parent) PRIMA dell'espansione
    # parent-section. Senza riordino, l'espansione parent-section recupera i
    # sibling-chunk per ogni child, duplicandoli con il contenuto già denormalizzato
    # in ``parent_text``. Collassando prima, l'espansione vede UN hit per parent
    # → niente duplicazione, niente inflate del context window. Idempotente:
    # ``rag_context.build_context`` mantiene il safety-net collapse, no-op se già
    # collassato qui.
    from llm_wiki.config import HIERARCHICAL_RETRIEVAL_ENABLED

    if HIERARCHICAL_RETRIEVAL_ENABLED and hits:
        from llm_wiki.vectorstore.hierarchical import collapse_hits_by_parent

        hits = collapse_hits_by_parent(hits)

    # Stage 3c: parent-section retrieval (small-to-big).
    # Per ogni top-K hit, allega sibling chunks della stessa sezione del
    # documento. Riduce hallucination da decontestualizzazione (es. matching
    # del solo titolo di sezione senza gli esempi sottostanti). Sibling
    # entrano dopo MMR per non gonfiare il pool prima della diversificazione
    # e prima delle espansioni cross-doc (graph + rinvii) per dare priorità
    # alla coesione intra-doc. Hit con ``hierarchical_collapsed=True`` sono
    # skippati dall'espansione (il parent_text già contiene la sezione).
    hits = expand_to_parent_section(hits)

    # Stage 4: graph expansion (wikilinks annotation + graphify-style
    # entity-driven page expansion). The first decorates existing hits with
    # neighbor pages; the second appends NEW hits for pages reachable via
    # entity neighborhood. Both gated independently (`expand_with_graph`
    # for annotation, `GRAPH_RAG_ENABLED` env for entity expansion).
    if expand_with_graph:
        hits = _expand_with_graph(hits)

    # Identify entità citate dalla query: pilota shortest-path boost
    # comparativo dentro expand_with_entity_graph. Skip se archetype non
    # è comparative — riduce LLM-time cost del lookup (substring scan su
    # entity table) ai casi dove serve davvero.
    query_entity_ids: list[str] = []
    archetype_for_log = "n/a"
    try:
        from llm_wiki.vectorstore.query_classifier import (
            detect_archetype,
            spot_entities_in_query,
        )

        arche, _conf, _matched = detect_archetype(query)
        archetype_for_log = arche
        if arche == "comparative":
            query_entity_ids = spot_entities_in_query(query)
            if query_entity_ids:
                logger.info(
                    "[graph.rag] comparative query: %d entità identificate (%s)",
                    len(query_entity_ids),
                    archetype_for_log,
                )
    except Exception:
        # Best-effort: spotting fail → niente boost, ma niente blocco.
        query_entity_ids = []

    hits = _expand_with_entity_graph(hits, query_entities=query_entity_ids or None)

    # Stage 5: follow-the-link retrieval (rinvii interni ad articoli).
    # Dopo rerank, perché il reranker lavora meglio su hits pulite e i chunk
    # "via_rinvio" non devono competere con la query utente sul ranking.
    if follow_rinvii:
        hits = expand_with_rinvii(hits)

    # Stage 6: annotazione edizione_audit (segnala mix di versioni all'agente).
    # Passiamo `prefer_vigente_applied` per distinguere il mix legittimo
    # (vigenti distinti dopo il filtro retrieval) dal mix sospetto.
    hits = annotate_mix_edizioni(hits, prefer_vigente_applied=prefer_vigente)
    t_end = time.perf_counter()

    logger.info(
        "[perf] search '%s…': %d hits · variants=%d retrieve=%.2fs rerank=%.2fs mmr=%.2fs graph=%.2fs total=%.2fs",
        query[:40],
        len(hits),
        len(queries),
        t_retr - t0,
        t_rr - t_retr,
        t_mmr - t_rr,
        t_end - t_mmr,
        t_end - t0,
    )
    return hits


async def search_async(
    query: str,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Versione async-safe: offload CPU/GPU work su thread pool.

    Usa questa in contesti FastAPI / asyncio per non bloccare l'event loop
    durante embedding query + rerank predict (entrambe ~100-500ms su GPU).
    """
    return await asyncio.to_thread(search, query, **kwargs)

"""Chunk-level entity tagging (cross-chapter linking via Knowledge Graph).

Materializza il principio graphify "wiki-as-knowledge" a granularità
chunk: i chunk vettoriali ricevono il signal entity-level
(``entities_mentioned`` + ``entity_tiers``) propagato dal KG store. Senza
questo passaggio, il KG resta confinato al livello pagina e l'espansione
``expand_with_entity_graph`` non sa quali chunk DI UN DOC specifico
parlano davvero di un'entità — fetch del primo chunk casuale.

Coerenza con graphify
---------------------
- **Confidence tiers preservati** (principle #2): il tier
  EXTRACTED/INFERRED/AMBIGUOUS del MENTIONS edge viaggia fino al payload
  del singolo chunk; il rag_context può surface al modello "why matched"
  con tier esplicito.
- **No LLM extra** (principle: pipeline efficiente): zero LLM call. Il
  tagging riusa la pagina già processata dal post-write KG extractor +
  un substring match deterministico (entity name + aliases).
- **Deduplicazione canonica** (principle: aliases → canonical id): la
  match si basa su ``entity name`` + ``aliases`` ma il payload conserva
  solo ``canonical_entity_id`` — un'entità con 3 surface form produce
  UN tag, non tre.
- **Best-effort, idempotente**: qualunque errore (KG offline, Qdrant
  irraggiungibile) → no-op, niente eccezioni ai caller. Il re-run
  sovrascrive in-place via ``set_payload`` (no re-embed, no reindex).

Trigger
-------
Chiamato da ``llm_wiki.wiki.ingest`` dopo il batch di indicizzazione,
gated da ``GRAPH_CHUNK_ENTITY_TAGGING_ENABLED`` (default OFF) +
``GRAPH_EXTRACT_ENABLED`` + KG store enabled. Saltato in setup mode o
quando il KG layer non è installato.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def _make_matcher(surface_forms: list[str]) -> re.Pattern[str] | None:
    """Compila un regex case-insensitive che matcha una delle ``surface_forms``
    come token completo (word boundary). Ritorna ``None`` quando l'input è
    vuoto o tutto whitespace.

    Le surface form sono escapate (caratteri regex) e ordinate per lunghezza
    decrescente in modo che "Unipol Assicurazioni" matchi prima di
    "Unipol" quando entrambi sono presenti — evita doppio tag della
    sub-stringa.
    """
    cleaned: list[str] = []
    seen: set[str] = set()
    for sf in surface_forms:
        s = (sf or "").strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(re.escape(s))
    if not cleaned:
        return None
    cleaned.sort(key=len, reverse=True)
    pattern = r"(?<!\w)(?:" + "|".join(cleaned) + r")(?!\w)"
    return re.compile(pattern, re.IGNORECASE)


def tag_chunks_for_document(document_id: str) -> int:
    """Aggiorna i payload Qdrant del documento con ``entities_mentioned``
    + ``entity_tiers``. Ritorna il numero di chunk taggati.

    Algoritmo:
        1. Query KG: entità menzionate dalla pagina (incluse aliases e tier).
        2. Scroll Qdrant: tutti i chunk del ``document_id``.
        3. Per ogni chunk, regex match entity name + aliases sul ``raw_text``.
        4. Payload merge via ``set_payload`` (no re-embed, no reindex).

    Idempotente: re-esecuzione sovrascrive i tag con il KG corrente.

    Gated all'ingresso da ``GRAPH_CHUNK_ENTITY_TAGGING_ENABLED``. Qualunque
    errore upstream è loggato e swallowed (best-effort).
    """
    from llm_wiki.config import (
        COLLECTION_NAME,
        GRAPH_CHUNK_ENTITY_TAGGING_ENABLED,
        GRAPH_EXTRACT_ENABLED,
    )

    if not GRAPH_CHUNK_ENTITY_TAGGING_ENABLED or not GRAPH_EXTRACT_ENABLED:
        return 0
    if not document_id:
        return 0

    try:
        from qdrant_client.models import (  # type: ignore[import-not-found]
            FieldCondition,
            Filter,
            MatchValue,
        )

        from llm_wiki.graphdb.store import get_kg_store
        from llm_wiki.vectorstore.qdrant_ops import get_qdrant
    except Exception as exc:
        logger.debug("[graph.chunk-tag] deps not available: %s", exc)
        return 0

    store = get_kg_store()
    if not store.enabled:
        return 0
    client = get_qdrant()
    if not client:
        return 0

    entities = store.entities_for_page(document_id)
    if not entities:
        return 0

    # Costruisco una surface→canonical_id map e un matcher unico.
    surface_to_id: dict[str, str] = {}
    id_to_tier: dict[str, str] = {}
    id_to_conf: dict[str, float] = {}
    all_forms: list[str] = []
    for ent, conf, tier in entities:
        forms = [ent.name, *ent.aliases]
        for sf in forms:
            key = (sf or "").strip().lower()
            if not key:
                continue
            # Preferisco mantenere la PRIMA occorrenza (entity con confidence
            # più alta — entities_for_page le restituisce ORDER BY conf DESC).
            surface_to_id.setdefault(key, ent.id)
            all_forms.append(sf)
        # Tier/confidence indicizzati per entity_id canonico.
        if ent.id not in id_to_tier or conf > id_to_conf.get(ent.id, -1.0):
            id_to_tier[ent.id] = tier
            id_to_conf[ent.id] = conf

    matcher = _make_matcher(all_forms)
    if matcher is None:
        return 0

    try:
        scroll_filter = Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        )
        # Page tipica = 5-50 chunk; limit alto basta una pass.
        results, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=500,
            with_payload=True,
        )
    except Exception as exc:
        logger.debug("[graph.chunk-tag] scroll failed for %s: %s", document_id, exc)
        return 0

    tagged = 0
    for pt in results:
        payload = dict(pt.payload or {})
        text = str(payload.get("raw_text") or payload.get("text") or "")
        if not text:
            continue
        matches = matcher.findall(text)
        if not matches:
            continue
        # Dedup canonical id (più surface form → un id solo).
        mentioned: list[str] = []
        seen_ids: set[str] = set()
        for surface in matches:
            cid = surface_to_id.get(surface.strip().lower())
            if not cid or cid in seen_ids:
                continue
            seen_ids.add(cid)
            mentioned.append(cid)
        if not mentioned:
            continue
        # Tier/confidence ristretti agli id matched (payload-light).
        tiers = {cid: id_to_tier.get(cid, "") for cid in mentioned}
        confs = {cid: id_to_conf.get(cid, 0.0) for cid in mentioned}
        try:
            client.set_payload(
                collection_name=COLLECTION_NAME,
                payload={
                    "entities_mentioned": mentioned,
                    "entity_tiers": tiers,
                    "entity_confidences": confs,
                },
                points=[pt.id],
            )
            tagged += 1
        except Exception as exc:
            logger.debug("[graph.chunk-tag] set_payload failed for %s: %s", pt.id, exc)
            continue

    if tagged:
        logger.info(
            "[graph.chunk-tag] %s: %d/%d chunk taggati con entità (%d entità totali)",
            document_id,
            tagged,
            len(results),
            len(surface_to_id),
        )
    return tagged


def tag_chunks_for_documents(document_ids: list[str]) -> int:
    """Batch tagger: applica :func:`tag_chunks_for_document` a una lista di
    pagine. Best-effort: errore su una pagina non interrompe le altre.
    """
    total = 0
    for did in document_ids:
        try:
            total += tag_chunks_for_document(did)
        except Exception as exc:
            logger.warning("[graph.chunk-tag] doc=%s failed: %s", did, exc)
    return total


__all__ = ["tag_chunks_for_document", "tag_chunks_for_documents"]

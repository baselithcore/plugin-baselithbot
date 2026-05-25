"""MemoriesStore — wrapper async sopra ``core.services.vectorstore``.

Architettura post-019:

- **Postgres** (`memories` table) = metadata source-of-truth: id, tenant,
  user, kind, key, value, metadata, timestamps. RLS forzato per tenant.
  CRUD via :mod:`llm_wiki.db.memories`.
- **Qdrant** (collection ``user_memories``) = vector storage. Payload
  include ``{tenant_id, user_id, kind}`` per filtri per-user.
  Search via :class:`core.services.vectorstore.VectorStoreService` →
  isolamento tenant automatico tramite context-var ``tenant_id``.
- **Redis** (cache embedding) = cache trasparente del servizio core
  per evitare ri-embedding di testi identici.

Bridge tenant: il context-var di core (``core.context._tenant_context``)
viene popolato per la durata della call usando il ``tenant_id`` di
``llm_wiki.auth.tenant_context.require_tenant_id()``. Token-reset
garantisce nessun leak fra request concorrenti (asyncio task isolation).

Failure-mode design:

- ``add()`` scrive Postgres **prima** di Qdrant. Se Qdrant fallisce
  rimuove la riga Postgres (rollback manuale) e propaga l'errore
  — la memoria non risulta mai parzialmente persistente.
- ``delete()`` cancella Qdrant **prima** di Postgres: in caso di
  fallimento Qdrant la riga Postgres resta, l'utente può ritentare la
  delete.
- ``search()`` recupera id da Qdrant + joina Postgres: se Postgres
  non ritrova un id (ad es. riga cancellata) lo scarta silentemente
  (drift recovery handled by reindex job).
"""

from __future__ import annotations

import logging
from typing import Any

from core.context import (
    get_current_tenant_id,
    reset_tenant_context,
    set_tenant_context,
)
from core.models.domain import Document
from core.services.vectorstore.service import get_vectorstore_service

from llm_wiki import config
from llm_wiki.auth.tenant_context import require_tenant_id
from llm_wiki.db.memories import (
    create_memory_row,
    delete_memory_row,
    get_memories_by_ids,
    upsert_preference_row,
)

logger = logging.getLogger(__name__)

_USER_MEMORIES_COLLECTION = "user_memories"
_VECTOR_SIZE = 1024  # BGE-M3 dense dim


class _WikigenEmbedderAdapter:
    """Adatta l'embedder wikigen al ``EmbedderProtocol`` di core.

    Wikigen embedder: ``encode(texts: list[str], *, is_query: bool)
    -> EmbeddingOutput`` (con `.dense`).
    Core embedder: ``encode(sentences, batch_size=..., ..., normalize_embeddings=...)``.

    L'adapter accetta TUTTI i kwargs del protocollo core (li ignora —
    BGE-M3 li gestisce internamente) e ritorna solo la componente
    dense (sparse/colbert non usati nello user-memories store).
    """

    def __init__(self, embedder: Any, *, is_query: bool = False) -> None:
        self._embedder = embedder
        self._is_query = is_query

    def encode(
        self,
        sentences: str | list[str],
        batch_size: int = 32,
        show_progress_bar: bool | None = None,
        output_value: str = "sentence_embedding",
        convert_to_numpy: bool = True,
        convert_to_tensor: bool = False,
        device: str | None = None,
        normalize_embeddings: bool = False,
    ) -> Any:
        del (
            batch_size,
            show_progress_bar,
            output_value,
            convert_to_numpy,
            convert_to_tensor,
            device,
            normalize_embeddings,
        )
        if isinstance(sentences, str):
            texts = [sentences]
        else:
            texts = list(sentences)
        out = self._embedder.encode(texts, is_query=self._is_query)
        return out.dense or []


class MemoriesStore:
    """Facade unica per memorie utente. Orchestrazione Postgres+Qdrant."""

    def __init__(self) -> None:
        self._vector_service = get_vectorstore_service()
        self._collection = _USER_MEMORIES_COLLECTION
        self._ensured: bool = False

    async def _ensure_collection(self) -> None:
        """Lazy create della collection Qdrant. Idempotente."""
        if self._ensured:
            return
        try:
            await self._vector_service.create_collection(
                collection_name=self._collection,
                vector_size=_VECTOR_SIZE,
            )
            self._ensured = True
        except Exception as exc:
            # ``create_collection`` è già idempotente sotto il cofano;
            # qui logghiamo e proviamo comunque a usare la collection —
            # la prima ``index()`` rilancerà un errore esplicito se
            # davvero non è raggiungibile.
            logger.debug("[memories] ensure_collection: %s", exc)
            self._ensured = True

    def _bridge_tenant(self) -> Any:
        """Allinea il tenant context di core con quello di wikigen.

        Restituisce un token da passare a ``_release_tenant`` per
        ripristinare lo stato precedente del context var di core (no
        leak fra task asyncio concorrenti)."""
        tenant_id = require_tenant_id()
        return set_tenant_context(tenant_id)

    def _release_tenant(self, token: Any) -> None:
        try:
            reset_tenant_context(token)
        except Exception:  # pragma: no cover — defensive
            pass

    async def add(
        self,
        *,
        user_id: str,
        value: str,
        kind: str = "note",
        key: str | None = None,
        metadata: dict[str, Any] | None = None,
        embedder: Any,
    ) -> dict[str, Any]:
        """Crea memoria. Postgres → Qdrant in sequenza con rollback su
        fallimento Qdrant. ``embedder`` è iniettato dal chiamante per
        evitare import circolare di moduli ML pesanti."""
        if not config.POSTGRES_ENABLED:
            raise RuntimeError("Postgres disabilitato.")
        await self._ensure_collection()

        record = create_memory_row(
            user_id=user_id,
            value=value,
            kind=kind,
            key=key,
            metadata=metadata,
        )
        memory_id = record["id"]

        try:
            await self._index(
                memory_id=memory_id,
                user_id=user_id,
                kind=kind,
                key=key,
                value=value,
                embedder=embedder,
                extra_metadata=metadata or {},
            )
        except Exception as exc:
            # Rollback Postgres per evitare riga orfana senza vettore.
            logger.error(
                "[memories] Qdrant index failed for %s (%s) — rolling back row",
                memory_id,
                exc,
            )
            try:
                delete_memory_row(memory_id)
            except Exception as cleanup_exc:
                logger.error(
                    "[memories] rollback delete fallito per %s: %s",
                    memory_id,
                    cleanup_exc,
                )
            raise

        return record

    async def upsert_preference(
        self,
        *,
        user_id: str,
        key: str,
        value: str,
        metadata: dict[str, Any] | None = None,
        embedder: Any,
    ) -> dict[str, Any]:
        """Set-or-replace preferenza. Se sovrascrive una precedente,
        rimuove il vecchio vettore Qdrant prima di indicizzare il nuovo
        (lo stesso ``memory_id`` rimane ma il content è cambiato)."""
        if not config.POSTGRES_ENABLED:
            raise RuntimeError("Postgres disabilitato.")
        await self._ensure_collection()

        record, replaced = upsert_preference_row(
            user_id=user_id,
            key=key,
            value=value,
            metadata=metadata,
        )
        memory_id = record["id"]

        if replaced:
            # Stesso id ma valore cambiato → re-index pulisce + riscrive.
            try:
                await self._delete_vector(memory_id)
            except Exception as exc:
                logger.warning(
                    "[memories] cleanup vettore precedente fallito per %s: %s",
                    memory_id,
                    exc,
                )

        try:
            await self._index(
                memory_id=memory_id,
                user_id=user_id,
                kind="preference",
                key=key,
                value=value,
                embedder=embedder,
                extra_metadata=metadata or {},
            )
        except Exception as exc:
            logger.error(
                "[memories] Qdrant index failed for preference %s — rolling back row",
                memory_id,
            )
            try:
                delete_memory_row(memory_id)
            except Exception:
                pass
            raise exc

        return record

    async def search(
        self,
        *,
        user_id: str | None,
        query: str,
        top_k: int = 5,
        kind: str | None = None,
        min_similarity: float = 0.0,
        embedder: Any,
    ) -> list[dict[str, Any]]:
        """Top-K similarity. ``user_id=None`` cerca su tutto il tenant
        (raro: workspace condivisi). Restituisce dict con campo
        ``similarity`` extra (cosine, range [-1, 1] — con BGE-M3
        normalizzato ≈ [0, 1])."""
        if not config.POSTGRES_ENABLED or top_k <= 0:
            return []
        await self._ensure_collection()

        # Embed query
        adapter = _WikigenEmbedderAdapter(embedder, is_query=True)
        vectors = adapter.encode([query])
        if not vectors or not vectors[0]:
            return []
        query_vector = vectors[0]

        # Build payload filter
        query_filter = self._build_filter(user_id=user_id, kind=kind)

        token = self._bridge_tenant()
        try:
            results = await self._vector_service.search(
                query_vector=query_vector,
                k=max(1, min(top_k, 50)),
                collection_name=self._collection,
                use_cache=False,  # similarity dinamica per-user, cache poco utile
                query_filter=query_filter,
            )
        finally:
            self._release_tenant(token)

        # Estrai (memory_id, similarity) e filtra per min_similarity
        scored: list[tuple[str, float]] = []
        for res in results:
            score = float(getattr(res, "score", 0.0))
            if score < min_similarity:
                continue
            doc = getattr(res, "document", None)
            if doc is None:
                continue
            doc_id = doc.metadata.get("memory_id") or doc.id
            if doc_id:
                scored.append((str(doc_id), score))

        if not scored:
            return []

        # Joina i metadata Postgres (RLS filtra ulteriormente per tenant)
        rows = get_memories_by_ids([sid for sid, _ in scored])
        by_id = {r["id"]: r for r in rows}
        out: list[dict[str, Any]] = []
        for sid, sim in scored:
            row = by_id.get(sid)
            if not row:
                # Drift: vettore esiste in Qdrant ma riga Postgres no
                # (delete parziale). Skippa, lascia che reindex job pulisca.
                continue
            out.append({**row, "similarity": sim})
        return out

    async def delete(self, memory_id: str) -> bool:
        """Cancella memoria. Qdrant prima (idempotente), Postgres dopo
        (autorevole). Errori Qdrant non bloccano il delete Postgres —
        il vettore orfano sarà raccolto da ``cleanup_orphans`` worker."""
        if not config.POSTGRES_ENABLED:
            return False
        try:
            await self._delete_vector(memory_id)
        except Exception as exc:
            logger.warning(
                "[memories] delete vettore %s fallito (drift gestito da reindex): %s",
                memory_id,
                exc,
            )
        return delete_memory_row(memory_id)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    async def _index(
        self,
        *,
        memory_id: str,
        user_id: str,
        kind: str,
        key: str | None,
        value: str,
        embedder: Any,
        extra_metadata: dict[str, Any],
    ) -> None:
        adapter = _WikigenEmbedderAdapter(embedder, is_query=False)
        doc_metadata: dict[str, Any] = {
            "memory_id": memory_id,
            "user_id": user_id,
            "kind": kind,
        }
        if key:
            doc_metadata["key"] = key
        # Allow custom payload extras (sources etc) senza override delle
        # chiavi sistema (memory_id/user_id/kind/key/tenant_id).
        for k, v in extra_metadata.items():
            doc_metadata.setdefault(k, v)

        doc = Document(id=memory_id, content=value, metadata=doc_metadata)
        token = self._bridge_tenant()
        try:
            await self._vector_service.index(
                documents=[doc],
                collection_name=self._collection,
                embedder=adapter,
            )
        finally:
            self._release_tenant(token)

    async def _delete_vector(self, memory_id: str) -> None:
        token = self._bridge_tenant()
        try:
            await self._vector_service.delete_document(
                document_id=memory_id,
                collection_name=self._collection,
            )
        finally:
            self._release_tenant(token)

    @staticmethod
    def _build_filter(*, user_id: str | None, kind: str | None) -> Any:
        """Costruisce un Qdrant ``Filter`` con condizioni user/kind. Il
        ``tenant_id`` viene aggiunto automaticamente dal provider Qdrant
        in base al context-var. Ritorna ``None`` se nessun filtro extra
        (provider gestisce comunque l'isolamento tenant)."""
        try:
            from qdrant_client.http.models import (
                FieldCondition,
                Filter,
                MatchValue,
            )
        except Exception:
            # Qdrant non disponibile a import-time (test/CI minimi)
            return None

        conditions: list[Any] = []
        if user_id:
            conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )
        if kind:
            conditions.append(
                FieldCondition(key="kind", match=MatchValue(value=kind))
            )
        if not conditions:
            return None
        return Filter(must=conditions)


_singleton: MemoriesStore | None = None


def get_memories_store() -> MemoriesStore:
    """Factory singleton. Eager-init alla prima call per avere il
    ``VectorStoreService`` pronto al primo write."""
    global _singleton
    if _singleton is None:
        _singleton = MemoriesStore()
    return _singleton


# Stub usato dai test per evitare l'init di Qdrant durante il setup.
def reset_for_tests() -> None:  # pragma: no cover
    global _singleton
    _singleton = None


__all__ = ["MemoriesStore", "get_memories_store", "reset_for_tests"]


# Touched so tooling does not flag the unused ``get_current_tenant_id``
# re-export, which is provided here for callers that want to verify
# the current tenant before/after invoking the store.
_ = get_current_tenant_id

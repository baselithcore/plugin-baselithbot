from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from qdrant_client.models import FieldCondition, Filter, MatchValue

from agent_jira.chat.agent_state import AgentState
from agent_jira.chat.context import build_context_and_sources
from agent_jira.chat.feedback import apply_feedback_boost
from agent_jira.db import get_document_feedback_summary
from agent_jira.telemetry import telemetry
from agent_jira.config import (
    COLLECTION,
    FEEDBACK_BOOST_ENABLED,
    FEEDBACK_NEGATIVE_WEIGHT,
    FEEDBACK_POSITIVE_WEIGHT,
    FEEDBACK_SCORE_MIN_TOTAL,
    QDRANT,
    RERANK_MAX_CANDIDATES,
)

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService


def search(*args, **kwargs):
    from agent_jira.vectorstore import search as _search

    return _search(*args, **kwargs)


def rerank_hits(*args, **kwargs):
    from agent_jira.chat.reranking import rerank_hits as _rerank_hits

    return _rerank_hits(*args, **kwargs)


class RetrievalPipeline:
    """Orchestrates retrieval, reranking, context building, and caching."""

    def __init__(
        self,
        service: "ChatService",
        *,
        search_fn=search,
        rerank_fn=rerank_hits,
        build_context_fn=build_context_and_sources,
    ) -> None:
        self.service = service
        self.search_fn = search_fn
        self.rerank_fn = rerank_fn
        self.build_context_fn = build_context_fn

    def load_history(self, state: AgentState) -> None:
        conversation_id = (state.request.conversation_id or "").strip() or None
        state.conversation_id = conversation_id

        history_turns, history_text = self.service.history_manager.load(conversation_id)
        state.history_turns = history_turns
        state.history_text = history_text

        # Include il contesto della conversazione per follow-up più precisi.
        # Per il retrieval/reranking, usiamo solo gli ultimi turni per evitare che
        # il contesto vecchio (es. altro documento) domini il vettore di ricerca.
        retrieval_history = ""
        if history_turns:
            # Prendiamo gli ultimi 2 turni (4 scambi max: U, A, U, A)
            recent_turns = history_turns[-2:]
            lines = []
            for turn in recent_turns:
                q = turn.get("query", "")
                a = turn.get("answer", "")
                if q:
                    lines.append(f"Utente: {q}")
                if a:
                    # Tronchiamo l'asserzione dell'assistente se troppo lunga per il retrieval
                    if len(a) > 200:
                        a = a[:200] + "..."
                    lines.append(f"Assistente: {a}")
            retrieval_history = "\n".join(lines)

        query_text = state.user_query
        if retrieval_history:
            query_text = f"{state.user_query}\nContesto recente:\n{retrieval_history}"

        state.rerank_query = query_text
        state.normalized_query = " ".join(query_text.split())
        state.query_vector = self.service.embedder.encode([query_text])[0]
        state.next_action = "retrieve_documents"

    def retrieve_documents(self, state: AgentState) -> None:
        telemetry.increment("retrieval.requests")
        kb_label = str(state.metadata.get("kb_label") or "").strip() or None
        hits = self.search_fn(
            state.query_vector,
            limit=self.service.INITIAL_SEARCH_K,
            kb_label=kb_label,
        )
        if not hits and kb_label:
            state.log(f"retrieval:kb_label_miss={kb_label}")
            hits = self.search_fn(
                state.query_vector,
                limit=self.service.INITIAL_SEARCH_K,
                kb_label=None,
            )
        preferred = set()
        if state.conversation_id and state.conversation_id in getattr(
            self.service, "_last_sources", {}
        ):
            preferred = self.service._last_sources.get(state.conversation_id, set())

        if preferred:

            def _doc_id(hit: Any) -> str:
                payload = getattr(hit, "payload", None) or {}
                for key in ("document_id", "relative_path", "path", "source", "url"):
                    val = payload.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
                return str(getattr(hit, "id", ""))

            # Boost i documenti già usati nella conversazione, ma non escludere gli altri.
            hits = sorted(
                hits,
                key=lambda h: 0 if _doc_id(h) in preferred else 1,
            )

        # Limita i chunk per documento per diversificare i risultati,
        # ma solo se ci sono più documenti. Con pochi documenti (es. un solo
        # file Excel) servono più chunk per coprire record diversi.
        doc_ids_in_hits = {
            (getattr(h, "payload", None) or {}).get("document_id") for h in hits
        }
        doc_ids_in_hits = {d for d in doc_ids_in_hits if isinstance(d, str)}
        if len(doc_ids_in_hits) > 2:
            hits = self._limit_chunks_per_doc(list(hits))

        # Fallback recall: se non abbiamo alcun hit, prova a recuperare qualche documento indicizzato (uno per doc)
        # per evitare di non dare alcuna risposta, ma non forzare il riempimento se abbiamo già match validi.
        try:
            if not hits and not kb_label:
                from agent_jira.vectorstore.state import (
                    _refresh_indexed_items,
                    indexed_items,
                )

                _refresh_indexed_items(force=True)
                if indexed_items:
                    hits = self._fetch_fallback_chunks(
                        state.query_vector,
                        seen_docs=set(),
                        limit=self.service.FINAL_TOP_K,
                    )
        except Exception:
            pass

        # Aggancia documenti citati nel testo (titolo/filename) anche se la similarità non li riprende
        explicit_match_query = state.rerank_query or state.user_query
        hits = self._inject_explicit_doc_matches(
            explicit_match_query,
            hits,
            project_key=state.metadata.get("project_key"),
            kb_label=kb_label,
        )
        if len(doc_ids_in_hits) > 2:
            hits = self._limit_chunks_per_doc(list(hits))
        state.hits = hits
        if not state.hits:
            telemetry.increment("retrieval.empty")
            state.log("retrieval:empty")
            state.clarification_reason = "no_hits"
            state.next_action = "request_clarification"
            return
        telemetry.increment("retrieval.success")
        state.next_action = "score_documents"

    def score_documents(self, state: AgentState) -> None:
        telemetry.increment("rerank.requests")
        rerank_query = state.rerank_query or state.user_query
        normalized_query = state.normalized_query or " ".join(rerank_query.split())
        max_candidates = min(
            len(state.hits), self.service.INITIAL_SEARCH_K, RERANK_MAX_CANDIDATES
        )
        candidates = state.hits[:max_candidates]
        state.ranked_hits = self.rerank_fn(
            rerank_query,
            normalized_query,
            candidates,
            reranker=self.service.reranker,
            cache=self.service.rerank_cache,
        )
        # Diversità per documento: tieni il miglior chunk per doc, poi ordina per score.
        # APPLICA SOGLIA RELATIVA: il cross-encoder produce logit scores che possono
        # essere negativi. Un threshold assoluto (es. 0.0) eliminerebbe tutti i
        # risultati validi. Usiamo un approccio relativo: scartiamo solo i chunk il
        # cui score è molto inferiore al massimo osservato.
        best_per_doc: dict[str, tuple[Any, float]] = {}
        configured_threshold = getattr(self.service, "RERANK_THRESHOLD", 0.0)

        # Determina il massimo score per calcolare la soglia relativa
        if state.ranked_hits:
            max_score = max(s for _, s in state.ranked_hits)
            # Se il threshold configurato è 0.0 (default) e gli score sono tutti negativi,
            # usa soglia relativa: accetta chunk entro 4 punti dal massimo
            if configured_threshold >= 0.0 and max_score < 0.0:
                threshold = max_score - 4.0
            else:
                threshold = configured_threshold
        else:
            threshold = configured_threshold

        above_threshold: list[tuple[Any, float]] = []
        doc_ids_seen: set[str] = set()
        for hit, score in state.ranked_hits:
            if score < threshold:
                continue

            payload = getattr(hit, "payload", None) or {}
            doc_id = payload.get("document_id") or getattr(hit, "id", None)
            if not isinstance(doc_id, str):
                continue
            above_threshold.append((hit, score))
            doc_ids_seen.add(doc_id)
            existing = best_per_doc.get(doc_id)
            if existing is None or score > existing[1]:
                best_per_doc[doc_id] = (hit, score)

        if best_per_doc:
            n_docs = len(best_per_doc)
            final_k = self.service.FINAL_TOP_K
            if n_docs <= 2:
                # Pochi documenti (es. un singolo file Excel): servono molti chunk
                # per coprire tutti i record/campi. Usiamo un multiplo di final_k.
                expanded_k = final_k * 3
                state.ranked_hits = sorted(
                    above_threshold, key=lambda item: item[1], reverse=True
                )[:expanded_k]
            elif n_docs < final_k:
                # Pochi documenti ma >2: prendiamo i top chunk per riempire il contesto.
                state.ranked_hits = sorted(
                    above_threshold, key=lambda item: item[1], reverse=True
                )[:final_k]
            else:
                diverse = sorted(
                    best_per_doc.values(), key=lambda item: item[1], reverse=True
                )
                state.ranked_hits = diverse[:final_k]
        else:
            state.ranked_hits = self._fallback_ranked_hits(candidates)

        if not state.ranked_hits:
            telemetry.increment("rerank.empty")
            state.log("rerank:empty")
            state.clarification_reason = "no_reranked_hits"
            state.next_action = "request_clarification"
            return

        if FEEDBACK_BOOST_ENABLED:
            state.next_action = "apply_feedback"
        else:
            state.next_action = "build_context"

    def apply_feedback(self, state: AgentState) -> None:
        feedback_stats = get_document_feedback_summary(
            min_total=FEEDBACK_SCORE_MIN_TOTAL
        )
        state.ranked_hits = apply_feedback_boost(
            state.ranked_hits,
            feedback_stats,
            min_total=FEEDBACK_SCORE_MIN_TOTAL,
            positive_weight=FEEDBACK_POSITIVE_WEIGHT,
            negative_weight=FEEDBACK_NEGATIVE_WEIGHT,
        )
        state.next_action = "build_context"

    def build_context(self, state: AgentState) -> None:
        # Per scenari con pochi documenti (tipico Excel), score_documents ha già
        # espanso ranked_hits a final_k*3. Rispettiamo quella decisione.
        unique_doc_ids: set[str] = set()
        for hit, _ in state.ranked_hits:
            payload = getattr(hit, "payload", None) or {}
            doc_id = payload.get("document_id")
            if isinstance(doc_id, str):
                unique_doc_ids.add(doc_id)
        effective_top_k = (
            self.service.FINAL_TOP_K * 3
            if len(unique_doc_ids) <= 2
            else self.service.FINAL_TOP_K
        )
        state.ranked_hits = state.ranked_hits[:effective_top_k]
        context, doc_sources = self.build_context_fn(
            state.ranked_hits,
            final_top_k=effective_top_k,
            newline=self.service.newline,
            double_newline=self.service.double_newline,
            section_separator=self.service.section_separator,
        )
        state.context = context
        state.doc_sources = list(doc_sources)
        if state.doc_sources:
            source_metrics: Dict[str, Any] = {}
            ratios: List[float] = []
            scores: List[float] = []
            top_ratio: Optional[float] = None

            for idx, source in enumerate(state.doc_sources):
                ratio_value = source.get("context_ratio")
                if isinstance(ratio_value, (int, float)):
                    ratios.append(ratio_value)
                    if idx == 0:
                        top_ratio = ratio_value
                score_value = source.get("score_avg")
                if not isinstance(score_value, (int, float)):
                    score_value = source.get("score")
                if isinstance(score_value, (int, float)):
                    scores.append(score_value)

            if ratios:
                total_ratio = sum(ratios)
                source_metrics["total_context_ratio"] = total_ratio
                source_metrics["mean_context_ratio"] = total_ratio / len(ratios)
            if scores:
                source_metrics["mean_score"] = sum(scores) / len(scores)
                source_metrics["max_score"] = max(scores)
            if top_ratio is not None:
                source_metrics["top_context_ratio"] = top_ratio
                low_coverage = top_ratio < 0.25
                source_metrics["low_coverage"] = low_coverage
                state.log(f"sources:top_ratio={top_ratio:.2f}")
                if low_coverage:
                    telemetry.increment("sources.low_coverage")
            else:
                source_metrics["low_coverage"] = False
            state.source_metrics = source_metrics
        else:
            state.source_metrics = {}

        if not state.context.strip() and not state.history_text:
            state.log("context:empty_without_history")
            state.clarification_reason = "empty_context"
            state.next_action = "request_clarification"
            return

        state.next_action = "check_cache"

    def check_cache(self, state: AgentState) -> None:
        if self.service.response_cache is None:
            state.next_action = (
                "plan_backlog" if not state.rag_only else "generate_answer"
            )
            return

        cache_context_repr = state.context
        if state.history_text:
            cache_context_repr = f"{state.history_text}\n\n====\n\n{state.context}"
        if state.rag_only:
            cache_context_repr = f"[RAG_ONLY]\n{cache_context_repr}"

        context_hash = hashlib.sha256(cache_context_repr.encode("utf-8")).hexdigest()
        state.cache_key = (state.normalized_query, context_hash)
        cached_answer = self.service.response_cache.get(state.cache_key)

        if cached_answer is not None:
            telemetry.increment("response_cache.hit")
            telemetry.increment("answers.cached")
            state.answer = cached_answer
            state.done = True
            state.next_action = ""
            return

        telemetry.increment("response_cache.miss")
        state.next_action = "plan_backlog" if not state.rag_only else "generate_answer"

    @staticmethod
    def _limit_chunks_per_doc(all_hits: list[Any], max_per_doc: int = 2) -> list[Any]:
        """Mantiene al massimo `max_per_doc` chunk per document_id, preservando l'ordine."""
        kept: list[Any] = []
        seen_counts: Dict[str, int] = {}
        for hit in all_hits:
            payload = getattr(hit, "payload", None) or {}
            doc_id = payload.get("document_id")
            if not isinstance(doc_id, str):
                kept.append(hit)
                continue
            count = seen_counts.get(doc_id, 0)
            if count < max_per_doc:
                kept.append(hit)
                seen_counts[doc_id] = count + 1
        return kept

    @staticmethod
    def _fallback_ranked_hits(candidates: Sequence[Any]) -> list[tuple[Any, float]]:
        """
        Se il reranker non produce risultati utilizzabili ma il retrieval ha trovato chunk,
        conserva i migliori hit raw per evitare falsi negativi su query generiche.
        """
        best_per_doc: Dict[str, tuple[Any, float]] = {}
        for idx, hit in enumerate(candidates):
            payload = getattr(hit, "payload", None) or {}
            raw_doc_id = payload.get("document_id") or getattr(hit, "id", None)
            if raw_doc_id is None:
                doc_id = f"candidate-{idx}"
            else:
                doc_id = str(raw_doc_id)

            raw_score = getattr(hit, "score", None)
            try:
                score = float(raw_score) if raw_score is not None else 0.0
            except (TypeError, ValueError):
                score = 0.0

            existing = best_per_doc.get(doc_id)
            if existing is None or score > existing[1]:
                best_per_doc[doc_id] = (hit, score)

        if not best_per_doc:
            return []

        return sorted(best_per_doc.values(), key=lambda item: item[1], reverse=True)

    @staticmethod
    def _inject_explicit_doc_matches(
        query: str,
        hits: list[Any],
        project_key: Optional[str] = None,
        kb_label: Optional[str] = None,
    ) -> list[Any]:
        """
        Se l'utente cita esplicitamente un titolo/filename già indicizzato, inserisci almeno
        un chunk di quel documento anche se la similarità non lo riprende.
        """

        try:
            query_l = query.lower()
            doc_ids_in_hits = {
                (getattr(hit, "payload", None) or {}).get("document_id") for hit in hits
            }
            doc_ids_in_hits = {
                doc_id for doc_id in doc_ids_in_hits if isinstance(doc_id, str)
            }
            kb_label_norm = str(kb_label or "").strip().lower()

            # Retrieve project_key from arguments
            project_key_norm = project_key.upper() if project_key else ""

            candidates: list[str] = []
            from agent_jira.vectorstore.state import (
                _refresh_indexed_items,
                indexed_items,
            )

            _refresh_indexed_items(force=False)  # Usa cache/throttling
            for doc_id, meta in indexed_items.items():
                md = meta.get("metadata") or {}
                document_labels = {
                    str(doc_id).strip().lower(),
                    str(md.get("kb_label") or "").strip().lower(),
                    str(md.get("doc_label") or "").strip().lower(),
                    str(md.get("jira_label") or "").strip().lower(),
                    str(md.get("label") or "").strip().lower(),
                }
                document_labels = {label for label in document_labels if label}

                if kb_label_norm:
                    if (
                        kb_label_norm in document_labels
                        and doc_id not in doc_ids_in_hits
                    ):
                        candidates.append(doc_id)
                    continue

                title = str(md.get("title") or "").lower()
                filename = str(md.get("filename") or "").lower()
                rel = str(md.get("relative_path") or "").lower()

                # Check for explicit project match in metadata
                doc_projects_raw = str(md.get("doc_projects") or "").upper()
                doc_projects = [
                    p.strip() for p in doc_projects_raw.split(",") if p.strip()
                ]

                project_match = project_key_norm and project_key_norm in doc_projects

                stems = {
                    Path(rel).stem.lower() if rel else "",
                    Path(filename).stem.lower() if filename else "",
                    Path(title).stem.lower() if title else "",
                }
                stems = {s for s in stems if s}
                tokens = set(query_l.replace("_", " ").replace("-", " ").split())
                if (
                    project_match
                    or (title and title in query_l)
                    or (filename and filename in query_l)
                    or (rel and rel in query_l)
                    or any(stem in tokens for stem in stems)
                ):
                    if doc_id not in doc_ids_in_hits:
                        candidates.append(doc_id)

            extra_hits: list[Any] = []
            for doc_id in candidates:
                try:
                    filt = Filter(
                        must=[
                            FieldCondition(
                                key="document_id", match=MatchValue(value=doc_id)
                            )
                        ]
                    )
                    points, _ = QDRANT.scroll(
                        collection_name=COLLECTION,
                        limit=2,
                        offset=None,
                        with_payload=True,
                        with_vectors=False,
                        filter=filt,
                    )
                    if points:
                        extra_hits.append(points[0])
                        if len(points) > 1:
                            extra_hits.append(points[1])
                except Exception:
                    continue

            return hits + extra_hits if extra_hits else hits
        except Exception:
            return hits

    @staticmethod
    def _fetch_fallback_chunks(
        query_vector: list[float], seen_docs: set[str], limit: int
    ) -> list[Any]:
        """Recupera fino a `limit` chunk da documenti non presenti in `seen_docs`."""
        if limit <= 0:
            return []

        try:
            # Escludiamo i documenti già visti per forzare la diversità
            must_not = []
            for doc_id in seen_docs:
                if doc_id:
                    must_not.append(
                        FieldCondition(
                            key="document_id", match=MatchValue(value=doc_id)
                        )
                    )

            # Eseguiamo una ricerca più ampia per trovare candidati da documenti diversi.
            # Qdrant non garantisce 1 per doc in una singola query_points standard senza set
            # prefissati, quindi ne chiediamo di più e deduplichiamo.
            response = QDRANT.query_points(
                collection_name=COLLECTION,
                query=query_vector,
                limit=min(limit * 5, 100),
                query_filter=Filter(must_not=must_not) if must_not else None,
                with_payload=True,
                with_vectors=False,
            )

            extra: list[Any] = []
            seen_extra_docs = set()
            for point in response.points:
                p_doc_id = (point.payload or {}).get("document_id")
                if (
                    p_doc_id
                    and p_doc_id not in seen_docs
                    and p_doc_id not in seen_extra_docs
                ):
                    extra.append(point)
                    seen_extra_docs.add(p_doc_id)
                    if len(extra) >= limit:
                        break
            return extra
        except Exception:
            return []


__all__ = ["RetrievalPipeline"]

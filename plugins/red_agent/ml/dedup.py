"""Cross-scan semantic dedup of findings.

Embeds each new finding and checks Qdrant for prior findings on the
same target/tenant. Hits above the cosine threshold are linked back to
the existing finding (``evidence['duplicate_of']``) instead of being
persisted as new — collapsing recurring nuclei templates, repeat zap
banners, and re-discovered nmap services into a single canonical
record per target.

Design invariants:

- **Fail-open**: any error in embedding, search, or upsert returns the
  input findings as-if dedup were disabled. The deterministic flow is
  never blocked.
- **Tenant + target scoping**: every payload carries ``tenant_id`` and
  ``target_value``; the query filters on both, so tenants never see
  each other's data and findings only collapse when they belong to the
  same logical target.
- **Stable id**: each finding occupies a Qdrant point keyed by its UUID
  string. Re-running dedup with the same finding is idempotent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding

logger = get_logger(__name__)


class _EmbedderLike(Protocol):
    """Subset of ``EmbedderProtocol`` we depend on."""

    def encode(self, sentences: Any, **kwargs: Any) -> Any: ...


class _VectorStoreLike(Protocol):
    """Subset of :class:`core.services.vectorstore.service.VectorStoreService`."""

    async def create_collection(
        self,
        collection_name: str | None = None,
        vector_size: int | None = None,
        **kwargs: Any,
    ) -> None: ...

    async def search(
        self,
        query_vector: Any,
        k: int | None = None,
        collection_name: str | None = None,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> Any: ...


class _ProviderLike(Protocol):
    """Subset of the underlying Qdrant provider used for raw upserts."""

    async def upsert(
        self, collection_name: str, points: list[dict[str, Any]], **kwargs: Any
    ) -> None: ...


@dataclass(slots=True)
class DedupResult:
    """Outcome of a dedup pass."""

    new: list[Finding] = field(default_factory=list)
    duplicates: list[Finding] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.new) + len(self.duplicates)


class SemanticDedupService:
    """Embedding-based dedup of findings across scans."""

    def __init__(
        self,
        *,
        vectorstore: _VectorStoreLike | None,
        embedder: _EmbedderLike | None,
        collection: str,
        threshold: float,
        enabled: bool,
        embedding_model_id: str = "all-MiniLM-L6-v2",
        vector_size: int = 384,
    ) -> None:
        self._vs = vectorstore
        self._embedder = embedder
        self._collection = collection
        self._threshold = threshold
        self._enabled = enabled and vectorstore is not None and embedder is not None
        self._embedding_model_id = embedding_model_id
        self._vector_size = vector_size
        self._collection_ready = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def dedupe(
        self,
        scan_id: UUID,
        findings: list[Finding],
        tenant_id: str | None,
        target_value: str,
    ) -> DedupResult:
        """Split ``findings`` into (new, duplicates).

        Duplicates are returned annotated with
        ``evidence['duplicate_of']`` set to the existing finding's id
        and ``evidence['duplicate_score']`` set to the cosine sim.
        Callers should skip persisting duplicates as new rows but may
        emit an event so the UI can show the recurrence count.
        """
        if not self._enabled or not findings:
            return DedupResult(new=list(findings))

        try:
            await self._ensure_collection()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.dedup.collection_init_failed", extra={"err": str(e)}
            )
            return DedupResult(new=list(findings))

        try:
            vectors = await self._embed_batch([_finding_text(f) for f in findings])
        except Exception as e:  # noqa: BLE001
            logger.warning("red_agent.dedup.embed_failed", extra={"err": str(e)})
            return DedupResult(new=list(findings))

        result = DedupResult()
        new_points: list[dict[str, Any]] = []
        for f, vec in zip(findings, vectors):
            existing = await self._find_match(vec, tenant_id, target_value)
            if existing is not None:
                existing_id, score = existing
                annotated = _mark_duplicate(f, existing_id, score)
                result.duplicates.append(annotated)
                continue

            result.new.append(f)
            new_points.append(
                {
                    "id": str(f.id),
                    "vector": list(vec),
                    "payload": {
                        "scan_id": str(scan_id),
                        "tenant_id": tenant_id or "default",
                        "target_value": target_value,
                        "scanner": f.scanner,
                        "title": f.title,
                        "severity": f.severity.value,
                        "endpoint": f.endpoint,
                        "cwe": f.cwe,
                        "cve": f.cve,
                    },
                }
            )

        if new_points:
            await self._upsert_points(new_points)
        return result

    async def _ensure_collection(self) -> None:
        if self._collection_ready or self._vs is None:
            return
        try:
            await self._vs.create_collection(
                collection_name=self._collection, vector_size=self._vector_size
            )
        except Exception as e:  # noqa: BLE001
            # Provider raises on "already exists" too — log at debug and move on
            # rather than retrying on every dedup call.
            logger.debug(
                "red_agent.dedup.create_collection_skipped", extra={"err": str(e)}
            )
        self._collection_ready = True

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        assert self._embedder is not None  # narrowed by self._enabled
        out = self._embedder.encode(texts, convert_to_numpy=True)
        if hasattr(out, "tolist"):
            out = out.tolist()
        return [list(v) for v in out]

    async def _find_match(
        self,
        vector: list[float],
        tenant_id: str | None,
        target_value: str,
    ) -> tuple[str, float] | None:
        if self._vs is None:
            return None
        try:
            query_filter = _build_filter(tenant_id, target_value)
            results = await self._vs.search(
                query_vector=vector,
                k=1,
                collection_name=self._collection,
                use_cache=False,
                query_filter=query_filter,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("red_agent.dedup.search_failed", extra={"err": str(e)})
            return None

        top = _top_hit(results)
        if top is None:
            return None
        existing_id, score = top
        if score < self._threshold:
            return None
        return existing_id, score

    async def _upsert_points(self, points: list[dict[str, Any]]) -> None:
        if self._vs is None:
            return
        provider: _ProviderLike | None = getattr(self._vs, "provider", None)
        if provider is None:
            logger.warning("red_agent.dedup.no_provider_for_upsert")
            return
        try:
            await provider.upsert(collection_name=self._collection, points=points)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.dedup.upsert_failed",
                extra={"err": str(e), "count": len(points)},
            )


def _finding_text(f: Finding) -> str:
    """Stable embedding payload for a finding.

    Concatenates the fields that determine "is this the same finding"
    semantically. Volatile fields (timestamps, ids) are excluded so the
    embedding is reproducible across scans.
    """
    parts = [
        f.scanner,
        f.title,
        f.description[:500],
        f.endpoint or "",
        f.service or "",
        f.cwe or "",
        f.cve or "",
    ]
    return " | ".join(p for p in parts if p)


def _mark_duplicate(f: Finding, existing_id: str, score: float) -> Finding:
    new_evidence = dict(f.evidence) if isinstance(f.evidence, dict) else {}
    new_evidence["duplicate_of"] = existing_id
    new_evidence["duplicate_score"] = round(score, 4)
    return f.model_copy(update={"evidence": new_evidence})


def _build_filter(tenant_id: str | None, target_value: str) -> Any:
    """Build a Qdrant ``Filter`` scoped to the tenant + target.

    Imported lazily so the plugin still imports when ``qdrant_client``
    is not installed (dedup is opt-in).
    """
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchValue
    except ImportError:
        return None

    return Filter(
        must=[  # type: ignore[list-item]  # qdrant_client uses invariant list[Condition]
            FieldCondition(
                key="tenant_id", match=MatchValue(value=tenant_id or "default")
            ),
            FieldCondition(key="target_value", match=MatchValue(value=target_value)),
        ]
    )


def _top_hit(results: Any) -> tuple[str, float] | None:
    """Normalize the various shapes of Qdrant search results to (id, score)."""
    if not results:
        return None
    try:
        top = results[0]
    except (TypeError, IndexError):
        return None

    point_id = getattr(top, "id", None)
    score = getattr(top, "score", None)
    if point_id is None and isinstance(top, dict):
        point_id = top.get("id")
        score = top.get("score")
    if point_id is None or score is None:
        return None
    return str(point_id), float(score)

"""CVE Hunter Vector Store.

Vector store integration for semantic CVE search.
Wraps core/vector module for CVE-specific embeddings.
"""

from core.observability.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timezone


from typing import Any, Dict, List, Optional

logger = get_logger(__name__)


# =============================================================================
# Search Result Model
# =============================================================================


@dataclass
class CVESearchResult:
    """Result from semantic CVE search."""

    cve_id: str
    score: float
    description: str
    severity: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "cve_id": self.cve_id,
            "score": self.score,
            "description": self.description,
            "severity": self.severity,
            "metadata": self.metadata,
        }


# =============================================================================
# Vector Store
# =============================================================================


class CVEVectorStore:
    """Vector store for semantic CVE search.

    Provides embedding-based similarity search for CVEs.

    Example:
        ```python
        store = CVEVectorStore()
        await store.initialize()
        await store.index_cve(cve)
        results = await store.search("SQL injection in authentication")
        ```
    """

    COLLECTION_NAME = "cve_hunter_cves"

    def __init__(self):
        """Initialize vector store."""
        self._store = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the vector store.

        Returns:
            True if initialization succeeded
        """
        if self._initialized:
            return True

        try:
            from core.vector import VectorStore

            self._store = VectorStore(collection_name=self.COLLECTION_NAME)
            await self._store.initialize()
            self._initialized = True
            logger.info("CVE vector store initialized")
            return True

        except ImportError:
            logger.warning("Vector store not available - core.vector not found")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            return False

    async def index_cve(
        self,
        cve_id: str,
        description: str,
        severity: str,
        cvss_score: float,
        cwe_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Index a CVE for semantic search.

        Args:
            cve_id: CVE identifier
            description: CVE description (used for embedding)
            severity: Severity level
            cvss_score: CVSS score
            cwe_ids: Associated CWEs
            metadata: Additional metadata

        Returns:
            True if indexing succeeded
        """
        if not self._initialized:
            return False

        try:
            doc_metadata = {
                "cve_id": cve_id,
                "severity": severity,
                "cvss_score": cvss_score,
                "cwe_ids": cwe_ids or [],
                "indexed_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            }

            await self._store.add(
                document_id=cve_id,
                text=description,
                metadata=doc_metadata,
            )

            logger.debug(f"Indexed CVE: {cve_id}")
            return True

        except Exception as e:
            logger.warning(f"Failed to index CVE {cve_id}: {e}")
            return False

    async def index_batch(
        self,
        cves: List[Dict[str, Any]],
    ) -> int:
        """Index multiple CVEs.

        Args:
            cves: List of CVE dicts with id, description, severity, cvss_score

        Returns:
            Number of successfully indexed CVEs
        """
        if not self._initialized:
            return 0

        indexed = 0
        for cve in cves:
            success = await self.index_cve(
                cve_id=cve.get("cve_id", cve.get("id", "")),
                description=cve.get("description", ""),
                severity=cve.get("severity", "unknown"),
                cvss_score=cve.get("cvss_score", 0.0),
                cwe_ids=cve.get("cwe_ids"),
            )
            if success:
                indexed += 1

        logger.info(f"Batch indexed {indexed}/{len(cves)} CVEs")
        return indexed

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.5,
        severity_filter: Optional[str] = None,
    ) -> List[CVESearchResult]:
        """Search for similar CVEs.

        Args:
            query: Natural language query
            limit: Maximum results to return
            min_score: Minimum similarity score
            severity_filter: Optional severity filter

        Returns:
            List of search results
        """
        if not self._initialized:
            return []

        try:
            filter_dict = {}
            if severity_filter:
                filter_dict["severity"] = severity_filter

            results = await self._store.search(
                query=query,
                limit=limit,
                filters=filter_dict if filter_dict else None,
            )

            search_results = []
            for result in results:
                if result.score >= min_score:
                    search_results.append(
                        CVESearchResult(
                            cve_id=result.metadata.get("cve_id", ""),
                            score=result.score,
                            description=result.text[:500],
                            severity=result.metadata.get("severity", "unknown"),
                            metadata=result.metadata,
                        )
                    )

            return search_results

        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []

    async def find_similar(
        self,
        cve_id: str,
        limit: int = 5,
    ) -> List[CVESearchResult]:
        """Find CVEs similar to a given CVE.

        Args:
            cve_id: Reference CVE ID
            limit: Maximum results

        Returns:
            List of similar CVEs
        """
        if not self._initialized:
            return []

        try:
            # Get the CVE's embedding
            doc = await self._store.get(cve_id)
            if not doc:
                return []

            # Search for similar (excluding self)
            results = await self._store.search_by_vector(
                vector=doc.vector,
                limit=limit + 1,
            )

            return [
                CVESearchResult(
                    cve_id=r.metadata.get("cve_id", ""),
                    score=r.score,
                    description=r.text[:500],
                    severity=r.metadata.get("severity", "unknown"),
                    metadata=r.metadata,
                )
                for r in results
                if r.metadata.get("cve_id") != cve_id
            ][:limit]

        except Exception as e:
            logger.warning(f"Similar search failed: {e}")
            return []

    async def delete(self, cve_id: str) -> bool:
        """Delete a CVE from the index.

        Args:
            cve_id: CVE to delete

        Returns:
            True if deletion succeeded
        """
        if not self._initialized:
            return False

        try:
            await self._store.delete(cve_id)
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        if not self._initialized:
            return {"status": "not_initialized"}

        try:
            return {
                "status": "active",
                "collection": self.COLLECTION_NAME,
                "count": self._store.count() if hasattr(self._store, "count") else -1,
            }
        except Exception:
            return {"status": "error"}


# =============================================================================
# Singleton
# =============================================================================

_store_instance: Optional[CVEVectorStore] = None


def get_cve_vector_store() -> CVEVectorStore:
    """Get singleton vector store instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = CVEVectorStore()
    return _store_instance

"""Lookup mixin for HoneypotCVECorrelator."""

from datetime import datetime, timezone
from typing import List

from core.observability.logging import get_logger

from ...events import HoneypotEvents, emit_honeypot_event

logger = get_logger(__name__)


class LookupMixin:
    """Mixin providing CVE lookup methods for the correlator."""

    async def _request_cve_lookup(
        self,
        category: str,
        cwes: List[str],
        patterns: List[str],
    ) -> None:
        """Request CVE lookup from CVE Hunter via EventBus."""
        if not self._event_bus:
            return

        # Rate limiting (debounce)
        key = f"{category}:{sorted(cwes)}"
        now = datetime.now(timezone.utc)

        if key in self._last_lookup:
            elapsed = (now - self._last_lookup[key]).total_seconds()
            if elapsed < 60:  # 1 minute debounce
                logger.debug(f"Debouncing CVE lookup for {key}")
                return

        self._last_lookup[key] = now

        await emit_honeypot_event(
            HoneypotEvents.REQUEST_CVE_LOOKUP,
            {
                "source": "honeypot",
                "category": category,
                "cwes": cwes,
                "patterns": patterns,
                "timestamp": now.isoformat(),
                "request_category": category,  # Redundant but explicit
            },
        )

    async def _dynamic_cve_lookup(self, category: str, cwes: List[str]) -> None:
        """Perform dynamic CVE lookup using CVE service.

        Args:
            category: Attack category
            cwes: CWE identifiers
        """
        if not self._cve_service:
            logger.warning("CVE service not available for dynamic lookup")
            return

        try:
            # Search by first CWE (most relevant)
            if cwes:
                result = await self._cve_service.search_by_cwe(cwes[0], limit=10)
                logger.info(
                    f"Dynamic CVE lookup for {category} ({cwes[0]}): "
                    f"{len(result.results)} results"
                )

                # Cache results
                for cve_data in result.results:
                    self._cve_cache[cve_data.cve_id] = {
                        "cve_id": cve_data.cve_id,
                        "description": cve_data.description,
                        "severity": cve_data.cvss_v3_severity or "unknown",
                        "score": cve_data.cvss_v3_score or cve_data.cvss_v2_score,
                        "cwe_ids": cve_data.cwe_ids,
                        "references": cve_data.references,
                        "source": "nvd_dynamic",
                    }

        except Exception as e:
            logger.error(f"Dynamic CVE lookup failed for {category}: {e}")

    async def _enrich_cve_from_service(self, cve_id: str) -> None:
        """Enrich CVE data from service.

        Args:
            cve_id: CVE identifier
        """
        if not self._cve_service:
            return

        try:
            cve_data = await self._cve_service.lookup_cve(cve_id)
            if cve_data:
                self._cve_cache[cve_id] = {
                    "cve_id": cve_data.cve_id,
                    "description": cve_data.description,
                    "severity": cve_data.cvss_v3_severity or "unknown",
                    "score": cve_data.cvss_v3_score or cve_data.cvss_v2_score,
                    "cwe_ids": cve_data.cwe_ids,
                    "references": cve_data.references,
                    "source": "nvd_direct",
                }
                logger.info(f"Enriched {cve_id} from NVD")
        except Exception as e:
            logger.error(f"CVE enrichment failed for {cve_id}: {e}")

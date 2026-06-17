"""NVD API mixin for CVEService.

Wraps nvdlib calls (sync) in async executors.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import nvdlib

from core.observability.logging import get_logger

from ...models.cve import CVEData

logger = get_logger(__name__)


class NVDMixin:
    """NVD API helpers for CVEService."""

    async def _fetch_from_nvd(self, cve_id: str) -> Optional[CVEData]:
        """Fetch CVE from NVD API.

        Args:
            cve_id: CVE identifier

        Returns:
            CVE data or None
        """
        try:
            # nvdlib is sync, wrap in executor
            loop = asyncio.get_event_loop()
            cve_result = await loop.run_in_executor(
                None,
                lambda: (
                    nvdlib.searchCVE(
                        cveId=cve_id,
                        key=self.config.nvd_api_key,
                        delay=self._rate_limit_delay,
                    )[0]
                    if nvdlib.searchCVE(
                        cveId=cve_id,
                        key=self.config.nvd_api_key,
                        delay=self._rate_limit_delay,
                    )
                    else None
                ),
            )

            if not cve_result:
                return None

            self._stats.api_calls += 1
            return self._parse_nvd_result(cve_result)

        except Exception as e:
            logger.error(f"NVD API error for {cve_id}: {e}")
            return None

    async def _search_nvd_by_cwe(self, cwe_id: str, limit: int) -> List[CVEData]:
        """Search NVD by CWE.

        Args:
            cwe_id: CWE identifier
            limit: Max results

        Returns:
            List of CVE data
        """
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: nvdlib.searchCVE(
                    cweId=cwe_id,
                    key=self.config.nvd_api_key,
                    delay=self._rate_limit_delay,
                    limit=limit,
                ),
            )

            self._stats.api_calls += 1
            return [self._parse_nvd_result(r) for r in results if r][:limit]

        except Exception as e:
            logger.error(f"NVD CWE search error for {cwe_id}: {e}")
            return []

    async def _search_nvd_by_keywords(
        self, keywords: List[str], limit: int
    ) -> List[CVEData]:
        """Search NVD by keywords.

        Args:
            keywords: Search keywords
            limit: Max results

        Returns:
            List of CVE data
        """
        try:
            # For keyword search, we use the keyword parameter
            keyword_str = " ".join(keywords)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: nvdlib.searchCVE(
                    keywordSearch=keyword_str,
                    key=self.config.nvd_api_key,
                    delay=self._rate_limit_delay,
                    limit=limit,
                ),
            )

            self._stats.api_calls += 1
            return [self._parse_nvd_result(r) for r in results if r][:limit]

        except Exception as e:
            logger.error(f"NVD keyword search error: {e}")
            return []

    async def _fetch_recent_from_nvd(self, limit: int) -> List[CVEData]:
        """Fetch recent CVEs from NVD.

        Args:
            limit: Max results

        Returns:
            List of recent CVE data
        """
        try:
            # Get CVEs from last 30 days
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: nvdlib.searchCVE(
                    pubStartDate=start_date,
                    pubEndDate=end_date,
                    key=self.config.nvd_api_key,
                    delay=self._rate_limit_delay,
                    limit=limit,
                ),
            )

            self._stats.api_calls += 1
            return [self._parse_nvd_result(r) for r in results if r][:limit]

        except Exception as e:
            logger.error(f"NVD recent CVEs fetch error: {e}")
            return []

    def _parse_nvd_result(self, nvd_cve) -> CVEData:
        """Parse nvdlib CVE result into our model.

        Args:
            nvd_cve: nvdlib CVE object

        Returns:
            Structured CVE data
        """
        # Extract CVSS scores
        cvss_v3_score = None
        cvss_v3_severity = None
        cvss_v2_score = None

        if hasattr(nvd_cve, "v3score"):
            cvss_v3_score = nvd_cve.v3score
        if hasattr(nvd_cve, "v3severity"):
            cvss_v3_severity = nvd_cve.v3severity
        if hasattr(nvd_cve, "score") and not cvss_v3_score:
            cvss_v2_score = nvd_cve.score

        # Extract CWE IDs
        cwe_ids = []
        if hasattr(nvd_cve, "cwe"):
            cwe_ids = nvd_cve.cwe if isinstance(nvd_cve.cwe, list) else [nvd_cve.cwe]

        # Extract CPEs
        cpe_uris = []
        if hasattr(nvd_cve, "cpe"):
            cpe_uris = nvd_cve.cpe if isinstance(nvd_cve.cpe, list) else [nvd_cve.cpe]

        # Extract references
        references = []
        if hasattr(nvd_cve, "url"):
            references = nvd_cve.url if isinstance(nvd_cve.url, list) else [nvd_cve.url]

        return CVEData(
            cve_id=nvd_cve.id,
            description=getattr(nvd_cve, "descriptions", [""])[0]
            if hasattr(nvd_cve, "descriptions")
            else "",
            published_date=getattr(nvd_cve, "published", None),
            last_modified=getattr(nvd_cve, "lastModified", None),
            cvss_v3_score=cvss_v3_score,
            cvss_v3_severity=cvss_v3_severity,
            cvss_v2_score=cvss_v2_score,
            cwe_ids=cwe_ids,
            cpe_uris=cpe_uris,
            references=references,
            source="nvd",
            cached=False,
            fetched_at=datetime.now(timezone.utc),
        )

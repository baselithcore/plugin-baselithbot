"""Scanning mixin for CVE Hunter Swarm Coordinator.

Extracts SAST/DAST/Full scan orchestration logic from the coordinator,
keeping the core coordinator focused on lifecycle and agent management.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from core.observability.tracing import get_tracer
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from core.swarm.types import Task, TaskPriority

from ...models import (
    AgentTaskStatus,
    CVERecord,
    CVESource,
    DASTFinding,
    DASTScanResult,
    SASTFinding,
    SASTScanResult,
    ScanResult,
)
from ...utils.patterns import pattern_to_severity

if TYPE_CHECKING:
    from ...config import CVEHunterConfig
    from ...agents.discovery import CVEDiscoveryAgent
    from ...metrics import CVEHunterMetrics
    from .dast_tools import DASTToolsHandler
    from .feedback import FeedbackHandler
    from .findings import FindingsHandler
    from .sast_tools import SASTToolsHandler

logger = get_logger(__name__)
_tracer = get_tracer("cve_hunter.scanning")


class ScanningProtocol(Protocol):
    """Protocol defining required attributes for ScanningMixin."""

    config: CVEHunterConfig
    _discovery: CVEDiscoveryAgent
    _colony: Any
    _cve_cache: Dict[str, CVERecord]
    _scanner: Any
    _scan_results: List[ScanResult]
    _sast_findings: List[SASTFinding]
    _dast_findings: List[DASTFinding]
    _sast_scan_results: List[SASTScanResult]
    _dast_scan_results: List[DASTScanResult]
    _cache_lock: Any
    feedback_handler: FeedbackHandler
    findings_handler: FindingsHandler
    sast_tools_handler: SASTToolsHandler
    dast_tools_handler: DASTToolsHandler
    metrics: CVEHunterMetrics

    def _update_agent_status(
        self, agent_id: str, status: AgentTaskStatus, task: Optional[str] = None
    ) -> None: ...

    def _add_discovery_log(
        self, message: str, is_alert: bool = False, is_error: bool = False
    ) -> None: ...

    def _should_alert(self, cve: CVERecord) -> bool: ...
    async def _create_alert(self, cve: CVERecord) -> Any: ...
    async def _analyze_new_cves(self, cves: List[CVERecord]) -> None: ...
    async def _store_cves_in_memory(self, cves: List[CVERecord]) -> None: ...
    async def _emit_scan_completed(self, result: ScanResult) -> None: ...
    async def _run_full_scan_impl(self, days_back: int) -> ScanResult: ...
    async def _run_sast_scan_impl(
        self, paths: Optional[List[str]] = None
    ) -> SASTScanResult: ...
    async def _run_dast_scan_impl(
        self, targets: Optional[List[str]] = None
    ) -> DASTScanResult: ...


class ScanningMixin:
    """Mixin providing SAST/DAST/Full scanning capabilities."""

    async def run_full_scan(self: ScanningProtocol, days_back: int = 7) -> ScanResult:
        """Run a full CVE scan across all sources.

        Args:
            days_back: Days to look back

        Returns:
            ScanResult with scan statistics
        """
        with _tracer.start_span(
            "cve_hunter.run_full_scan",
            attributes={
                "cve_hunter.days_back": days_back,
                "cve_hunter.sources": ",".join(self.config.enabled_sources),
            },
        ):
            return await self._run_full_scan_impl(days_back)

    async def _run_full_scan_impl(self: ScanningProtocol, days_back: int) -> ScanResult:
        logger.info("Starting full CVE scan", extra={"days_back": days_back})

        self._update_agent_status("scanner-1", AgentTaskStatus.SCANNING)
        self._add_discovery_log(
            f"SCANNER: Initiating full CVE scan (days_back={days_back})..."
        )

        task = Task(
            id=str(uuid4()),
            parameters={"name": "full_cve_scan"},
            description=f"Scan all CVE sources for last {days_back} days",
            required_capabilities=["nvd", "github"],
            priority=TaskPriority.LOW,
        )
        await self._colony.submit_task(task)

        cves_found = 0
        new_cves_count = 0
        errors: List[str] = []
        result = ScanResult(
            scan_id=str(uuid4()),
            source=CVESource.NVD,
            started_at=datetime.now(timezone.utc),
        )

        try:
            scan_tasks = []
            if "nvd" in self.config.enabled_sources:
                scan_tasks.append(self._scanner.scan_nvd(days_back=days_back))
            if "github" in self.config.enabled_sources:
                scan_tasks.append(self._scanner.scan_github())
            if "cisa_kev" in self.config.enabled_sources:
                scan_tasks.append(self._scanner.scan_cisa_kev())
            if "osv" in self.config.enabled_sources:
                scan_tasks.append(self._scanner.scan_osv())

            new_cves: List[CVERecord] = []

            for scan_gen in scan_tasks:
                try:
                    async for cve in scan_gen:
                        cves_found += 1
                        async with self._cache_lock:
                            is_new = cve.cve_id not in self._cve_cache
                            if is_new:
                                self._cve_cache[cve.cve_id] = cve
                        if is_new:
                            new_cves.append(cve)
                            new_cves_count += 1
                            if self._should_alert(cve):
                                await self._create_alert(cve)
                except Exception as e:
                    logger.error(
                        "Error during source scan",
                        extra={"error": str(e)},
                    )
                    errors.append(str(e))

            result.completed_at = datetime.now(timezone.utc)
            result.success = not errors
            result.cves_found = cves_found
            result.new_cves = new_cves_count
            result.errors = errors
            if result.completed_at and result.started_at:
                result.duration_seconds = (
                    result.completed_at - result.started_at
                ).total_seconds()

            self._scan_results.append(result)
            self.metrics.record_scan(
                source=result.source.value,
                duration=result.duration_seconds or 0.0,
                cves_found=cves_found,
                new_cves=new_cves_count,
                errors=len(errors),
            )
            self.metrics.set_cve_cache_size(len(self._cve_cache))

            if new_cves:
                await self._analyze_new_cves(new_cves)
            await self._store_cves_in_memory(new_cves)

            self._colony.complete_task(task.id, success=True, result=result)
            await self._emit_scan_completed(result)

            logger.info(
                "Scan complete",
                extra={
                    "scan_id": result.scan_id,
                    "cves_found": result.cves_found,
                    "new_cves": result.new_cves,
                    "duration_s": result.duration_seconds,
                },
            )

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            self._colony.complete_task(task.id, success=False)
            result = ScanResult(
                scan_id=str(uuid4()),
                source=CVESource.NVD,
                started_at=datetime.now(timezone.utc),
                success=False,
                errors=[str(e)],
            )

        finally:
            self._update_agent_status("scanner-1", AgentTaskStatus.IDLE)
            self._add_discovery_log(
                f"SCANNER: Scan finished. Total: {result.cves_found}, New: {result.new_cves}"
            )

        return result

    async def run_sast_scan(
        self: ScanningProtocol,
        paths: Optional[List[str]] = None,
    ) -> SASTScanResult:
        """Run a SAST scan on local code repositories.

        Args:
            paths: Optional list of local paths to scan (defaults to config)

        Returns:
            SASTScanResult with scan statistics and findings
        """
        with _tracer.start_span(
            "cve_hunter.run_sast_scan",
            attributes={
                "cve_hunter.paths_count": len(paths or self.config.sast_paths or [])
            },
        ):
            return await self._run_sast_scan_impl(paths)

    async def _run_sast_scan_impl(
        self: ScanningProtocol,
        paths: Optional[List[str]] = None,
    ) -> SASTScanResult:
        result = SASTScanResult(
            scan_id=str(uuid4()),
            started_at=datetime.now(timezone.utc),
        )

        if not self.config.enable_sast:
            result.completed_at = datetime.now(timezone.utc)
            return result

        scan_paths = paths or self.config.sast_paths
        if not scan_paths:
            result.completed_at = datetime.now(timezone.utc)
            return result

        self._update_agent_status(
            "discovery-1", AgentTaskStatus.DISCOVERING, "SAST Scan"
        )
        self._add_discovery_log(
            f"SAST: Starting scan across {len(scan_paths)} path(s)..."
        )

        try:
            repo_content, files_scanned = self.findings_handler.collect_repo_content(
                scan_paths
            )
            result.files_scanned = files_scanned

            findings = await self._discovery.scan_code_repository(repo_content)
            sast_findings: List[SASTFinding] = []
            for finding in findings:
                severity = pattern_to_severity(finding.get("pattern", ""))
                sast_findings.append(
                    SASTFinding(
                        finding_id=str(uuid4()),
                        file_path=finding.get("source", "unknown"),
                        pattern=finding.get("pattern", "unknown"),
                        confidence=float(finding.get("confidence", 0.0)),
                        severity=severity,
                        context=finding.get("context"),
                        source="sast",
                        engine="pattern",
                    )
                )

            semgrep_findings = await self.sast_tools_handler.run_semgrep(scan_paths)
            if semgrep_findings:
                sast_findings.extend(semgrep_findings)

            codeql_findings = await self.sast_tools_handler.run_codeql()
            if codeql_findings:
                sast_findings.extend(codeql_findings)

            result.findings = sast_findings
            result.findings_count = len(sast_findings)
            self._sast_findings = sast_findings[-500:]
            self._sast_scan_results.append(result)

        finally:
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at and result.completed_at:
                result.duration_seconds = (
                    result.completed_at - result.started_at
                ).total_seconds()

            self._update_agent_status("discovery-1", AgentTaskStatus.IDLE)
            self._add_discovery_log(
                f"SAST: Finished. Files: {result.files_scanned}, Findings: {result.findings_count}"
            )

        return result

    async def run_dast_scan(
        self: ScanningProtocol,
        targets: Optional[List[str]] = None,
    ) -> DASTScanResult:
        """Run a DAST scan against configured targets.

        Args:
            targets: Optional list of base URLs to scan (defaults to config)

        Returns:
            DASTScanResult with scan statistics and findings
        """
        with _tracer.start_span(
            "cve_hunter.run_dast_scan",
            attributes={
                "cve_hunter.targets_count": len(
                    targets or self.config.dast_targets or []
                )
            },
        ):
            return await self._run_dast_scan_impl(targets)

    async def _run_dast_scan_impl(
        self: ScanningProtocol,
        targets: Optional[List[str]] = None,
    ) -> DASTScanResult:
        result = DASTScanResult(
            scan_id=str(uuid4()),
            started_at=datetime.now(timezone.utc),
        )

        if not self.config.enable_dast:
            result.completed_at = datetime.now(timezone.utc)
            return result

        scan_targets = targets or self.config.dast_targets
        if not scan_targets:
            result.completed_at = datetime.now(timezone.utc)
            return result

        self._update_agent_status(
            "discovery-1", AgentTaskStatus.DISCOVERING, "DAST Scan"
        )
        self._add_discovery_log(
            f"DAST: Starting scan across {len(scan_targets)} target(s)..."
        )

        findings: List[DASTFinding] = []
        max_pages = max(1, self.config.dast_max_pages)

        try:
            async with httpx.AsyncClient(
                timeout=self.config.dast_request_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "CVE-Hunter/1.0"},
            ) as client:
                for target in scan_targets:
                    target = target.strip()
                    if not target:
                        continue

                    target_origin = urlparse(target).netloc
                    queue: deque[str] = deque([target])
                    visited: set[str] = set()

                    while queue and len(visited) < max_pages:
                        url = queue.popleft()
                        if url in visited:
                            continue
                        visited.add(url)

                        try:
                            resp = await client.get(url)
                        except httpx.RequestError:
                            continue

                        text = resp.text or ""
                        analysis = (
                            await self._discovery.analyze_text_for_vulnerabilities(
                                text, source=url
                            )
                        )

                        for finding in analysis:
                            severity = pattern_to_severity(finding.get("pattern", ""))
                            findings.append(
                                DASTFinding(
                                    finding_id=str(uuid4()),
                                    url=url,
                                    pattern=finding.get("pattern", "unknown"),
                                    confidence=float(finding.get("confidence", 0.0)),
                                    severity=severity,
                                    context=finding.get("context"),
                                    source="dast",
                                    engine="crawler",
                                )
                            )

                        for link in self.dast_tools_handler.extract_links(
                            text, base_url=url
                        ):
                            parsed = urlparse(link)
                            if parsed.netloc and parsed.netloc != target_origin:
                                continue
                            if link not in visited:
                                queue.append(link)

                    zap_findings = await self.dast_tools_handler.run_zap(target)
                    if zap_findings:
                        findings.extend(zap_findings)

                    result.targets_scanned += 1

        finally:
            result.completed_at = datetime.now(timezone.utc)
            result.findings = findings
            result.findings_count = len(findings)
            self._dast_findings = findings[-500:]
            self._dast_scan_results.append(result)

            if result.started_at and result.completed_at:
                result.duration_seconds = (
                    result.completed_at - result.started_at
                ).total_seconds()

            self._update_agent_status("discovery-1", AgentTaskStatus.IDLE)
            self._add_discovery_log(
                f"DAST: Finished. Targets: {result.targets_scanned}, Findings: {result.findings_count}"
            )

        return result

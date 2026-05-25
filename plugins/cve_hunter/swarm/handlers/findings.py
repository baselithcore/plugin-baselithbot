"""Findings Handler for CVE Hunter Swarm.

Contains logic for processing and normalizing findings:
- Unified finding normalization
- Deduplication
- Risk score calculation
- Repository content collection
"""

import fnmatch
from core.observability.logging import get_logger
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from ...config import CVEHunterConfig
    from ...models import CVESeverity, DASTFinding, SASTFinding
    from ...utils.hashing import stable_finding_id
    from ...utils.patterns import extract_cwe_ids, is_code_file, pattern_to_severity
except ImportError:
    from plugins.cve_hunter.config import CVEHunterConfig
    from plugins.cve_hunter.models import CVESeverity, DASTFinding, SASTFinding
    from plugins.cve_hunter.utils.hashing import stable_finding_id
    from plugins.cve_hunter.utils.patterns import (
        extract_cwe_ids,
        is_code_file,
        pattern_to_severity,
    )

logger = get_logger(__name__)


class FindingsHandler:
    """Handler for finding normalization and processing.

    Extracts finding-specific logic from the coordinator for better
    maintainability and separation of concerns.
    """

    def __init__(
        self,
        config: CVEHunterConfig,
        log_callback: Optional[Callable[[str, bool, bool], None]] = None,
    ):
        """Initialize findings handler.

        Args:
            config: CVE Hunter configuration
            log_callback: Optional callback for logging (message, is_alert, is_error)
        """
        self.config = config
        self._log_callback = log_callback

    def _add_log(
        self, message: str, is_alert: bool = False, is_error: bool = False
    ) -> None:
        """Add a log entry via callback if available."""
        if self._log_callback:
            self._log_callback(message, is_alert, is_error)
        else:
            if is_error:
                logger.error(message)
            elif is_alert:
                logger.warning(message)
            else:
                logger.info(message)

    # =========================================================================
    # Repository Content Collection
    # =========================================================================

    def collect_repo_content(self, paths: List[str]) -> Tuple[Dict[str, str], int]:
        """Collect code files from local paths for SAST scanning.

        Args:
            paths: List of directory paths to scan

        Returns:
            Tuple of (file_path -> content dict, files_scanned count)
        """
        repo_content: Dict[str, str] = {}
        files_scanned = 0

        max_files = max(1, self.config.sast_max_files)
        max_size_bytes = max(1, self.config.sast_max_file_size_kb) * 1024

        for root in paths:
            if files_scanned >= max_files:
                break

            if not os.path.exists(root):
                self._add_log(f"SAST: Skipping missing path: {root}")
                continue

            for dirpath, dirnames, filenames in os.walk(root):
                rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
                if self.is_excluded_path(rel_dir):
                    dirnames[:] = []
                    continue

                dirnames[:] = [
                    d
                    for d in dirnames
                    if not self.is_excluded_path(
                        os.path.join(rel_dir, d).replace(os.sep, "/")
                    )
                ]

                for filename in filenames:
                    if files_scanned >= max_files:
                        break

                    rel_path = os.path.join(rel_dir, filename).replace(os.sep, "/")
                    if self.is_excluded_path(rel_path):
                        continue

                    file_path = os.path.join(dirpath, filename)
                    if not is_code_file(file_path):
                        continue

                    try:
                        if os.path.getsize(file_path) > max_size_bytes:
                            continue
                    except OSError:
                        continue

                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            repo_content[file_path] = f.read()
                            files_scanned += 1
                    except OSError:
                        continue

        return repo_content, files_scanned

    def is_excluded_path(self, rel_path: str) -> bool:
        """Check if a relative path matches any exclude glob.

        Args:
            rel_path: Relative path to check

        Returns:
            True if path should be excluded
        """
        if rel_path.startswith("./"):
            rel_path = rel_path[2:]
        if rel_path in ("", "."):
            return False
        for pattern in self.config.sast_exclude_globs:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
        return False

    # =========================================================================
    # Finding Normalization
    # =========================================================================

    def build_unified_findings(
        self,
        sast_findings: List[SASTFinding],
        dast_findings: List[DASTFinding],
        discovery_findings: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Normalize and deduplicate findings from multiple sources.

        Args:
            sast_findings: List of SAST findings
            dast_findings: List of DAST findings
            discovery_findings: List of raw discovery findings

        Returns:
            List of normalized, deduplicated finding dictionaries
        """
        raw: List[Dict[str, Any]] = []

        for sast_finding in sast_findings:
            cwe_ids = extract_cwe_ids(sast_finding.pattern, sast_finding.rule_id)
            raw.append(
                self.normalize_finding(
                    finding_id=sast_finding.finding_id,
                    source_type="sast",
                    engine=sast_finding.engine,
                    location=sast_finding.file_path,
                    pattern=sast_finding.pattern,
                    cwe_ids=cwe_ids,
                    severity=sast_finding.severity,
                    confidence=sast_finding.confidence,
                    context=sast_finding.context,
                    rule_id=sast_finding.rule_id,
                    feedback=sast_finding.feedback,
                )
            )

        for dast_finding in dast_findings:
            cwe_ids = extract_cwe_ids(dast_finding.pattern, dast_finding.rule_id)
            raw.append(
                self.normalize_finding(
                    finding_id=dast_finding.finding_id,
                    source_type="dast",
                    engine=dast_finding.engine,
                    location=dast_finding.url,
                    pattern=dast_finding.pattern,
                    cwe_ids=cwe_ids,
                    severity=dast_finding.severity,
                    confidence=dast_finding.confidence,
                    context=dast_finding.context,
                    rule_id=dast_finding.rule_id,
                    feedback=dast_finding.feedback,
                )
            )

        for discovery_finding in discovery_findings:
            pattern = discovery_finding.get("pattern", "unknown")
            source = discovery_finding.get("source", "unknown")
            context = discovery_finding.get("context")
            confidence = float(discovery_finding.get("confidence", 0.0))
            severity = pattern_to_severity(pattern)
            cwe_ids = extract_cwe_ids(pattern, None)
            stable_id = stable_finding_id(pattern, source, context)

            raw.append(
                self.normalize_finding(
                    finding_id=stable_id,
                    source_type="discovery",
                    engine="signal",
                    location=source,
                    pattern=pattern,
                    cwe_ids=cwe_ids,
                    severity=severity,
                    confidence=confidence,
                    context=context,
                    rule_id=None,
                    feedback=None,
                )
            )

        return self.dedupe_findings(raw)

    def normalize_finding(
        self,
        finding_id: str,
        source_type: str,
        engine: Optional[str],
        location: str,
        pattern: str,
        cwe_ids: List[str],
        severity: CVESeverity,
        confidence: float,
        context: Optional[str],
        rule_id: Optional[str],
        feedback: Optional[str],
    ) -> Dict[str, Any]:
        """Normalize a finding into a unified structure with score.

        Args:
            finding_id: Unique finding ID
            source_type: Type of source (sast, dast, discovery)
            engine: Tool that produced the finding
            location: File path or URL
            pattern: Vulnerability pattern
            cwe_ids: Related CWE identifiers
            severity: Severity level
            confidence: Confidence score (0.0-1.0)
            context: Additional context
            rule_id: Tool rule ID
            feedback: User feedback if any

        Returns:
            Normalized finding dictionary
        """
        score = self.calculate_risk_score(severity, confidence)
        return {
            "finding_id": finding_id,
            "source_type": source_type,
            "engine": engine,
            "location": location,
            "pattern": pattern,
            "cwe_ids": cwe_ids,
            "severity": severity.value,
            "confidence": round(confidence, 3),
            "score": score,
            "context": context,
            "rule_id": rule_id,
            "feedback": feedback,
        }

    def dedupe_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate findings by source/pattern/location.

        Args:
            findings: List of findings to deduplicate

        Returns:
            Deduplicated list of findings
        """
        deduped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        for finding in findings:
            key = (
                finding.get("source_type", ""),
                finding.get("pattern", ""),
                finding.get("location", ""),
            )
            existing = deduped.get(key)
            if not existing:
                deduped[key] = finding
                continue

            if finding.get("score", 0.0) > existing.get("score", 0.0):
                deduped[key] = finding
            else:
                existing_cwes = set(existing.get("cwe_ids", []))
                existing_cwes.update(finding.get("cwe_ids", []))
                existing["cwe_ids"] = sorted(existing_cwes)

        return list(deduped.values())

    def calculate_risk_score(self, severity: CVESeverity, confidence: float) -> float:
        """Calculate a normalized risk score using severity and confidence.

        Args:
            severity: Severity level
            confidence: Confidence score (0.0-1.0)

        Returns:
            Risk score (0.0-10.0)
        """
        severity_map = {
            CVESeverity.CRITICAL: 9.5,
            CVESeverity.HIGH: 8.0,
            CVESeverity.MEDIUM: 5.0,
            CVESeverity.LOW: 2.0,
            CVESeverity.NONE: 0.0,
        }
        base = severity_map.get(severity, 0.0)
        confidence = max(0.0, min(1.0, confidence))
        score = base * (0.5 + (confidence / 2.0))
        return round(score, 2)

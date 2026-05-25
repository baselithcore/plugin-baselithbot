"""Correlations Handler for CVE Hunter Swarm.

Contains logic for correlating findings with CVEs and attack patterns:
- Finding-to-CVE correlation via CWE
- Attack chain pattern detection
"""

from core.observability.logging import get_logger
from typing import Any, Callable, Dict, List, Optional
from uuid import NAMESPACE_DNS, uuid5

try:
    from ...models import CVERecord
    from .feedback import FeedbackHandler
except ImportError:
    from plugins.cve_hunter.models import CVERecord
    from plugins.cve_hunter.swarm.handlers.feedback import FeedbackHandler

logger = get_logger(__name__)


class CorrelationsHandler:
    """Handler for finding-to-CVE and attack pattern correlations.

    Extracts correlation logic from the coordinator for better
    maintainability and separation of concerns.
    """

    # Attack chain patterns for detection
    ATTACK_CHAIN_PATTERNS = [
        {
            "name": "Reconnaissance to RCE",
            "cwes": [["CWE-200", "CWE-209"], ["CWE-94", "CWE-78"]],
            "techniques": ["T1595", "T1059"],
        },
        {
            "name": "Auth Bypass to Privilege Escalation",
            "cwes": [["CWE-287", "CWE-306"], ["CWE-269", "CWE-732"]],
            "techniques": ["T1078", "T1068"],
        },
        {
            "name": "Injection to Data Exfiltration",
            "cwes": [["CWE-89", "CWE-79"], ["CWE-200", "CWE-522"]],
            "techniques": ["T1190", "T1005"],
        },
        {
            "name": "Path Traversal to Sensitive Data",
            "cwes": [["CWE-22", "CWE-23"], ["CWE-200", "CWE-532"]],
            "techniques": ["T1083", "T1005"],
        },
        {
            "name": "SSRF to Cloud Metadata",
            "cwes": [["CWE-918"], ["CWE-522", "CWE-200"]],
            "techniques": ["T1552", "T1656"],
        },
    ]

    def __init__(
        self,
        feedback_handler: FeedbackHandler,
        correlator: Any,  # CVECorrelatorAgent
        log_callback: Optional[Callable[[str, bool, bool], None]] = None,
    ):
        """Initialize correlations handler.

        Args:
            feedback_handler: Handler for feedback operations
            correlator: CVECorrelatorAgent instance for chain detection
            log_callback: Optional callback for logging
        """
        self.feedback_handler = feedback_handler
        self._correlator = correlator
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
    # Finding-to-CVE Correlation
    # =========================================================================

    def correlate_findings_with_cves(
        self,
        unified: List[Dict[str, Any]],
        cve_cache: Dict[str, CVERecord],
    ) -> List[Dict[str, Any]]:
        """Correlate unified findings to known CVEs via CWE matches.

        Args:
            unified: List of unified finding dictionaries
            cve_cache: Dictionary of CVE ID -> CVERecord

        Returns:
            List of correlation dictionaries
        """
        cwe_to_findings: Dict[str, List[Dict[str, Any]]] = {}
        for finding in unified:
            for cwe in finding.get("cwe_ids", []):
                cwe_to_findings.setdefault(cwe, []).append(finding)

        correlations: Dict[tuple, Dict[str, Any]] = {}
        for cve in cve_cache.values():
            for cwe in cve.cwe_ids:
                matches = cwe_to_findings.get(cwe, [])
                if not matches:
                    continue

                key = (cve.cve_id, cwe)
                confidence = max(m["confidence"] for m in matches)
                cid = str(uuid5(NAMESPACE_DNS, f"{cve.cve_id}|{cwe}"))
                correlations[key] = {
                    "correlation_id": cid,
                    "correlation_type": "cwe_match",
                    "cve_id": cve.cve_id,
                    "cwe_id": cwe,
                    "finding_ids": [m["finding_id"] for m in matches],
                    "confidence": round(confidence, 3),
                    "description": f"Findings match {cwe} in {cve.cve_id}",
                    "feedback": self.feedback_handler.get_outcome(
                        self.feedback_handler.finding_correlation_feedback,
                        cid,
                    ),
                }

        return list(correlations.values())

    # =========================================================================
    # Attack Pattern Correlation
    # =========================================================================

    def correlate_findings_with_attack_patterns(
        self,
        unified: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Correlate findings to attack-chain patterns by CWE stages.

        Args:
            unified: List of unified finding dictionaries

        Returns:
            List of attack chain candidate dictionaries
        """
        cwe_to_findings: Dict[str, List[Dict[str, Any]]] = {}
        for finding in unified:
            for cwe in finding.get("cwe_ids", []):
                cwe_to_findings.setdefault(cwe, []).append(finding)

        candidates: List[Dict[str, Any]] = []
        for pattern in self.ATTACK_CHAIN_PATTERNS:
            matched_stages: List[Dict[str, Any]] = []
            for idx, stage_cwes in enumerate(pattern.get("cwes", []), start=1):
                stage_findings: List[Dict[str, Any]] = []
                for cwe in stage_cwes:
                    stage_findings.extend(cwe_to_findings.get(cwe, []))
                if stage_findings:
                    matched_stages.append(
                        {
                            "stage": idx,
                            "cwe_ids": stage_cwes,
                            "finding_ids": [f["finding_id"] for f in stage_findings],
                        }
                    )

            if len(matched_stages) >= 2:
                confidence = min(0.95, 0.4 + (0.2 * (len(matched_stages) - 1)))
                chain_id = str(
                    uuid5(
                        NAMESPACE_DNS,
                        f"{pattern['name']}|{len(matched_stages)}",
                    )
                )
                candidates.append(
                    {
                        "chain_id": chain_id,
                        "name": pattern["name"],
                        "matched_stages": matched_stages,
                        "confidence": round(confidence, 3),
                        "description": "Findings align with attack-chain CWE stages.",
                        "mitre_techniques": pattern.get("techniques", []),
                        "feedback": self.feedback_handler.get_outcome(
                            self.feedback_handler.attack_chain_feedback, chain_id
                        ),
                    }
                )

        return candidates

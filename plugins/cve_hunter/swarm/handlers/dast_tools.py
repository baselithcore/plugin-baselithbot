"""DAST Tools Handler for CVE Hunter Swarm.

Contains logic for running dynamic analysis security tools:
- OWASP ZAP
- Link extraction/crawling utilities
"""

import asyncio
import json
from core.observability.logging import get_logger
import os
import re
import subprocess  # nosec B404
import tempfile
from typing import Callable, List, Optional
from urllib.parse import urljoin
from uuid import uuid4

try:
    from ...config import CVEHunterConfig
    from ...models import CVESeverity, DASTFinding
except ImportError:
    from plugins.cve_hunter.config import CVEHunterConfig
    from plugins.cve_hunter.models import CVESeverity, DASTFinding

logger = get_logger(__name__)


class DASTToolsHandler:
    """Handler for DAST tooling (OWASP ZAP).

    Extracts tool-specific logic from the coordinator for better
    maintainability and separation of concerns.
    """

    def __init__(
        self,
        config: CVEHunterConfig,
        log_callback: Optional[Callable[[str, bool, bool], None]] = None,
    ):
        """Initialize DAST tools handler.

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
    # Link Extraction
    # =========================================================================

    def extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and normalize links from HTML.

        Args:
            html: HTML content to parse
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute URLs found in the HTML
        """
        urls: List[str] = []
        for match in re.findall(r'href=["\']([^"\']*)["\']', html, flags=re.IGNORECASE):
            if match.startswith("javascript:") or match.startswith("mailto:"):
                continue
            urls.append(urljoin(base_url, match))
        for match in re.findall(r'src=["\']([^"\']*)["\']', html, flags=re.IGNORECASE):
            if match.startswith("data:"):
                continue
            urls.append(urljoin(base_url, match))
        return urls

    # =========================================================================
    # OWASP ZAP Integration
    # =========================================================================

    async def run_zap(self, target: str) -> List[DASTFinding]:
        """Run OWASP ZAP baseline scan and convert results to DAST findings.

        Args:
            target: Target URL to scan

        Returns:
            List of DASTFinding objects
        """
        if not self.config.enable_zap:
            return []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as report_file:
            report_path = report_file.name

        cmd: List[str] = [self.config.zap_command, "-t", target, "-J", report_path]
        if self.config.zap_args:
            cmd.extend(self.config.zap_args)

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.config.zap_timeout_seconds,
            )
        except FileNotFoundError:
            self._add_log("DAST: ZAP command not found in PATH.", is_error=True)
            return []
        except subprocess.TimeoutExpired:
            self._add_log("DAST: ZAP scan timed out.", is_error=True)
            return []
        finally:
            if os.path.exists(report_path) and os.path.getsize(report_path) == 0:
                try:
                    os.remove(report_path)
                except OSError:
                    pass  # nosec B110

        if result.returncode not in (0, 1):
            self._add_log(f"DAST: ZAP failed ({result.returncode}).", is_error=True)
            return []

        if not os.path.exists(report_path):
            return []

        try:
            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._add_log("DAST: ZAP report parse failed.", is_error=True)
            return []
        finally:
            try:
                os.remove(report_path)
            except OSError:
                pass

        findings: List[DASTFinding] = []
        for site in data.get("site", []):
            for alert in site.get("alerts", []):
                riskcode = str(alert.get("riskcode", "0"))
                severity = self._zap_risk_to_severity(riskcode)
                confidence = self._zap_risk_to_confidence(riskcode)
                instances = alert.get("instances", []) or []
                target_url = target
                evidence = None
                if instances:
                    target_url = instances[0].get("uri") or target
                    evidence = instances[0].get("evidence")

                desc = alert.get("desc") or ""
                riskdesc = alert.get("riskdesc") or ""
                context = " ".join(part for part in [riskdesc, desc, evidence] if part)
                if not context:
                    context = alert.get("alert", "ZAP finding")

                findings.append(
                    DASTFinding(
                        finding_id=str(uuid4()),
                        url=target_url,
                        pattern=alert.get("alert", "zap_finding"),
                        confidence=confidence,
                        severity=severity,
                        context=context,
                        source="dast",
                        engine="zap",
                        rule_id=alert.get("pluginid"),
                    )
                )

        return findings

    def _zap_risk_to_severity(self, riskcode: str) -> CVESeverity:
        """Map ZAP risk code to CVE severity."""
        if riskcode == "3":
            return CVESeverity.HIGH
        if riskcode == "2":
            return CVESeverity.MEDIUM
        return CVESeverity.LOW

    def _zap_risk_to_confidence(self, riskcode: str) -> float:
        """Map ZAP risk code to confidence score."""
        if riskcode == "3":
            return 0.85
        if riskcode == "2":
            return 0.65
        if riskcode == "1":
            return 0.45
        return 0.3

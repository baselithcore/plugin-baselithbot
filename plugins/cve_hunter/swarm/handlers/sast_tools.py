"""SAST Tools Handler for CVE Hunter Swarm.

Contains logic for running static analysis security tools:
- Semgrep
- CodeQL
"""

import asyncio
import json
from core.observability.logging import get_logger
import os
import subprocess  # nosec B404
import tempfile
from typing import Callable, List, Optional
from uuid import uuid4

try:
    from ...config import CVEHunterConfig
    from ...models import CVESeverity, SASTFinding
except ImportError:
    from plugins.cve_hunter.config import CVEHunterConfig
    from plugins.cve_hunter.models import CVESeverity, SASTFinding

logger = get_logger(__name__)


class SASTToolsHandler:
    """Handler for SAST tooling (Semgrep, CodeQL).

    Extracts tool-specific logic from the coordinator for better
    maintainability and separation of concerns.
    """

    def __init__(
        self,
        config: CVEHunterConfig,
        log_callback: Optional[Callable[[str, bool, bool], None]] = None,
    ):
        """Initialize SAST tools handler.

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
    # Semgrep Integration
    # =========================================================================

    async def run_semgrep(self, paths: List[str]) -> List[SASTFinding]:
        """Run Semgrep and convert results to SAST findings.

        Args:
            paths: List of paths to scan

        Returns:
            List of SASTFinding objects
        """
        if not self.config.enable_semgrep:
            return []

        configs: List[str] = []
        if self.config.semgrep_config_path:
            configs.append(self.config.semgrep_config_path)
        if self.config.semgrep_rules:
            configs.extend(self.config.semgrep_rules)

        if not configs:
            self._add_log(
                "SAST: Semgrep enabled but no configs specified.", is_error=True
            )
            return []

        cmd: List[str] = ["semgrep", "--json", "--quiet"]
        for config in configs:
            cmd.extend(["--config", config])
        cmd.extend(paths)

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.config.semgrep_timeout_seconds,
            )
        except FileNotFoundError:
            self._add_log("SAST: Semgrep not found in PATH.", is_error=True)
            return []
        except subprocess.TimeoutExpired:
            self._add_log("SAST: Semgrep timed out.", is_error=True)
            return []

        if result.returncode not in (0, 1):
            self._add_log(f"SAST: Semgrep failed ({result.returncode}).", is_error=True)
            return []

        try:
            data = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            self._add_log("SAST: Semgrep output parse failed.", is_error=True)
            return []

        findings: List[SASTFinding] = []
        for finding in data.get("results", []):
            extra = finding.get("extra", {}) or {}
            severity_str = str(extra.get("severity", "INFO"))
            severity = self._semgrep_severity_to_cve(severity_str)
            start = finding.get("start", {}) or {}
            line = start.get("line")
            message = extra.get("message", "Semgrep finding")
            context = message
            if line:
                context = f"{message} (line {line})"

            findings.append(
                SASTFinding(
                    finding_id=str(uuid4()),
                    file_path=finding.get("path", "unknown"),
                    pattern=extra.get("metadata", {}).get("category")
                    or finding.get("check_id", "semgrep"),
                    confidence=self._semgrep_confidence(severity_str),
                    severity=severity,
                    context=context,
                    source="sast",
                    engine="semgrep",
                    rule_id=finding.get("check_id"),
                )
            )

        return findings

    def _semgrep_severity_to_cve(self, severity: str) -> CVESeverity:
        """Map Semgrep severity to CVE severity."""
        normalized = severity.strip().lower()
        if normalized == "error":
            return CVESeverity.HIGH
        if normalized == "warning":
            return CVESeverity.MEDIUM
        return CVESeverity.LOW

    def _semgrep_confidence(self, severity: str) -> float:
        """Map Semgrep severity to a confidence score."""
        normalized = severity.strip().lower()
        if normalized == "error":
            return 0.9
        if normalized == "warning":
            return 0.7
        return 0.5

    # =========================================================================
    # CodeQL Integration
    # =========================================================================

    async def run_codeql(self) -> List[SASTFinding]:
        """Run CodeQL analysis and convert results to SAST findings.

        Returns:
            List of SASTFinding objects
        """
        if not self.config.enable_codeql:
            return []

        db_path = self.config.codeql_database_path
        if not db_path:
            self._add_log(
                "SAST: CodeQL enabled but no database path provided.", is_error=True
            )
            return []

        if not os.path.exists(db_path):
            if not self.config.codeql_autocreate:
                self._add_log(
                    f"SAST: CodeQL database not found at {db_path}.",
                    is_error=True,
                )
                return []

            if not self.config.codeql_source_root or not self.config.codeql_languages:
                self._add_log(
                    "SAST: CodeQL autocreate requires source root and languages.",
                    is_error=True,
                )
                return []

            create_cmd: List[str] = [
                self.config.codeql_cli_path,
                "database",
                "create",
                db_path,
                "--source-root",
                self.config.codeql_source_root,
                "--language",
                ",".join(self.config.codeql_languages),
                "--overwrite",
            ]

            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    create_cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.config.codeql_timeout_seconds,
                )
            except FileNotFoundError:
                self._add_log("SAST: CodeQL CLI not found in PATH.", is_error=True)
                return []
            except subprocess.TimeoutExpired:
                self._add_log("SAST: CodeQL database create timed out.", is_error=True)
                return []

            if result.returncode != 0:
                self._add_log(
                    f"SAST: CodeQL database create failed ({result.returncode}).",
                    is_error=True,
                )
                return []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sarif", delete=False
        ) as report_file:
            report_path = report_file.name

        analyze_cmd: List[str] = [
            self.config.codeql_cli_path,
            "database",
            "analyze",
            db_path,
            self.config.codeql_query_suite,
            "--format=sarifv2.1.0",
            "--output",
            report_path,
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                analyze_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.config.codeql_timeout_seconds,
            )
        except FileNotFoundError:
            self._add_log("SAST: CodeQL CLI not found in PATH.", is_error=True)
            return []
        except subprocess.TimeoutExpired:
            self._add_log("SAST: CodeQL analyze timed out.", is_error=True)
            return []

        if result.returncode not in (0, 1):
            self._add_log(
                f"SAST: CodeQL analyze failed ({result.returncode}).", is_error=True
            )
            return []

        if not os.path.exists(report_path):
            return []

        try:
            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._add_log("SAST: CodeQL report parse failed.", is_error=True)
            return []
        finally:
            try:
                os.remove(report_path)
            except OSError:
                pass  # nosec B110

        findings: List[SASTFinding] = []
        for run in data.get("runs", []):
            for result_item in run.get("results", []):
                level = str(result_item.get("level", "warning"))
                severity = self._codeql_level_to_severity(level)
                confidence = self._codeql_level_to_confidence(level)
                rule_id = result_item.get("ruleId") or "codeql_finding"
                message = (result_item.get("message") or {}).get(
                    "text"
                ) or "CodeQL finding"

                file_path = "unknown"
                context = message
                locations = result_item.get("locations") or []
                if locations:
                    physical = locations[0].get("physicalLocation") or {}
                    artifact = physical.get("artifactLocation") or {}
                    file_path = artifact.get("uri") or file_path
                    region = physical.get("region") or {}
                    line = region.get("startLine")
                    if line:
                        context = f"{message} (line {line})"

                findings.append(
                    SASTFinding(
                        finding_id=str(uuid4()),
                        file_path=file_path,
                        pattern=rule_id,
                        confidence=confidence,
                        severity=severity,
                        context=context,
                        source="sast",
                        engine="codeql",
                        rule_id=rule_id,
                    )
                )

        return findings

    def _codeql_level_to_severity(self, level: str) -> CVESeverity:
        """Map CodeQL level to CVE severity."""
        normalized = level.strip().lower()
        if normalized == "error":
            return CVESeverity.HIGH
        if normalized == "warning":
            return CVESeverity.MEDIUM
        return CVESeverity.LOW

    def _codeql_level_to_confidence(self, level: str) -> float:
        """Map CodeQL level to a confidence score."""
        normalized = level.strip().lower()
        if normalized == "error":
            return 0.9
        if normalized == "warning":
            return 0.7
        return 0.5

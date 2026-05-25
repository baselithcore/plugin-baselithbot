from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService

logger = logging.getLogger(__name__)


class AuditIssue(BaseModel):
    """Represents a single issue found during audit."""

    category: str  # e.g., "PII", "Safety", "Hallucination"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    message: str
    snippet: Optional[str] = None


class AuditReport(BaseModel):
    """Complete audit report for an interaction."""

    is_safe: bool
    risk_score: float = 0.0  # 0.0 (safe) to 1.0 (unsafe)
    issues: List[AuditIssue] = Field(default_factory=list)
    action_taken: str = "OBSERVE"  # "OBSERVE", "BLOCK", "FLAG"


class AuditAgent:
    """
    Agent responsible for auditing interactions for quality, safety, and compliance.
    Designed to be non-intrusive and fail-open by default.
    """

    def __init__(self, service: ChatService) -> None:
        self.service = service
        self.logger = logger

    def evaluate_interaction(
        self, query: str, response: str, context: Optional[str] = None
    ) -> AuditReport:
        """
        Evaluates a user interaction (query + response).

        Args:
            query: User input
            response: Agent response
            context: Context used for generation (if applicable)

        Returns:
            AuditReport with findings
        """
        issues = []

        # 1. PII Scan (Heuristic)
        pii_issues = self._scan_pii(response)
        issues.extend(pii_issues)

        # 2. Safety/Injection Check (Heuristic)
        # Check output for leaked system prompts or bad patterns
        safety_issues = self._scan_safety(response)
        issues.extend(safety_issues)

        # 3. Quality/Hallucination Check (LLM - Placeholder for MVP)
        # To avoid latency, we skip LLM check in sync path for now
        # or we could make it async. For MVP, we stick to heuristics.

        # Calculate Risk Score
        risk_score = 0.0
        if any(i.severity == "CRITICAL" for i in issues):
            risk_score = 1.0
        elif any(i.severity == "HIGH" for i in issues):
            risk_score = 0.8
        elif any(i.severity == "MEDIUM" for i in issues):
            risk_score = 0.5
        elif issues:
            risk_score = 0.2

        is_safe = risk_score < 0.2

        report = AuditReport(
            is_safe=is_safe,
            risk_score=risk_score,
            issues=issues,
            action_taken="BLOCK" if not is_safe else "OBSERVE",
        )

        if not is_safe:
            self.logger.warning(
                f"AuditAgent: Unsafe interaction detected! Score: {risk_score}. Issues: {len(issues)}"
            )

        return report

    def _scan_pii(self, text: str) -> List[AuditIssue]:
        """Scans text for PII using regex."""
        issues = []

        # Email Regex
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        if re.search(email_pattern, text):
            issues.append(
                AuditIssue(
                    category="PII",
                    severity="MEDIUM",
                    message="Potential Email address detected in output.",
                    snippet="[EMAIL_REDACTED]",
                )
            )

        # Credit Card (Simple Luhn-like pattern check is too complex for regex alone, using simple digit grouping)
        # Matches typical 4-4-4-4 pattern
        cc_pattern = r"\b(?:\d{4}[-\s]){3}\d{4}\b"
        if re.search(cc_pattern, text):
            issues.append(
                AuditIssue(
                    category="PII",
                    severity="HIGH",
                    message="Potential Credit Card number detected.",
                )
            )

        return issues

    def _scan_safety(self, text: str) -> List[AuditIssue]:
        """Scans for safety violations."""
        issues = []

        # Check for leaked internal delimiters
        if "<EPHEMERAL_MESSAGE>" in text or "SYSTEM_PROMPT" in text:
            issues.append(
                AuditIssue(
                    category="Security",
                    severity="CRITICAL",
                    message="System internal delimiters leaked in output.",
                )
            )

        return issues

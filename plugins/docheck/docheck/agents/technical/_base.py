"""Rule contracts and helpers for DocCheck_Builtin technical rules."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from ...schemas.finding import Citation, Finding, PolicyRef, ReasoningStep, Severity
from ...schemas.state import Chunk

POLICY_ID = "DocCheck_Builtin"
POLICY_VERSION = "1.0.0"


@dataclass(frozen=True)
class RuleSpec:
    """Static metadata for a built-in deterministic rule."""

    rule_id: str
    title: str
    excerpt: str
    default_severity: Severity
    default_confidence: float


class Rule(Protocol):
    spec: RuleSpec

    def evaluate(self, chunk: Chunk) -> list[Finding]:
        """Return zero or more findings for the given chunk."""
        ...


def make_finding(
    *,
    spec: RuleSpec,
    chunk: Chunk,
    severity: Severity,
    confidence: float,
    explanation: str,
    suggestion: str | None,
    reasoning: list[ReasoningStep],
    match_start: int,
    match_end: int,
    snippet_pad: int = 80,
) -> Finding:
    """Build a glass-box compliant Finding with PolicyRef + Citation."""
    text = chunk.text or ""
    pad_lo = max(0, match_start - snippet_pad)
    pad_hi = min(len(text), match_end + snippet_pad)
    snippet = text[pad_lo:pad_hi]

    return Finding(
        id=f"f-{uuid.uuid4().hex[:8]}",
        severity=severity,
        rule_id=spec.rule_id,
        policy_ref=PolicyRef(
            id=spec.rule_id,
            policy_id=POLICY_ID,
            version=POLICY_VERSION,
            title=spec.title,
            excerpt=spec.excerpt,
        ),
        evidence=Citation(
            chunk_id=chunk.id,
            page=chunk.page,
            line_start=chunk.line_start,
            line_end=chunk.line_end,
            bbox=chunk.bbox,
            text=text,
            match_start=match_start,
            match_end=match_end,
            snippet=snippet,
        ),
        explanation=explanation,
        suggestion=suggestion,
        confidence=confidence,
        reasoning=reasoning,
    )


def step(
    n: int,
    agent: str,
    action: str,
    thought: str,
    *,
    inp: dict[str, Any] | None = None,
    out: dict[str, Any] | None = None,
) -> ReasoningStep:
    return ReasoningStep(
        step=n,
        agent=agent,
        action=action,
        thought=thought,
        input=inp,
        output=out,
    )

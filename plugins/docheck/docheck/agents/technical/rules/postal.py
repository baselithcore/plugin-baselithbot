"""FORMAT-CAP-IT — Italian postal code (CAP) sanity check.

Detects 5-digit codes near address-related lemmas where the CAP value is
out of the valid Italian range (00010-98168, plus reserved blocks).
Acts as INFO/WARN — not all 5-digit numbers are CAPs, but proximity to
address triggers makes false positives rare.
"""

from __future__ import annotations

import re

from ....schemas.finding import Finding, Severity
from ....schemas.state import Chunk
from .._base import RuleSpec, make_finding, step
from ..patterns import CAP_IT
from ..severity import is_enabled, resolve_severity

ADDR_TRIGGER = re.compile(r"\b(via|viale|piazza|corso|cap|c\.a\.p\.|località)\b", re.IGNORECASE)


def cap_in_range(cap: str) -> bool:
    if not (cap.isdigit() and len(cap) == 5):
        return False
    n = int(cap)
    return 10 <= n <= 98168


SPEC = RuleSpec(
    rule_id="FORMAT-CAP-IT",
    title="CAP italiano fuori range",
    excerpt="I CAP italiani devono rientrare nell'intervallo amministrativo (00010-98168).",
    default_severity="INFO",
    default_confidence=0.6,
)


class CapItRule:
    spec = SPEC

    def evaluate(self, chunk: Chunk) -> list[Finding]:
        if not is_enabled(self.spec.rule_id):
            return []
        text = chunk.text or ""
        if not ADDR_TRIGGER.search(text):
            return []
        out: list[Finding] = []
        seen: set[tuple[int, int]] = set()
        for m in CAP_IT.finditer(text):
            value = m.group(0)
            if cap_in_range(value):
                continue
            key = (m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            sev: Severity = resolve_severity(self.spec.rule_id, self.spec.default_severity)
            reasoning = [
                step(
                    1,
                    "TechnicalComplianceAgent",
                    "context_check",
                    "Trigger di indirizzo presente nel chunk → ammessa interpretazione CAP.",
                    out={"trigger_present": True},
                ),
                step(
                    2,
                    "TechnicalComplianceAgent",
                    "range_verify",
                    f"Valore '{value}' fuori range CAP IT (00010-98168).",
                    out={"value": value, "valid": False},
                ),
            ]
            out.append(
                make_finding(
                    spec=self.spec,
                    chunk=chunk,
                    severity=sev,
                    confidence=self.spec.default_confidence,
                    explanation=f"Possibile CAP '{value}' fuori range italiano.",
                    suggestion="Verificare il CAP riportato nell'indirizzo.",
                    reasoning=reasoning,
                    match_start=m.start(),
                    match_end=m.end(),
                )
            )
        return out

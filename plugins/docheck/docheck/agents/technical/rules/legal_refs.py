"""REF-LEGAL-MALFORMED — legal reference must include number/year.

Catches dangling refs like "ai sensi del D.Lgs." without "n. NNN/AAAA",
which obstruct downstream policy linking and make audit trails ambiguous.
"""

from __future__ import annotations

import re

from ....schemas.finding import Finding, Severity
from ....schemas.state import Chunk
from .._base import RuleSpec, make_finding, step
from ..severity import is_enabled, resolve_severity

# Capture lead lemma + up to 80 chars window to look for "n. X/YYYY" or "del DD/MM/YYYY".
LEAD = re.compile(
    r"\b(D\.?\s*Lgs\.?|D\.?\s*L\.?|D\.?\s*P\.?\s*R\.?|Legge|L\.?\s*n\.?|"
    r"Reg\.?\s*UE|Regolamento\s+\(UE\)|Direttiva)",
    re.IGNORECASE,
)
HAS_NUM_YEAR = re.compile(r"n\.?\s*\d+\s*/\s*\d{2,4}|\d+\s*/\s*\d{2,4}", re.IGNORECASE)
HAS_VERBOSE_DATE = re.compile(r"\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}")

SPEC = RuleSpec(
    rule_id="REF-LEGAL-MALFORMED",
    title="Riferimento normativo incompleto",
    excerpt="I riferimenti normativi devono includere numero e anno (es. D.Lgs. n. 36/2023).",
    default_severity="WARN",
    default_confidence=0.7,
)


class LegalRefMalformedRule:
    spec = SPEC

    def evaluate(self, chunk: Chunk) -> list[Finding]:
        if not is_enabled(self.spec.rule_id):
            return []
        text = chunk.text or ""
        out: list[Finding] = []
        for m in LEAD.finditer(text):
            win_lo = m.start()
            win_hi = min(len(text), m.end() + 80)
            window = text[win_lo:win_hi]
            if HAS_NUM_YEAR.search(window) or HAS_VERBOSE_DATE.search(window):
                continue
            sev: Severity = resolve_severity(
                self.spec.rule_id, self.spec.default_severity
            )
            reasoning = [
                step(
                    1,
                    "TechnicalComplianceAgent",
                    "lead_detected",
                    f"Lead normativo '{m.group(0)}' a offset {m.start()}-{m.end()}.",
                    out={"lead": m.group(0)},
                ),
                step(
                    2,
                    "TechnicalComplianceAgent",
                    "completeness_check",
                    "Cerca numero/anno o data verbose nei 80 char successivi. Non trovato.",
                    out={"complete": False},
                ),
                step(
                    3,
                    "TechnicalComplianceAgent",
                    "severity_assignment",
                    "Riferimento normativo monco → impedisce linking a fonte autoritativa.",
                    out={"severity": sev},
                ),
            ]
            out.append(
                make_finding(
                    spec=self.spec,
                    chunk=chunk,
                    severity=sev,
                    confidence=self.spec.default_confidence,
                    explanation=(
                        f"Riferimento '{m.group(0)}' senza numero/anno o data adiacente."
                    ),
                    suggestion="Specificare numero e anno (es. 'D.Lgs. n. 36/2023').",
                    reasoning=reasoning,
                    match_start=m.start(),
                    match_end=m.end(),
                )
            )
        return out

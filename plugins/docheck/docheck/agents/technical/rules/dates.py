"""FORMAT-DATE-ISO — deadline references must carry a parseable date."""

from __future__ import annotations

import re

from ....schemas.finding import Finding, Severity
from ....schemas.state import Chunk
from .._base import RuleSpec, make_finding, step
from ..patterns import ANY_DATE, PATTERNS
from ..severity import is_enabled, resolve_severity

DEADLINE_TRIGGERS = re.compile(
    r"\b(scadenza|scadenze|scaden(?:e|te|ti)|entro\s+il|termine\s+ultimo|"
    r"deadline|expir(?:y|ation|es?))\b",
    re.IGNORECASE,
)
STRICT_DEADLINE = re.compile(
    r"\b(termine\s+ultimo|termine\s+perentorio|inderogabil[ei]|"
    r"pena\s+(?:di\s+)?esclusione|a\s+pena\s+di\s+nullit[àa])\b",
    re.IGNORECASE,
)

SPEC = RuleSpec(
    rule_id="FORMAT-DATE-ISO",
    title="Date format ISO 8601",
    excerpt="Le date devono essere espresse in formato ISO 8601 (YYYY-MM-DD).",
    default_severity="WARN",
    default_confidence=0.75,
)


class DateIsoRule:
    spec = SPEC

    def evaluate(self, chunk: Chunk) -> list[Finding]:
        if not is_enabled(self.spec.rule_id):
            return []
        text = chunk.text or ""
        m = DEADLINE_TRIGGERS.search(text)
        if not m:
            return []
        t_start, t_end = m.start(), m.end()
        t_word = m.group(0)

        win_lo = max(0, t_start - 240)
        win_hi = min(len(text), t_end + 240)
        window = text[win_lo:win_hi]
        if PATTERNS["iso_date"].search(window) or ANY_DATE.search(window):
            return []

        is_strict = bool(STRICT_DEADLINE.search(window))
        sev: Severity = resolve_severity(
            self.spec.rule_id, "FAIL" if is_strict else "WARN"
        )
        confidence = 0.9 if is_strict else 0.75

        reasoning = [
            step(
                1,
                "TechnicalComplianceAgent",
                "trigger_detected",
                f"Lemma scadenza '{t_word}' a offset {t_start}-{t_end} → trigger check ISO date.",
                out={"trigger": t_word, "trigger_offset": [t_start, t_end]},
            ),
            step(
                2,
                "TechnicalComplianceAgent",
                "regex_check",
                "Cerca ±240 char qualsiasi formato data (ISO, EU numerico, verbose IT/EN). "
                "Regola scatta solo se nessuna data presente.",
                inp={"window_chars": 240},
                out={"matched_iso": False, "matched_any_date": False},
            ),
            step(
                3,
                "TechnicalComplianceAgent",
                "severity_assignment",
                "Lemma stringente (termine ultimo / perentorio / pena esclusione) → FAIL; "
                "lemma generico → WARN.",
                out={"severity": sev, "is_strict_deadline": is_strict},
            ),
            step(
                4,
                "TechnicalComplianceAgent",
                "recommendation",
                "Suggerire data ISO 8601 esplicita (YYYY-MM-DD) per parsing deterministico.",
                out={
                    "suggestion_template": "Specificare data esplicita formato YYYY-MM-DD."
                },
            ),
        ]
        return [
            make_finding(
                spec=self.spec,
                chunk=chunk,
                severity=sev,
                confidence=confidence,
                explanation=(
                    f"Riferimento a '{t_word}' senza data riconoscibile (ISO/EU/verbose) "
                    "nel contesto adiacente."
                    + (
                        " Termine perentorio: ambiguità = rischio compliance."
                        if is_strict
                        else ""
                    )
                ),
                suggestion="Specificare data esplicita formato YYYY-MM-DD accanto al riferimento.",
                reasoning=reasoning,
                match_start=t_start,
                match_end=t_end,
            )
        ]

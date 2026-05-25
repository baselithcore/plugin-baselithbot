"""ID-IBAN-MOD97 — Italian IBAN mod-97 checksum validation."""

from __future__ import annotations

from ....schemas.finding import Finding, Severity
from ....schemas.state import Chunk
from .._base import RuleSpec, make_finding, step
from ..patterns import PATTERNS
from ..severity import is_enabled, resolve_severity


def iban_mod97_valid(iban: str) -> bool:
    iban = iban.replace(" ", "").upper()
    if len(iban) < 4:
        return False
    rearranged = iban[4:] + iban[:4]
    converted = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    if not converted.isdigit():
        return False
    return int(converted) % 97 == 1


SPEC = RuleSpec(
    rule_id="ID-IBAN-MOD97",
    title="IBAN — checksum mod-97 non valido",
    excerpt="Gli IBAN devono superare la validazione mod-97 (ISO 13616).",
    default_severity="WARN",
    default_confidence=0.97,
)


class IbanRule:
    spec = SPEC

    def evaluate(self, chunk: Chunk) -> list[Finding]:
        if not is_enabled(self.spec.rule_id):
            return []
        text = chunk.text or ""
        out: list[Finding] = []
        for m in PATTERNS["iban_it"].finditer(text):
            value = m.group(0)
            if iban_mod97_valid(value):
                continue
            sev: Severity = resolve_severity(self.spec.rule_id, self.spec.default_severity)
            reasoning = [
                step(
                    1,
                    "TechnicalComplianceAgent",
                    "regex_match",
                    f"Pattern IBAN IT '{value}'.",
                    out={"value": value, "offset": [m.start(), m.end()]},
                ),
                step(
                    2,
                    "TechnicalComplianceAgent",
                    "checksum_verify",
                    "Mod-97 (ISO 13616): rearrange + map A=10..Z=35, mod 97 == 1. Non coerente.",
                    out={"valid": False},
                ),
                step(
                    3,
                    "TechnicalComplianceAgent",
                    "severity_assignment",
                    "IBAN sintatticamente IT ma checksum errato → typo o placeholder.",
                    out={"severity": sev},
                ),
            ]
            out.append(
                make_finding(
                    spec=self.spec,
                    chunk=chunk,
                    severity=sev,
                    confidence=self.spec.default_confidence,
                    explanation=f"IBAN '{value}' non supera mod-97.",
                    suggestion="Verificare l'IBAN; il checksum non è valido.",
                    reasoning=reasoning,
                    match_start=m.start(),
                    match_end=m.end(),
                )
            )
        return out

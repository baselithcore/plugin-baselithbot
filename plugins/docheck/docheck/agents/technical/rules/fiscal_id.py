"""ID-CF-CHECKSUM, ID-PIVA-CHECKSUM — validate Italian fiscal identifiers."""

from __future__ import annotations

from ....schemas.finding import Finding, Severity
from ....schemas.state import Chunk
from .._base import RuleSpec, make_finding, step
from ..patterns import PATTERNS
from ..severity import is_enabled, resolve_severity

# CF: control char algorithm (deterministic, no API).
_CF_ODD = {
    "0": 1,
    "1": 0,
    "2": 5,
    "3": 7,
    "4": 9,
    "5": 13,
    "6": 15,
    "7": 17,
    "8": 19,
    "9": 21,
    "A": 1,
    "B": 0,
    "C": 5,
    "D": 7,
    "E": 9,
    "F": 13,
    "G": 15,
    "H": 17,
    "I": 19,
    "J": 21,
    "K": 2,
    "L": 4,
    "M": 18,
    "N": 20,
    "O": 11,
    "P": 3,
    "Q": 6,
    "R": 8,
    "S": 12,
    "T": 14,
    "U": 16,
    "V": 10,
    "W": 22,
    "X": 25,
    "Y": 24,
    "Z": 23,
}
_CF_EVEN = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
    "E": 4,
    "F": 5,
    "G": 6,
    "H": 7,
    "I": 8,
    "J": 9,
    "K": 10,
    "L": 11,
    "M": 12,
    "N": 13,
    "O": 14,
    "P": 15,
    "Q": 16,
    "R": 17,
    "S": 18,
    "T": 19,
    "U": 20,
    "V": 21,
    "W": 22,
    "X": 23,
    "Y": 24,
    "Z": 25,
}
_CF_CONTROL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cf_checksum_valid(cf: str) -> bool:
    cf = cf.upper()
    if len(cf) != 16:
        return False
    total = 0
    for i, ch in enumerate(cf[:15]):
        # 1-indexed in spec: position 1 = odd. i=0 → odd.
        table = _CF_ODD if (i % 2 == 0) else _CF_EVEN
        if ch not in table:
            return False
        total += table[ch]
    return _CF_CONTROL[total % 26] == cf[15]


def piva_checksum_valid(piva: str) -> bool:
    """Italian VAT — Luhn-like with digit-pair odd/even doubling."""
    digits = piva.removeprefix("IT")
    if len(digits) != 11 or not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(digits[:10]):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    check = (10 - (total % 10)) % 10
    return check == int(digits[10])


_CF_SPEC = RuleSpec(
    rule_id="ID-CF-CHECKSUM",
    title="Codice Fiscale — checksum non valido",
    excerpt="Il codice fiscale deve avere checksum coerente (algoritmo art. 4 DM 23/12/1976).",
    default_severity="WARN",
    default_confidence=0.95,
)

_PIVA_SPEC = RuleSpec(
    rule_id="ID-PIVA-CHECKSUM",
    title="Partita IVA — checksum non valido",
    excerpt="La Partita IVA italiana deve avere checksum Luhn coerente (art. 35 DPR 633/1972).",
    default_severity="WARN",
    default_confidence=0.95,
)


class CodiceFiscaleRule:
    spec = _CF_SPEC

    def evaluate(self, chunk: Chunk) -> list[Finding]:
        if not is_enabled(self.spec.rule_id):
            return []
        text = chunk.text or ""
        out: list[Finding] = []
        for m in PATTERNS["codice_fiscale"].finditer(text):
            cf = m.group(0)
            if cf_checksum_valid(cf):
                continue
            sev: Severity = resolve_severity(self.spec.rule_id, self.spec.default_severity)
            reasoning = [
                step(
                    1,
                    "TechnicalComplianceAgent",
                    "regex_match",
                    f"Pattern CF '{cf}' a offset {m.start()}-{m.end()}.",
                    out={"value": cf, "offset": [m.start(), m.end()]},
                ),
                step(
                    2,
                    "TechnicalComplianceAgent",
                    "checksum_verify",
                    "Algoritmo CF (art. 4 DM 23/12/1976): somma pesata caratteri 1-15 → "
                    "carattere controllo posizione 16. Risultato non coerente.",
                    out={"valid": False},
                ),
                step(
                    3,
                    "TechnicalComplianceAgent",
                    "severity_assignment",
                    "CF formalmente sintatticamente corretto ma checksum errato → probabile "
                    "typo o valore fittizio. WARN per default (override possibile via settings).",
                    out={"severity": sev},
                ),
            ]
            out.append(
                make_finding(
                    spec=self.spec,
                    chunk=chunk,
                    severity=sev,
                    confidence=self.spec.default_confidence,
                    explanation=f"Codice fiscale '{cf}' con checksum non valido.",
                    suggestion="Verificare il codice fiscale; potrebbe essere errato o un placeholder.",
                    reasoning=reasoning,
                    match_start=m.start(),
                    match_end=m.end(),
                )
            )
        return out


class PartitaIvaRule:
    spec = _PIVA_SPEC

    def evaluate(self, chunk: Chunk) -> list[Finding]:
        if not is_enabled(self.spec.rule_id):
            return []
        text = chunk.text or ""
        out: list[Finding] = []
        for m in PATTERNS["partita_iva"].finditer(text):
            value = m.group(0)
            if piva_checksum_valid(value):
                continue
            sev: Severity = resolve_severity(self.spec.rule_id, self.spec.default_severity)
            reasoning = [
                step(
                    1,
                    "TechnicalComplianceAgent",
                    "regex_match",
                    f"Pattern P.IVA '{value}' a offset {m.start()}-{m.end()}.",
                    out={"value": value, "offset": [m.start(), m.end()]},
                ),
                step(
                    2,
                    "TechnicalComplianceAgent",
                    "checksum_verify",
                    "Algoritmo Luhn IT (art. 35 DPR 633/1972): doppio cifre pari, somma, "
                    "controllo cifra finale. Non coerente.",
                    out={"valid": False},
                ),
                step(
                    3,
                    "TechnicalComplianceAgent",
                    "severity_assignment",
                    "P.IVA formalmente corretta ma checksum errato → typo o placeholder.",
                    out={"severity": sev},
                ),
            ]
            out.append(
                make_finding(
                    spec=self.spec,
                    chunk=chunk,
                    severity=sev,
                    confidence=self.spec.default_confidence,
                    explanation=f"Partita IVA '{value}' con checksum non valido.",
                    suggestion="Verificare la P.IVA; potrebbe essere errata o un placeholder.",
                    reasoning=reasoning,
                    match_start=m.start(),
                    match_end=m.end(),
                )
            )
        return out

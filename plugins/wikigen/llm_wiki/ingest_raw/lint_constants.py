"""Costanti / regex / dataclass del linter wiki.

Estratto da :mod:`llm_wiki.ingest_raw.linter` per separare la "config"
deterministica (stringhe vietate, sezioni obbligatorie, regex articoli)
dal codice procedurale dei singoli check. Mantenere il payload
linguistico in un solo file rende ovvio dove aggiungere termini nuovi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass
class LintIssue:
    code: str
    message: str
    severity: Severity
    line: int | None = None
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "line": self.line,
            "hint": self.hint,
        }


@dataclass
class LintReport:
    path: str
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity is Severity.ERROR for i in self.issues)

    def add(
        self,
        code: str,
        message: str,
        severity: Severity = Severity.ERROR,
        line: int | None = None,
        hint: str | None = None,
    ) -> None:
        self.issues.append(LintIssue(code, message, severity, line, hint))

    def to_prompt_feedback(self, *, max_issues: int = 8) -> str:
        """Proietta il report in stringa consumabile dal critic LLM.

        ``max_issues`` cap evita prompt rigonfi quando il lint produce 30+
        problemi: il critic non è efficace su batch grandi (modello locale
        si concentra solo su pochi). Priorità: ERROR prima di WARN.
        """
        if not self.issues:
            return "Nessun errore rilevato."
        ordered = sorted(
            self.issues,
            key=lambda iss: 0 if iss.severity is Severity.ERROR else 1,
        )
        truncated = ordered[:max_issues]
        lines = [f"File: {self.path}", "Errori rilevati:"]
        for iss in truncated:
            tag = f"[{iss.severity.value.upper()}]"
            loc = f" (riga {iss.line})" if iss.line else ""
            hint = f" — Hint: {iss.hint}" if iss.hint else ""
            lines.append(f"- {tag} {iss.code}{loc}: {iss.message}{hint}")
        if len(ordered) > max_issues:
            lines.append(
                f"… (+{len(ordered) - max_issues} altri problemi non mostrati;"
                f" risolvi prima i {max_issues} sopra)"
            )
        return "\n".join(lines)


# --- regex / costanti -------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
ART_RE = re.compile(
    r"\bart(?:t|icolo)?\.?\s*\d+(?:[.,]\s*\d+)*(?:\s*c\.?\s*\d+)?"
    r"(?:\s*lett\.?\s*[a-z])?(?:\s*CC|\s*CdA|\s*CAP|\s*NTA|\s*CPC)?\b",
    re.IGNORECASE,
)
RULE_CALLOUT_RE = re.compile(r"^>\s*\[!rule\]", re.MULTILINE)
QUOTE_CALLOUT_RE = re.compile(r"^>\s*\[!quote\]", re.MULTILINE)
IMPORTANT_CALLOUT_RE = re.compile(r"^>\s*\[!important\]", re.MULTILINE)
TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$", re.MULTILINE)
YAML_FENCE_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)

# Termini vietati nel corpo normativo (CLAUDE.md §Rigore terminologico)
TERMINI_VIETATI = [
    r"\bstandard\b",
    r"\bdi solito\b",
    r"\bnormalmente\b",
    r"\btipicamente\b",
    r"\bcirca\b",
    r"\bpiù o meno\b",
    r"\bla compagnia paga\b",
    r"\bse succede\b",
    r"\bbasically\b",
    r"\breally\b",
]
TERMINI_VIETATI_RE = re.compile("|".join(TERMINI_VIETATI), re.IGNORECASE)

# Parole-spia per regole condizionali (CLAUDE.md §Regole condizionali)
PAROLE_SPIA_CONDIZIONE = [
    "salvo",
    "tranne",
    "deroga",
    "fermo restando",
    "purché",
    "a condizione che",
    "limitatamente a",
    "nei casi in cui",
    "ai sensi",
    "come previsto",
    "cfr. art.",
]

# Termini sensibili → richiedono verbatim quote vicina (CLAUDE.md §Citazioni verbatim)
TERMINI_SENSIBILI = [
    r"\bdolo\b",
    r"\bcolpa grave\b",
    r"\bcolpa lieve\b",
    r"\binvolontariamente\b",
    r"\baccidentalmente\b",
    r"\bimpreved[a-z]+\b",
    r"\bimprovviso\b",
    r"\bstraordinario\b",
    r"\beccezionale\b",
    r"\bfortuito\b",
    r"\bsalvo il caso di\b",
    r"\bpurché\b",
    r"\ba condizione che\b",
]
TERMINI_SENSIBILI_RE = re.compile("|".join(TERMINI_SENSIBILI), re.IGNORECASE)

# Sezioni obbligatorie per subtype garanzia
SEZIONI_GARANZIA = {
    "## In due righe",
    "## Vincoli di acquisto",
    "## Cosa copre",
    "## Cosa NON copre",
    "## Limiti",  # match parziale (es. "## Limiti di indennizzo, Franchigie e Scoperti")
    "## Dove vale",
    "## Obblighi in caso di sinistro",
    "## FAQ",
    "## Fonti",
}
SEZIONI_SOURCE = {
    "## Contesto",
    "## Takeaway principali",
    "## Dettagli rilevanti",
    "## Entità e concetti",
    "## Citazioni degne di nota",
    "## Domande aperte",
}

"""
Red-flag rule engine.

The rules are intentionally simple keyword matchers that scan both the
patient's raw utterances and the canonical symptoms extracted from them.
The list is conservative and meant to be extended by clinical reviewers.
Any unnegated match short-circuits the interview loop and forces
``TriageCode.RED``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from ..graph.repository import SymptomGraphRepository

RED_FLAG_KEYWORDS: Final[dict[str, str]] = {
    "dolore toracico": "Dolore toracico irradiato: sospetta sindrome coronarica acuta.",
    "chest pain": "Chest pain: rule out acute coronary syndrome.",
    "dispnea grave": "Dispnea severa: sospetta embolia polmonare o insufficienza respiratoria.",
    "perdita di coscienza": "Sincope/perdita di coscienza recente.",
    "deficit neurologico": "Deficit neurologico focale: sospetto stroke.",
    "afasia": "Afasia improvvisa: sospetto stroke.",
    "emiparesi": "Emiparesi: sospetto stroke.",
    "cefalea improvvisa": "Cefalea ad esordio iperacuto: rule out emorragia subaracnoidea.",
    "sanguinamento attivo": "Emorragia attiva non controllata.",
    "ideazione suicidaria": "Ideazione suicidaria attiva: escalation salute mentale.",
    "anafilassi": "Sospetta anafilassi.",
    "convulsione": "Crisi convulsiva in atto o recente.",
}


# Italian (+ English) negation cues. Window-based detection: any cue
# appearing within ``_NEGATION_WINDOW_CHARS`` characters before a keyword
# suppresses the match. Kept local to the safety module so red-flag
# scanning has no dependency on the agents layer.
_NEGATION_CUES: Final[tuple[str, ...]] = (
    "non ho ",
    "non ha ",
    "non avvert",
    "non sent",
    "non riferisc",
    "non not",
    "non c'è",
    "non c'e",
    "non present",
    "nego",
    "nega",
    "niente",
    "nessun",
    "nessuna",
    "nessuno",
    "senza ",
    "mai avut",
    "non mi pare",
    "non credo",
    "no, ",
    " no ",
)
_NEGATION_WINDOW_CHARS: Final[int] = 32


def _keyword_present_unnegated(text: str, keyword: str) -> bool:
    """``True`` when ``keyword`` appears in ``text`` without a preceding
    negation cue inside the look-back window.

    Scans every occurrence so a denied mention earlier in the utterance does
    not mask an affirmed mention later (``"non ho febbre, ma ho convulsione"``
    must still fire on ``convulsione``).
    """
    lower = text.lower()
    start = 0
    while True:
        idx = lower.find(keyword, start)
        if idx < 0:
            return False
        window_start = max(0, idx - _NEGATION_WINDOW_CHARS)
        window = lower[window_start:idx]
        if not any(cue in window for cue in _NEGATION_CUES):
            return True
        start = idx + max(1, len(keyword))


@dataclass
class RedFlagEvaluation:
    """Result of evaluating the red-flag rules against a session."""

    matches: list[str] = field(default_factory=list)

    @property
    def requires_immediate_escalation(self) -> bool:
        return bool(self.matches)

    @property
    def summary(self) -> str:
        return "; ".join(self.matches)


class RedFlagEvaluator:
    """Stateless rule evaluator over the current ``SymptomGraphRepository``."""

    def evaluate(
        self,
        repo: SymptomGraphRepository,
        session_id: str,
    ) -> RedFlagEvaluation:
        snap = repo.snapshot(session_id)
        matches: list[str] = []

        # 1) Scan affirmed symptoms by canonical_name (never negated by
        # construction — the extractor already strips denied symptoms).
        for symptom in snap.symptoms:
            name = symptom.canonical_name.lower()
            for keyword, message in RED_FLAG_KEYWORDS.items():
                if keyword in name and message not in matches:
                    matches.append(message)

        # 2) Scan symptom raw_quotes WITH negation awareness so a denied
        # mention inside an affirmed symptom's quote ("non ho dolore
        # toracico, ho mal di schiena") doesn't fire a false RED.
        for symptom in snap.symptoms:
            quote = symptom.raw_quote or ""
            if not quote:
                continue
            for keyword, message in RED_FLAG_KEYWORDS.items():
                if message in matches:
                    continue
                if _keyword_present_unnegated(quote, keyword):
                    matches.append(message)

        # 3) Scan the recent patient turns directly so dangerous mentions
        # the symptom extractor missed (e.g. "convulsione", "anafilassi",
        # "ideazione suicidaria" — not in the symptom lexicon) still
        # escalate the case.
        for utterance in snap.patient_turns:
            if not utterance:
                continue
            for keyword, message in RED_FLAG_KEYWORDS.items():
                if message in matches:
                    continue
                if _keyword_present_unnegated(utterance, keyword):
                    matches.append(message)

        return RedFlagEvaluation(matches=matches)

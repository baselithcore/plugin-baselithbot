"""Suggest validated bedside scores given a SymptomMatrix.

Maps canonical symptoms / DDx hypotheses to the most appropriate tier-2
score the clinician should compute. Deterministic, fast, no LLM.

Mapping rules are intentionally conservative — the suggester offers
candidates; the clinician decides. Each suggestion carries a short
``reason`` so the UI can render "we suggested HEART because the patient
reported chest pain" instead of a bare score name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .models.clinical import SymptomMatrix


@dataclass(frozen=True)
class ScoreSuggestion:
    score: str  # canonical score id (HEART / Wells-PE / Wells-DVT / Centor / NEWS2 / qSOFA / CURB-65)
    reason: str
    endpoint: str  # router path suffix the UI must POST to (or GET for tier-1)

    def to_dict(self) -> dict[str, str]:
        return {
            "score": self.score,
            "reason": self.reason,
            "endpoint": self.endpoint,
        }


# Trigger canonical symptoms → suggested score(s).
_SYMPTOM_TO_SCORES: Final[dict[str, tuple[tuple[str, str, str], ...]]] = {
    "dolore toracico": (
        (
            "HEART",
            "Chest pain reported — HEART stratifies 30-day MACE risk.",
            "POST /sessions/{id}/scores/heart",
        ),
        (
            "TIMI-UA-NSTEMI",
            "Chest pain may reflect UA/NSTEMI — apply TIMI risk score.",
            "POST /sessions/{id}/scores/timi",
        ),
        (
            "Wells-PE",
            "Chest pain may also reflect PE — apply Wells PE pretest probability.",
            "POST /sessions/{id}/scores/wells-pe",
        ),
        (
            "PERC",
            "If clinical gestalt is low-risk for PE, apply PERC to rule out.",
            "POST /sessions/{id}/scores/perc",
        ),
    ),
    "dispnea": (
        (
            "Wells-PE",
            "Dyspnea is a Wells-PE driver — compute pretest probability.",
            "POST /sessions/{id}/scores/wells-pe",
        ),
        (
            "PERC",
            "Low-risk dyspnea: PERC can safely rule out PE.",
            "POST /sessions/{id}/scores/perc",
        ),
        (
            "CURB-65",
            "Dyspnea raises pneumonia risk — CURB-65 grades severity.",
            "GET /sessions/{id}/scores",
        ),
    ),
    "sincope": (
        (
            "HEART",
            "Syncope with cardiac risk factors warrants HEART stratification.",
            "POST /sessions/{id}/scores/heart",
        ),
        (
            "GCS",
            "Syncope event — record GCS at presentation for trending.",
            "POST /sessions/{id}/scores/gcs",
        ),
    ),
    "deficit neurologico": (
        (
            "GCS",
            "Neurological deficit reported — capture GCS for severity.",
            "POST /sessions/{id}/scores/gcs",
        ),
    ),
    "afasia": (
        (
            "GCS",
            "Aphasia event — capture GCS at presentation.",
            "POST /sessions/{id}/scores/gcs",
        ),
    ),
    "emiparesi": (
        (
            "GCS",
            "Hemiparesis event — capture GCS at presentation.",
            "POST /sessions/{id}/scores/gcs",
        ),
    ),
    "tosse": (
        (
            "CURB-65",
            "Cough may indicate community-acquired pneumonia.",
            "GET /sessions/{id}/scores",
        ),
    ),
    "febbre": (
        (
            "qSOFA",
            "Fever + abnormal vitals can imply sepsis — qSOFA flags risk.",
            "GET /sessions/{id}/scores",
        ),
    ),
    "dolore addominale": (
        (
            "Alvarado",
            "Abdominal pain — Alvarado (MANTRELS) stratifies appendicitis risk.",
            "POST /sessions/{id}/scores/alvarado",
        ),
    ),
}


# Trigger past-medical-history canonicals → suggested score.
_PMH_TO_SCORES: Final[dict[str, tuple[tuple[str, str, str], ...]]] = {
    "pregresso IMA": (
        (
            "HEART",
            "Prior MI is a Risk-factors point — apply HEART when chest pain.",
            "POST /sessions/{id}/scores/heart",
        ),
    ),
    "fibrillazione atriale": (
        (
            "CHA2DS2-VASc",
            "AF — CHA2DS2-VASc grades stroke risk to decide on anticoagulation.",
            "POST /sessions/{id}/scores/cha2ds2-vasc",
        ),
        (
            "HAS-BLED",
            "If anticoagulating, balance with HAS-BLED bleeding-risk score.",
            "POST /sessions/{id}/scores/has-bled",
        ),
        (
            "Wells-PE",
            "AF predisposes to thromboembolism — consider Wells PE.",
            "POST /sessions/{id}/scores/wells-pe",
        ),
    ),
    "terapia anticoagulante": (
        (
            "HAS-BLED",
            "Patient on anticoagulation — HAS-BLED guides bleeding-risk review.",
            "POST /sessions/{id}/scores/has-bled",
        ),
    ),
}


def suggest_scores(matrix: SymptomMatrix) -> list[ScoreSuggestion]:
    """Return de-duplicated score suggestions ordered by first match."""
    seen: set[str] = set()
    out: list[ScoreSuggestion] = []

    for symptom in matrix.symptoms:
        for score_id, reason, endpoint in _SYMPTOM_TO_SCORES.get(
            symptom.canonical_name, ()
        ):
            if score_id in seen:
                continue
            seen.add(score_id)
            out.append(
                ScoreSuggestion(score=score_id, reason=reason, endpoint=endpoint)
            )

    # Pharyngitis pattern: tonsillar symptoms aren't in the canonical
    # symptom lexicon yet (Centor needs explicit clinician inputs), so we
    # surface Centor whenever the raw quote contains a pharyngitis hint.
    for symptom in matrix.symptoms:
        quote = (symptom.raw_quote or "").lower()
        if any(
            kw in quote
            for kw in ("mal di gola", "gola", "faringite", "sore throat", "tonsill")
        ):
            if "Centor-McIsaac" not in seen:
                seen.add("Centor-McIsaac")
                out.append(
                    ScoreSuggestion(
                        score="Centor-McIsaac",
                        reason=(
                            "Sore-throat / pharyngitis pattern — Centor "
                            "(McIsaac) stratifies group A strep likelihood."
                        ),
                        endpoint="POST /sessions/{id}/scores/centor",
                    )
                )
            break

    # Ankle / knee trauma patterns drive the Ottawa imaging rules.
    for symptom in matrix.symptoms:
        quote = (symptom.raw_quote or "").lower()
        if any(kw in quote for kw in ("caviglia", "ankle", "malleol")):
            if "Ottawa-Ankle" not in seen:
                seen.add("Ottawa-Ankle")
                out.append(
                    ScoreSuggestion(
                        score="Ottawa-Ankle",
                        reason=(
                            "Ankle / malleolar pain — Ottawa Ankle rules "
                            "decide whether radiograph is indicated."
                        ),
                        endpoint="POST /sessions/{id}/scores/ottawa-ankle",
                    )
                )
        if any(kw in quote for kw in ("ginocchio", "knee", "patell", "rotula")):
            if "Ottawa-Knee" not in seen:
                seen.add("Ottawa-Knee")
                out.append(
                    ScoreSuggestion(
                        score="Ottawa-Knee",
                        reason=(
                            "Knee trauma — Ottawa Knee rules decide whether "
                            "radiograph is indicated."
                        ),
                        endpoint="POST /sessions/{id}/scores/ottawa-knee",
                    )
                )

    for pmh in matrix.past_medical_history:
        for score_id, reason, endpoint in _PMH_TO_SCORES.get(pmh, ()):
            if score_id in seen:
                continue
            seen.add(score_id)
            out.append(
                ScoreSuggestion(score=score_id, reason=reason, endpoint=endpoint)
            )

    # NEWS2 is universally applicable when vitals are present; surface it
    # quietly at the end as a "default" so the UI can always show one.
    if matrix.vitals is not None and "NEWS2" not in seen:
        out.append(
            ScoreSuggestion(
                score="NEWS2",
                reason="Vitals captured — NEWS2 baseline acuity is available.",
                endpoint="GET /sessions/{id}/scores",
            )
        )

    return out

"""Tier-2 cardiology clinical scores.

Implements: HEART, Wells PE, Wells DVT, CHA2DS2-VASc, HAS-BLED.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from .scores import ScoreResult


# ---------------------------------------------------------------------------
# HEART score
# ---------------------------------------------------------------------------


class HeartScoreInput(BaseModel):
    """Inputs for the HEART acute chest-pain risk score.

    Each component is scored 0/1/2 by the clinician at the bedside; the
    model just sums and bands the result.
    """

    model_config = ConfigDict(extra="forbid")

    history: Annotated[int, Field(ge=0, le=2)]
    ecg: Annotated[int, Field(ge=0, le=2)]
    age: Annotated[int, Field(ge=0, le=2)]
    risk_factors: Annotated[int, Field(ge=0, le=2)]
    troponin: Annotated[int, Field(ge=0, le=2)]


def compute_heart(input: HeartScoreInput) -> ScoreResult:
    components = {
        "history": input.history,
        "ecg": input.ecg,
        "age": input.age,
        "risk_factors": input.risk_factors,
        "troponin": input.troponin,
    }
    total = sum(components.values())
    if total >= 7:
        band = "HIGH"
    elif total >= 4:
        band = "INTERMEDIATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="HEART",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale=(
            "HEART score (History/ECG/Age/Risk-factors/Troponin) applied; "
            "≥7 implies high MACE risk, 4-6 intermediate, ≤3 low."
        ),
    )


# ---------------------------------------------------------------------------
# Wells score — Pulmonary Embolism
# ---------------------------------------------------------------------------


class WellsPeInput(BaseModel):
    """Inputs for the Wells pretest probability score for PE."""

    model_config = ConfigDict(extra="forbid")

    clinical_signs_dvt: bool
    pe_more_likely_than_alternative: bool
    heart_rate_over_100: bool
    immobilisation_or_surgery_4w: bool
    previous_pe_or_dvt: bool
    hemoptysis: bool
    malignancy_treatment_or_palliative: bool


_WELLS_PE_POINTS: dict[str, float] = {
    "clinical_signs_dvt": 3.0,
    "pe_more_likely_than_alternative": 3.0,
    "heart_rate_over_100": 1.5,
    "immobilisation_or_surgery_4w": 1.5,
    "previous_pe_or_dvt": 1.5,
    "hemoptysis": 1.0,
    "malignancy_treatment_or_palliative": 1.0,
}


def compute_wells_pe(input: WellsPeInput) -> ScoreResult:
    components: dict[str, int] = {}
    total_f = 0.0
    for field_name, weight in _WELLS_PE_POINTS.items():
        flag: bool = getattr(input, field_name)
        # Store integer-doubled weight so the dict respects ScoreResult's
        # ``dict[str, int]`` contract (Wells uses half points).
        components[field_name] = int(weight * 2) if flag else 0
        if flag:
            total_f += weight
    if total_f > 6.0:
        band = "HIGH"
    elif total_f >= 2.0:
        band = "MODERATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="Wells-PE",
        computable=True,
        value=int(total_f * 2),  # half-point doubled, see Note in rationale.
        band=band,
        components=components,
        rationale=(
            "Wells score for PE applied; raw points are half-point weighted "
            "(values reported here are doubled — original total in points "
            f"= {total_f:.1f}). >6 high, 2-6 moderate, <2 low pretest "
            "probability."
        ),
    )


# ---------------------------------------------------------------------------
# Wells score — DVT
# ---------------------------------------------------------------------------


class WellsDvtInput(BaseModel):
    """Inputs for the Wells pretest probability score for DVT."""

    model_config = ConfigDict(extra="forbid")

    active_cancer: bool
    paralysis_or_recent_immobilisation: bool
    bedridden_3d_or_surgery_12w: bool
    tenderness_along_deep_veins: bool
    entire_leg_swollen: bool
    calf_swelling_3cm_asymmetry: bool
    pitting_edema_symptomatic_leg: bool
    collateral_superficial_veins: bool
    previous_dvt: bool
    alternative_diagnosis_at_least_as_likely: bool  # subtracts 2 points


def compute_wells_dvt(input: WellsDvtInput) -> ScoreResult:
    components: dict[str, int] = {
        "active_cancer": int(input.active_cancer),
        "paralysis_or_recent_immobilisation": int(
            input.paralysis_or_recent_immobilisation
        ),
        "bedridden_3d_or_surgery_12w": int(input.bedridden_3d_or_surgery_12w),
        "tenderness_along_deep_veins": int(input.tenderness_along_deep_veins),
        "entire_leg_swollen": int(input.entire_leg_swollen),
        "calf_swelling_3cm_asymmetry": int(input.calf_swelling_3cm_asymmetry),
        "pitting_edema_symptomatic_leg": int(input.pitting_edema_symptomatic_leg),
        "collateral_superficial_veins": int(input.collateral_superficial_veins),
        "previous_dvt": int(input.previous_dvt),
        "alternative_diagnosis_at_least_as_likely": (
            -2 if input.alternative_diagnosis_at_least_as_likely else 0
        ),
    }
    total = sum(components.values())
    if total >= 3:
        band = "HIGH"
    elif total >= 1:
        band = "MODERATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="Wells-DVT",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale=(
            "Wells score for DVT applied; ≥3 high probability, 1-2 moderate, "
            "≤0 low. Negative score is possible when an alternative diagnosis "
            "is at least as likely."
        ),
    )


# ---------------------------------------------------------------------------
# CHA2DS2-VASc — Stroke risk in non-valvular atrial fibrillation
# ---------------------------------------------------------------------------


class Cha2ds2VascInput(BaseModel):
    """Inputs for the CHA2DS2-VASc score (max 9 points)."""

    model_config = ConfigDict(extra="forbid")

    congestive_heart_failure: bool
    hypertension: bool
    age_75_or_more: bool  # 2 points
    diabetes_mellitus: bool
    stroke_tia_thromboembolism: bool  # 2 points
    vascular_disease: bool
    age_65_to_74: bool
    sex_female: bool


def compute_cha2ds2_vasc(input: Cha2ds2VascInput) -> ScoreResult:
    components = {
        "congestive_heart_failure": int(input.congestive_heart_failure),
        "hypertension": int(input.hypertension),
        "age_75_or_more": 2 if input.age_75_or_more else 0,
        "diabetes_mellitus": int(input.diabetes_mellitus),
        "stroke_tia_thromboembolism": (2 if input.stroke_tia_thromboembolism else 0),
        "vascular_disease": int(input.vascular_disease),
        # Per the original CHA2DS2-VASc table, age 65-74 is a separate
        # point and is NOT counted when age ≥75 is already 2 points. We
        # silently suppress the lower band to avoid double-counting.
        "age_65_to_74": (1 if input.age_65_to_74 and not input.age_75_or_more else 0),
        "sex_female": int(input.sex_female),
    }
    total = sum(components.values())
    if total >= 2:
        band = "HIGH"
    elif total == 1:
        band = "INTERMEDIATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="CHA2DS2-VASc",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale=(
            "CHA2DS2-VASc score for stroke risk in non-valvular AF; "
            "≥2 (≥3 in women) typically warrants oral anticoagulation, "
            "1 intermediate (case-by-case), 0 low (no antithrombotic)."
        ),
    )


# ---------------------------------------------------------------------------
# HAS-BLED — Bleeding risk on anticoagulation
# ---------------------------------------------------------------------------


class HasBledInput(BaseModel):
    """Inputs for the HAS-BLED bleeding risk score (max 9 points)."""

    model_config = ConfigDict(extra="forbid")

    hypertension_uncontrolled: bool
    abnormal_renal_function: bool
    abnormal_liver_function: bool
    stroke_history: bool
    bleeding_history_or_predisposition: bool
    labile_inr: bool
    elderly_over_65: bool
    drugs_increasing_bleeding: bool
    alcohol_use: bool


def compute_has_bled(input: HasBledInput) -> ScoreResult:
    components = {
        "hypertension_uncontrolled": int(input.hypertension_uncontrolled),
        "abnormal_renal_function": int(input.abnormal_renal_function),
        "abnormal_liver_function": int(input.abnormal_liver_function),
        "stroke_history": int(input.stroke_history),
        "bleeding_history_or_predisposition": int(
            input.bleeding_history_or_predisposition
        ),
        "labile_inr": int(input.labile_inr),
        "elderly_over_65": int(input.elderly_over_65),
        "drugs_increasing_bleeding": int(input.drugs_increasing_bleeding),
        "alcohol_use": int(input.alcohol_use),
    }
    total = sum(components.values())
    if total >= 3:
        band = "HIGH"
    elif total >= 1:
        band = "MODERATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="HAS-BLED",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale=(
            "HAS-BLED score for major bleeding risk on anticoagulation; "
            "≥3 high risk (caution, modify risk factors), 1-2 moderate, "
            "0 low. Always weigh against thrombotic risk (CHA2DS2-VASc)."
        ),
    )


__all__ = [
    "HeartScoreInput",
    "compute_heart",
    "WellsPeInput",
    "compute_wells_pe",
    "WellsDvtInput",
    "compute_wells_dvt",
    "Cha2ds2VascInput",
    "compute_cha2ds2_vasc",
    "HasBledInput",
    "compute_has_bled",
]

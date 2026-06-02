"""Tier-2 bedside clinical scores requiring explicit clinician input.

The NEWS2 / qSOFA / CURB-65 family in :mod:`scores` works purely off
:class:`Vitals` captured at intake. Tier-2 scores need *clinician
judgment* (ECG interpretation, suspected DVT signs, tonsillar exudate)
that the patient cannot self-report; they live here as **POST-driven**
endpoints where the validating clinician supplies the inputs explicitly.

Implemented:
    * **HEART score** — acute chest-pain risk stratification.
    * **Wells PE** — pretest probability of pulmonary embolism.
    * **Wells DVT** — pretest probability of deep vein thrombosis.
    * **Centor / McIsaac** — group A streptococcal pharyngitis.

Every calculator returns a :class:`~scores.ScoreResult` (same shape as
the tier-1 calculators) so the UI and FHIR exporter can render them with
one common code path. Cutoffs follow the published references.
"""

from __future__ import annotations

from typing import Annotated, Literal

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
# Centor / McIsaac score — group A streptococcal pharyngitis
# ---------------------------------------------------------------------------


_McIsaacAgeBand = Literal["3-14", "15-44", "45+"]


class CentorInput(BaseModel):
    """Inputs for the McIsaac-modified Centor score.

    McIsaac adds an age-based adjustment to classical Centor: +1 for age
    3-14, 0 for 15-44, -1 for age ≥45.
    """

    model_config = ConfigDict(extra="forbid")

    tonsillar_exudate: bool
    swollen_tender_anterior_cervical_nodes: bool
    fever_over_38: bool
    absence_of_cough: bool
    age_band: _McIsaacAgeBand


def compute_centor(input: CentorInput) -> ScoreResult:
    age_adj = 1 if input.age_band == "3-14" else -1 if input.age_band == "45+" else 0
    components: dict[str, int] = {
        "tonsillar_exudate": int(input.tonsillar_exudate),
        "swollen_tender_anterior_cervical_nodes": int(
            input.swollen_tender_anterior_cervical_nodes
        ),
        "fever_over_38": int(input.fever_over_38),
        "absence_of_cough": int(input.absence_of_cough),
        "age_adjustment": age_adj,
    }
    total = sum(components.values())
    if total >= 4:
        band = "HIGH"
    elif total >= 2:
        band = "MODERATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="Centor-McIsaac",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale=(
            "Centor (McIsaac-modified) score for group A strep pharyngitis "
            "applied; ≥4 high likelihood (empiric antibiotics consider), "
            "2-3 moderate (RADT/culture), ≤1 low (no testing)."
        ),
    )


# ---------------------------------------------------------------------------
# PERC rule — Pulmonary Embolism Rule-out Criteria
# ---------------------------------------------------------------------------


class PercInput(BaseModel):
    """Inputs for the PERC (Pulmonary Embolism Rule-out Criteria) rule.

    PERC is a *negative* rule: when **all eight** criteria are negative in
    a patient already judged to be low-risk by gestalt or Wells, no
    further PE work-up is required.
    """

    model_config = ConfigDict(extra="forbid")

    age_50_or_more: bool
    heart_rate_100_or_more: bool
    spo2_below_95: bool
    hemoptysis: bool
    estrogen_use: bool
    prior_dvt_or_pe: bool
    unilateral_leg_swelling: bool
    surgery_or_trauma_within_4w: bool


def compute_perc(input: PercInput) -> ScoreResult:
    components = {
        "age_50_or_more": int(input.age_50_or_more),
        "heart_rate_100_or_more": int(input.heart_rate_100_or_more),
        "spo2_below_95": int(input.spo2_below_95),
        "hemoptysis": int(input.hemoptysis),
        "estrogen_use": int(input.estrogen_use),
        "prior_dvt_or_pe": int(input.prior_dvt_or_pe),
        "unilateral_leg_swelling": int(input.unilateral_leg_swelling),
        "surgery_or_trauma_within_4w": int(input.surgery_or_trauma_within_4w),
    }
    positive_criteria = sum(components.values())
    band = "RULE_OUT" if positive_criteria == 0 else "WORKUP_REQUIRED"
    return ScoreResult(
        name="PERC",
        computable=True,
        value=positive_criteria,
        band=band,
        components=components,
        rationale=(
            "PERC rule applied; all 8 criteria must be negative to safely "
            "rule out PE without further testing. Any positive criterion "
            "requires conventional PE work-up."
        ),
    )


# ---------------------------------------------------------------------------
# TIMI score — Unstable angina / NSTEMI risk
# ---------------------------------------------------------------------------


class TimiInput(BaseModel):
    """Inputs for the TIMI risk score for UA/NSTEMI."""

    model_config = ConfigDict(extra="forbid")

    age_65_or_more: bool
    three_or_more_cad_risk_factors: bool
    known_cad_stenosis_50: bool
    asa_in_past_7d: bool
    severe_angina_two_episodes_24h: bool
    ecg_st_deviation_05mm: bool
    positive_cardiac_marker: bool


def compute_timi(input: TimiInput) -> ScoreResult:
    components = {
        "age_65_or_more": int(input.age_65_or_more),
        "three_or_more_cad_risk_factors": int(input.three_or_more_cad_risk_factors),
        "known_cad_stenosis_50": int(input.known_cad_stenosis_50),
        "asa_in_past_7d": int(input.asa_in_past_7d),
        "severe_angina_two_episodes_24h": int(input.severe_angina_two_episodes_24h),
        "ecg_st_deviation_05mm": int(input.ecg_st_deviation_05mm),
        "positive_cardiac_marker": int(input.positive_cardiac_marker),
    }
    total = sum(components.values())
    if total >= 5:
        band = "HIGH"
    elif total >= 3:
        band = "INTERMEDIATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="TIMI-UA-NSTEMI",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale=(
            "TIMI Risk Score for UA/NSTEMI applied; ≥5 high (40.9% 14-day "
            "MACE), 3-4 intermediate (13-19.9%), ≤2 low (4.7-8.3%)."
        ),
    )


# ---------------------------------------------------------------------------
# Glasgow Coma Scale (GCS)
# ---------------------------------------------------------------------------


class GcsInput(BaseModel):
    """Inputs for the Glasgow Coma Scale.

    Each subscale has its own published range:
        * Eye opening: 1-4
        * Verbal response: 1-5 (paediatric grids exist but are out of
          scope here — the calculator stays adult-only).
        * Motor response: 1-6
    """

    model_config = ConfigDict(extra="forbid")

    eye: Annotated[int, Field(ge=1, le=4)]
    verbal: Annotated[int, Field(ge=1, le=5)]
    motor: Annotated[int, Field(ge=1, le=6)]


def compute_gcs(input: GcsInput) -> ScoreResult:
    components = {
        "eye": input.eye,
        "verbal": input.verbal,
        "motor": input.motor,
    }
    total = input.eye + input.verbal + input.motor
    if total <= 8:
        band = "SEVERE"
    elif total <= 12:
        band = "MODERATE"
    else:
        band = "MILD"
    return ScoreResult(
        name="GCS",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale=(
            "Glasgow Coma Scale (adult). ≤8 severe (typically intubation "
            "considered), 9-12 moderate, ≥13 mild."
        ),
    )


# ---------------------------------------------------------------------------
# Alvarado score — Acute appendicitis
# ---------------------------------------------------------------------------


class AlvaradoInput(BaseModel):
    """Inputs for the Alvarado score (MANTRELS) for acute appendicitis.

    Two components carry 2 points (RLQ tenderness, leucocytosis); the
    other six binary criteria carry 1 point each. Total 0-10.
    """

    model_config = ConfigDict(extra="forbid")

    migration_to_rlq: bool
    anorexia: bool
    nausea_or_vomiting: bool
    tenderness_in_rlq: bool  # 2 points
    rebound_pain: bool
    elevated_temperature_over_37_3: bool
    leukocytosis_over_10k: bool  # 2 points
    left_shift_neutrophils_75: bool


def compute_alvarado(input: AlvaradoInput) -> ScoreResult:
    components = {
        "migration_to_rlq": int(input.migration_to_rlq),
        "anorexia": int(input.anorexia),
        "nausea_or_vomiting": int(input.nausea_or_vomiting),
        "tenderness_in_rlq": 2 if input.tenderness_in_rlq else 0,
        "rebound_pain": int(input.rebound_pain),
        "elevated_temperature_over_37_3": int(input.elevated_temperature_over_37_3),
        "leukocytosis_over_10k": 2 if input.leukocytosis_over_10k else 0,
        "left_shift_neutrophils_75": int(input.left_shift_neutrophils_75),
    }
    total = sum(components.values())
    if total >= 7:
        band = "HIGH"
    elif total >= 5:
        band = "MODERATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="Alvarado",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale=(
            "Alvarado score for acute appendicitis (MANTRELS) applied; "
            "≥7 high (surgical consult / appendectomy), 5-6 moderate "
            "(observation + imaging), ≤4 low (alternative diagnoses)."
        ),
    )


# ---------------------------------------------------------------------------
# Ottawa Ankle Rules
# ---------------------------------------------------------------------------


class OttawaAnkleInput(BaseModel):
    """Inputs for the Ottawa Ankle Rules.

    Imaging indicated when there is ankle pain in the malleolar zone AND
    any of: bone tenderness at posterior edge or tip of lateral/medial
    malleolus, inability to bear weight for 4 steps both at injury time
    AND in ED.
    """

    model_config = ConfigDict(extra="forbid")

    pain_in_malleolar_zone: bool
    tenderness_posterior_edge_lateral_malleolus: bool
    tenderness_posterior_edge_medial_malleolus: bool
    unable_to_bear_weight_4_steps_both_times: bool


def compute_ottawa_ankle(input: OttawaAnkleInput) -> ScoreResult:
    indicates_radiograph = input.pain_in_malleolar_zone and (
        input.tenderness_posterior_edge_lateral_malleolus
        or input.tenderness_posterior_edge_medial_malleolus
        or input.unable_to_bear_weight_4_steps_both_times
    )
    components = {
        "pain_in_malleolar_zone": int(input.pain_in_malleolar_zone),
        "tenderness_posterior_edge_lateral_malleolus": int(
            input.tenderness_posterior_edge_lateral_malleolus
        ),
        "tenderness_posterior_edge_medial_malleolus": int(
            input.tenderness_posterior_edge_medial_malleolus
        ),
        "unable_to_bear_weight_4_steps_both_times": int(
            input.unable_to_bear_weight_4_steps_both_times
        ),
    }
    band = (
        "RADIOGRAPH_INDICATED" if indicates_radiograph else "RADIOGRAPH_NOT_INDICATED"
    )
    return ScoreResult(
        name="Ottawa-Ankle",
        computable=True,
        value=1 if indicates_radiograph else 0,
        band=band,
        components=components,
        rationale=(
            "Ottawa Ankle Rules applied; ankle X-ray indicated when "
            "malleolar-zone pain coexists with any of: posterior-edge "
            "tenderness (lateral or medial malleolus) OR inability to "
            "bear weight for 4 steps at injury AND in ED."
        ),
    )


# ---------------------------------------------------------------------------
# Ottawa Knee Rules
# ---------------------------------------------------------------------------


class OttawaKneeInput(BaseModel):
    """Inputs for the Ottawa Knee Rules.

    Imaging indicated when ANY of: age ≥55, isolated tenderness of
    patella, tenderness of fibular head, inability to flex to 90°,
    inability to bear weight for 4 steps both at injury and in ED.
    """

    model_config = ConfigDict(extra="forbid")

    age_55_or_more: bool
    isolated_tenderness_of_patella: bool
    tenderness_of_fibular_head: bool
    unable_to_flex_90: bool
    unable_to_bear_weight_4_steps_both_times: bool


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


def compute_ottawa_knee(input: OttawaKneeInput) -> ScoreResult:
    components = {
        "age_55_or_more": int(input.age_55_or_more),
        "isolated_tenderness_of_patella": int(input.isolated_tenderness_of_patella),
        "tenderness_of_fibular_head": int(input.tenderness_of_fibular_head),
        "unable_to_flex_90": int(input.unable_to_flex_90),
        "unable_to_bear_weight_4_steps_both_times": int(
            input.unable_to_bear_weight_4_steps_both_times
        ),
    }
    indicates_radiograph = any(components.values())
    band = (
        "RADIOGRAPH_INDICATED" if indicates_radiograph else "RADIOGRAPH_NOT_INDICATED"
    )
    return ScoreResult(
        name="Ottawa-Knee",
        computable=True,
        value=1 if indicates_radiograph else 0,
        band=band,
        components=components,
        rationale=(
            "Ottawa Knee Rules applied; X-ray indicated when ANY of: "
            "age ≥55, isolated patellar tenderness, fibular-head "
            "tenderness, inability to flex to 90°, inability to bear "
            "weight for 4 steps at injury AND in ED."
        ),
    )

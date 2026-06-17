"""Tier-2 infectious disease clinical scores.

Implements: Centor/McIsaac, PERC, TIMI.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .scores import ScoreResult


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


__all__ = [
    "CentorInput",
    "compute_centor",
    "PercInput",
    "compute_perc",
    "TimiInput",
    "compute_timi",
]

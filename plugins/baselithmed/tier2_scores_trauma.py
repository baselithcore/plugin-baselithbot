"""Tier-2 trauma / surgical clinical scores.

Implements: GCS, Alvarado, Ottawa Ankle Rules, Ottawa Knee Rules.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from .scores import ScoreResult


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


__all__ = [
    "GcsInput",
    "compute_gcs",
    "AlvaradoInput",
    "compute_alvarado",
    "OttawaAnkleInput",
    "compute_ottawa_ankle",
    "OttawaKneeInput",
    "compute_ottawa_knee",
]

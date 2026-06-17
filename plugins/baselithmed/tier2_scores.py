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

Implementation is split by clinical domain:
    * :mod:`tier2_scores_cardio` — HEART, Wells PE/DVT, CHA2DS2-VASc, HAS-BLED
    * :mod:`tier2_scores_infectious` — Centor/McIsaac, PERC, TIMI
    * :mod:`tier2_scores_trauma` — GCS, Alvarado, Ottawa Ankle/Knee
"""

from __future__ import annotations

from .tier2_scores_cardio import (
    Cha2ds2VascInput,
    HasBledInput,
    HeartScoreInput,
    WellsDvtInput,
    WellsPeInput,
    compute_cha2ds2_vasc,
    compute_has_bled,
    compute_heart,
    compute_wells_dvt,
    compute_wells_pe,
)
from .tier2_scores_infectious import (
    CentorInput,
    PercInput,
    TimiInput,
    compute_centor,
    compute_perc,
    compute_timi,
)
from .tier2_scores_trauma import (
    AlvaradoInput,
    GcsInput,
    OttawaAnkleInput,
    OttawaKneeInput,
    compute_alvarado,
    compute_gcs,
    compute_ottawa_ankle,
    compute_ottawa_knee,
)

__all__ = [
    # cardio
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
    # infectious
    "CentorInput",
    "compute_centor",
    "PercInput",
    "compute_perc",
    "TimiInput",
    "compute_timi",
    # trauma
    "GcsInput",
    "compute_gcs",
    "AlvaradoInput",
    "compute_alvarado",
    "OttawaAnkleInput",
    "compute_ottawa_ankle",
    "OttawaKneeInput",
    "compute_ottawa_knee",
]

"""Validated bedside clinical scores.

Three deterministic calculators consumed by the triage UI:

    * :func:`compute_news2` — `Royal College of Physicians NEWS2 (2017)`.
      Sums six physiology weights; ``≥7`` is the standard ICU/sepsis
      trigger.
    * :func:`compute_qsofa` — `Sepsis-3 quick SOFA`.
      Three binary criteria; ``≥2`` flags presumed sepsis.
    * :func:`compute_curb65` — Community-acquired pneumonia severity.
      Five binary criteria; ``≥2`` recommends inpatient evaluation.

All three return :class:`ScoreResult` instances that explicitly report
which inputs were missing, so the UI can show "non calcolabile" rather
than a misleading partial value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from .models.clinical import SymptomMatrix, Vitals


@dataclass
class ScoreResult:
    """Outcome of a single clinical-score computation."""

    name: str
    computable: bool
    value: int | None = None
    band: str | None = None
    components: dict[str, int] = field(default_factory=dict)
    missing_inputs: list[str] = field(default_factory=list)
    rationale: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "computable": self.computable,
            "value": self.value,
            "band": self.band,
            "components": self.components,
            "missing_inputs": self.missing_inputs,
            "rationale": self.rationale,
        }


# ---------------------------------------------------------------------------
# NEWS2 — Royal College of Physicians (2017)
# ---------------------------------------------------------------------------
# The weights below are the canonical RCP table. Two SpO2 scales exist:
# scale 1 is the default; scale 2 (hypercapnic risk) is not implemented
# here — defaulting to scale 1 is the conservative choice for triage.

_NEWS2_REQUIRED: Final[tuple[str, ...]] = (
    "respiratory_rate_bpm",
    "spo2_percent",
    "temperature_c",
    "systolic_bp_mmhg",
    "heart_rate_bpm",
    "avpu_or_gcs",
)


def _news2_respiration(rr: int) -> int:
    if rr <= 8:
        return 3
    if rr <= 11:
        return 1
    if rr <= 20:
        return 0
    if rr <= 24:
        return 2
    return 3


def _news2_spo2_scale1(spo2: int) -> int:
    if spo2 <= 91:
        return 3
    if spo2 <= 93:
        return 2
    if spo2 <= 95:
        return 1
    return 0


def _news2_temperature(t: float) -> int:
    if t <= 35.0:
        return 3
    if t <= 36.0:
        return 1
    if t <= 38.0:
        return 0
    if t <= 39.0:
        return 1
    return 2


def _news2_systolic_bp(sbp: int) -> int:
    if sbp <= 90:
        return 3
    if sbp <= 100:
        return 2
    if sbp <= 110:
        return 1
    if sbp <= 219:
        return 0
    return 3


def _news2_heart_rate(hr: int) -> int:
    if hr <= 40:
        return 3
    if hr <= 50:
        return 1
    if hr <= 90:
        return 0
    if hr <= 110:
        return 1
    if hr <= 130:
        return 2
    return 3


def _news2_consciousness(vitals: Vitals) -> int | None:
    """Return 3 when consciousness is impaired, 0 when alert, ``None`` if
    neither GCS nor AVPU is available."""
    if vitals.avpu is not None:
        return 0 if vitals.avpu == "A" else 3
    if vitals.gcs_total is not None:
        return 0 if vitals.gcs_total >= 15 else 3
    return None


def _news2_band(total: int) -> str:
    if total >= 7:
        return "HIGH"
    if total >= 5:
        return "MEDIUM"
    if total >= 1:
        return "LOW"
    return "MINIMAL"


def compute_news2(matrix: SymptomMatrix) -> ScoreResult:
    """Compute NEWS2 from ``matrix.vitals`` when available."""
    if matrix.vitals is None:
        return ScoreResult(
            name="NEWS2",
            computable=False,
            missing_inputs=list(_NEWS2_REQUIRED),
            rationale="No vital signs captured for this session.",
        )
    v = matrix.vitals
    components: dict[str, int] = {}
    missing: list[str] = []

    if v.respiratory_rate_bpm is not None:
        components["respiration"] = _news2_respiration(v.respiratory_rate_bpm)
    else:
        missing.append("respiratory_rate_bpm")
    if v.spo2_percent is not None:
        components["spo2"] = _news2_spo2_scale1(v.spo2_percent)
        if v.on_supplemental_o2:
            # RCP NEWS2: add 2 points when patient is on supplemental O2.
            components["oxygen_supplement"] = 2
    else:
        missing.append("spo2_percent")
    if v.temperature_c is not None:
        components["temperature"] = _news2_temperature(v.temperature_c)
    else:
        missing.append("temperature_c")
    if v.systolic_bp_mmhg is not None:
        components["systolic_bp"] = _news2_systolic_bp(v.systolic_bp_mmhg)
    else:
        missing.append("systolic_bp_mmhg")
    if v.heart_rate_bpm is not None:
        components["heart_rate"] = _news2_heart_rate(v.heart_rate_bpm)
    else:
        missing.append("heart_rate_bpm")

    conscious = _news2_consciousness(v)
    if conscious is not None:
        components["consciousness"] = conscious
    else:
        missing.append("avpu_or_gcs")

    if missing:
        return ScoreResult(
            name="NEWS2",
            computable=False,
            components=components,
            missing_inputs=missing,
            rationale=(
                f"Missing required inputs: {', '.join(missing)}. "
                "Capture remaining vitals to compute NEWS2."
            ),
        )

    total = sum(components.values())
    return ScoreResult(
        name="NEWS2",
        computable=True,
        value=total,
        band=_news2_band(total),
        components=components,
        rationale="RCP NEWS2 (2017) chart applied; scale 1 SpO2 assumed.",
    )


# ---------------------------------------------------------------------------
# qSOFA — Sepsis-3 (2016)
# ---------------------------------------------------------------------------
_QSOFA_REQUIRED: Final[tuple[str, ...]] = (
    "respiratory_rate_bpm",
    "systolic_bp_mmhg",
    "consciousness",
)


def compute_qsofa(matrix: SymptomMatrix) -> ScoreResult:
    """Compute the Sepsis-3 quick SOFA score (0-3) from vitals."""
    if matrix.vitals is None:
        return ScoreResult(
            name="qSOFA",
            computable=False,
            missing_inputs=list(_QSOFA_REQUIRED),
            rationale="No vital signs captured for this session.",
        )
    v = matrix.vitals
    components: dict[str, int] = {}
    missing: list[str] = []

    if v.respiratory_rate_bpm is not None:
        components["respiratory_rate"] = 1 if v.respiratory_rate_bpm >= 22 else 0
    else:
        missing.append("respiratory_rate_bpm")
    if v.systolic_bp_mmhg is not None:
        components["systolic_bp"] = 1 if v.systolic_bp_mmhg <= 100 else 0
    else:
        missing.append("systolic_bp_mmhg")

    # Altered mentation: GCS < 15 OR AVPU != A.
    altered: bool | None = None
    if v.gcs_total is not None:
        altered = v.gcs_total < 15
    elif v.avpu is not None:
        altered = v.avpu != "A"
    if altered is not None:
        components["altered_mentation"] = 1 if altered else 0
    else:
        missing.append("consciousness")

    if missing:
        return ScoreResult(
            name="qSOFA",
            computable=False,
            components=components,
            missing_inputs=missing,
            rationale=(
                f"Missing required inputs: {', '.join(missing)}. "
                "Capture remaining vitals to compute qSOFA."
            ),
        )

    total = sum(components.values())
    band = "POSITIVE" if total >= 2 else "NEGATIVE"
    return ScoreResult(
        name="qSOFA",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale="Sepsis-3 qSOFA (2016) applied; ≥2 implies sepsis suspicion.",
    )


# ---------------------------------------------------------------------------
# CURB-65 — BTS community-acquired pneumonia severity
# ---------------------------------------------------------------------------
_CURB65_REQUIRED: Final[tuple[str, ...]] = (
    "confusion",
    "blood_urea_mmol_l",
    "respiratory_rate_bpm",
    "systolic_bp_mmhg",
    "age_years",
)


def compute_curb65(matrix: SymptomMatrix) -> ScoreResult:
    """Compute CURB-65 from vitals + age + (optional) urea."""
    if matrix.vitals is None:
        return ScoreResult(
            name="CURB-65",
            computable=False,
            missing_inputs=list(_CURB65_REQUIRED),
            rationale="No vital signs captured for this session.",
        )
    v = matrix.vitals
    components: dict[str, int] = {}
    missing: list[str] = []

    if v.confusion is not None:
        components["confusion"] = 1 if v.confusion else 0
    else:
        missing.append("confusion")
    if v.blood_urea_mmol_l is not None:
        components["urea"] = 1 if v.blood_urea_mmol_l > 7.0 else 0
    else:
        missing.append("blood_urea_mmol_l")
    if v.respiratory_rate_bpm is not None:
        components["respiratory_rate"] = 1 if v.respiratory_rate_bpm >= 30 else 0
    else:
        missing.append("respiratory_rate_bpm")
    if v.systolic_bp_mmhg is not None and v.diastolic_bp_mmhg is not None:
        components["blood_pressure"] = (
            1 if v.systolic_bp_mmhg < 90 or v.diastolic_bp_mmhg <= 60 else 0
        )
    else:
        missing.append("systolic_bp_mmhg")
        # Don't double-flag diastolic — counted alongside SBP.
    if v.age_years is not None:
        components["age_65"] = 1 if v.age_years >= 65 else 0
    else:
        missing.append("age_years")

    if missing:
        return ScoreResult(
            name="CURB-65",
            computable=False,
            components=components,
            missing_inputs=missing,
            rationale=(
                f"Missing required inputs: {', '.join(missing)}. "
                "Capture remaining inputs to compute CURB-65."
            ),
        )

    total = sum(components.values())
    if total >= 3:
        band = "SEVERE"
    elif total == 2:
        band = "MODERATE"
    else:
        band = "LOW"
    return ScoreResult(
        name="CURB-65",
        computable=True,
        value=total,
        band=band,
        components=components,
        rationale="BTS CURB-65 score applied; ≥2 implies inpatient evaluation.",
    )


def compute_all_scores(matrix: SymptomMatrix) -> dict[str, dict[str, object]]:
    """Convenience wrapper returning all three scores as JSON-ready dicts."""
    return {
        "news2": compute_news2(matrix).to_dict(),
        "qsofa": compute_qsofa(matrix).to_dict(),
        "curb65": compute_curb65(matrix).to_dict(),
    }

"""
Typed clinical models for BaselithMed.

Hard invariants enforced here:
    * Subjective patient data (``SymptomMatrix``) is kept strictly separated
      from probabilistic deductions (``DifferentialDiagnosis``).
    * Every hypothesis carries an explicit confidence score in ``[0, 1]``.
    * The final ``TriageReport`` is never emitted as a free-form string;
      consumers must accept the typed object (or its ``model_dump`` JSON).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

TemporalRelation = Literal["PRECEDES", "COOCCURS", "AGGRAVATES", "RELIEVES"]


class Symptom(BaseModel):
    """A single symptom reported by the patient.

    ``raw_quote`` preserves the verbatim utterance for medico-legal traceability;
    ``canonical_name`` is the normalized SNOMED/ICD-friendly form.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    canonical_name: str
    raw_quote: str
    body_site: str | None = None
    onset: datetime | None = None
    severity_nrs: Annotated[int, Field(ge=0, le=10)] | None = None
    character: list[str] = Field(default_factory=list)
    icd10_hint: str | None = None
    source_turn_id: str


class TemporalLink(BaseModel):
    """Temporal/causal edge between two symptoms in the Symptom Graph."""

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    relation: TemporalRelation
    delta_minutes: int | None = None


AvpuLevel = Literal["A", "V", "P", "U"]


class Vitals(BaseModel):
    """Objective vital signs captured at intake.

    All fields are optional. Clinical-score calculators (NEWS2, qSOFA,
    CURB-65) tolerate missing fields and report partial / not-computable
    results — they never invent values.
    """

    model_config = ConfigDict(extra="forbid")

    heart_rate_bpm: Annotated[int, Field(ge=20, le=250)] | None = None
    systolic_bp_mmhg: Annotated[int, Field(ge=40, le=260)] | None = None
    diastolic_bp_mmhg: Annotated[int, Field(ge=20, le=200)] | None = None
    respiratory_rate_bpm: Annotated[int, Field(ge=4, le=60)] | None = None
    temperature_c: Annotated[float, Field(ge=28.0, le=43.0)] | None = None
    spo2_percent: Annotated[int, Field(ge=40, le=100)] | None = None
    on_supplemental_o2: bool = False
    # Glasgow Coma Scale total — when capture allows it.
    gcs_total: Annotated[int, Field(ge=3, le=15)] | None = None
    # AVPU consciousness scale: Alert / Voice / Pain / Unresponsive.
    avpu: AvpuLevel | None = None
    # Age in years and reported chronic confusion (used by CURB-65).
    age_years: Annotated[int, Field(ge=0, le=130)] | None = None
    confusion: bool | None = None
    blood_urea_mmol_l: Annotated[float, Field(ge=0.0, le=80.0)] | None = None
    measured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SymptomMatrix(BaseModel):
    """Aggregated subjective data captured from the patient.

    The matrix is the only place where patient-reported information may live;
    LLM deductions belong to ``DifferentialDiagnosis``.
    """

    model_config = ConfigDict(extra="forbid")

    symptoms: list[Symptom] = Field(default_factory=list)
    temporal_sequence: list[TemporalLink] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    # Pertinent negatives: canonical symptom names the patient explicitly
    # denied. Surfaced to clinicians and used to penalize incompatible
    # hypotheses during ranking.
    denied_symptoms: list[str] = Field(default_factory=list)
    # Captured during the interview for the intake report.
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    past_medical_history: list[str] = Field(default_factory=list)
    # Objective measurements (optional). Drives downstream NEWS2/qSOFA.
    vitals: Vitals | None = None


class DifferentialHypothesis(BaseModel):
    """One ranked candidate condition produced by the reasoning agent."""

    model_config = ConfigDict(extra="forbid")

    condition: str
    icd10: str | None = None
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    p_value_simulated: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    supporting_findings: list[str] = Field(default_factory=list)
    contradicting_findings: list[str] = Field(default_factory=list)
    recommended_workup: list[str] = Field(default_factory=list)


class DifferentialDiagnosis(BaseModel):
    """Ranked differential, sorted descending by ``confidence``."""

    model_config = ConfigDict(extra="forbid")

    hypotheses: list[DifferentialHypothesis] = Field(default_factory=list)
    model_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str | None = None


class ExtractedObservation(BaseModel):
    """Raw NER output used to upsert nodes in the Symptom Graph.

    Kept separate from ``Symptom`` so the agent layer can normalize before
    persisting to the graph.
    """

    model_config = ConfigDict(extra="forbid")

    symptoms: list[Symptom] = Field(default_factory=list)
    body_sites: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    temporal_links: list[TemporalLink] = Field(default_factory=list)
    # Canonical names of symptoms the patient explicitly denied this turn.
    denied_symptoms: list[str] = Field(default_factory=list)


class ReportStatus(StrEnum):
    """Lifecycle states of a triage report."""

    DRAFT = "DRAFT"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class TriageReport(BaseModel):
    """The standardized, validator-ready payload handed to the clinician.

    Never serialize this as plain prose: downstream consumers expect the JSON
    object (``model_dump(mode="json")``).
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str
    patient_pseudonym: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symptom_matrix: SymptomMatrix
    differential: DifferentialDiagnosis
    # ``triage`` typed here as dict to keep the clinical module free of a
    # circular import with ``triage.py``; the wrapping ``TriageDecision``
    # instance is dumped before assignment.
    triage: dict
    disclaimer: str = (
        "Decisione preliminare automatica. "
        "Validazione clinica umana obbligatoria prima di qualsiasi atto medico."
    )
    status: ReportStatus = ReportStatus.PENDING_VALIDATION
    validation_request_id: str | None = None
    validator_signature: str | None = None
    # Optional, deterministically rendered clinical-intake markdown that
    # mirrors the appoint-ready report template (Primary concern / HPI /
    # Pertinent negatives / Relevant history / Medications). Generated
    # without LLM calls so it never breaks the response shape.
    intake_report: str | None = None

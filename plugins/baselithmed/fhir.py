"""FHIR R4 export for BaselithMed triage reports.

Builds a minimal :rfc:`HL7 FHIR R4`-compatible :samp:`Bundle` (``type =
collection``) from a stored :class:`TriageReport`. The exporter is
intentionally dependency-free: it emits plain dicts, so we do not pull the
heavy ``fhir.resources`` package into the wheel.

Resource map:
    * ``Patient`` — pseudonymized identifier only (no PHI by construction).
    * ``Encounter`` — bound to the session_id and emission timestamp.
    * ``Condition`` (one per DDx hypothesis) — ICD-10 coded when available.
    * ``Observation`` (one per Symptom in the matrix) — SNOMED-style category.
    * ``ClinicalImpression`` — the deterministic triage decision + ranked DDx.

Only fields with deterministic provenance are emitted. Free-form clinician
notes and validator signatures are exposed in dedicated extensions so EHRs
can ignore them safely.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models.clinical import TriageReport
from .scores import compute_all_scores

FHIR_BUNDLE_PROFILE: str = (
    "http://baselithcore.xyz/fhir/StructureDefinition/baselithmed-triage-bundle"
)


def _patient_resource(report: TriageReport) -> dict[str, Any]:
    return {
        "resourceType": "Patient",
        "id": f"patient-{report.patient_pseudonym}",
        "identifier": [
            {
                "system": "urn:baselithmed:pseudonym",
                "value": report.patient_pseudonym,
            }
        ],
    }


def _encounter_resource(report: TriageReport) -> dict[str, Any]:
    return {
        "resourceType": "Encounter",
        "id": f"encounter-{report.session_id}",
        "status": "finished" if report.status.value == "VALIDATED" else "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "subject": {"reference": f"Patient/patient-{report.patient_pseudonym}"},
        "period": {"start": report.generated_at.isoformat()},
    }


def _condition_resource(
    report: TriageReport, index: int, hypothesis: Any
) -> dict[str, Any]:
    coding: list[dict[str, Any]] = []
    if hypothesis.icd10:
        coding.append(
            {
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": hypothesis.icd10,
                "display": hypothesis.condition,
            }
        )
    coding.append(
        {
            "system": "urn:baselithmed:condition-label",
            "code": hypothesis.condition,
            "display": hypothesis.condition,
        }
    )
    return {
        "resourceType": "Condition",
        "id": f"condition-{report.session_id}-{index}",
        "clinicalStatus": {
            "coding": [
                {
                    "system": (
                        "http://terminology.hl7.org/CodeSystem/condition-clinical"
                    ),
                    "code": "active",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": (
                        "http://terminology.hl7.org/CodeSystem/condition-ver-status"
                    ),
                    "code": "provisional",
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": (
                            "http://terminology.hl7.org/CodeSystem/condition-category"
                        ),
                        "code": "encounter-diagnosis",
                    }
                ]
            }
        ],
        "code": {"coding": coding, "text": hypothesis.condition},
        "subject": {"reference": f"Patient/patient-{report.patient_pseudonym}"},
        "encounter": {"reference": f"Encounter/encounter-{report.session_id}"},
        "evidence": [
            {"code": [{"text": finding}]} for finding in hypothesis.supporting_findings
        ],
        "extension": [
            {
                "url": (
                    "http://baselithcore.xyz/fhir/StructureDefinition/ddx-confidence"
                ),
                "valueDecimal": float(hypothesis.confidence),
            }
        ],
    }


def _observation_resource(
    report: TriageReport, index: int, symptom: Any
) -> dict[str, Any]:
    coding: list[dict[str, Any]] = []
    if symptom.icd10_hint:
        coding.append(
            {
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": symptom.icd10_hint,
                "display": symptom.canonical_name,
            }
        )
    coding.append(
        {
            "system": "urn:baselithmed:symptom",
            "code": symptom.canonical_name,
            "display": symptom.canonical_name,
        }
    )
    obs: dict[str, Any] = {
        "resourceType": "Observation",
        "id": f"observation-{report.session_id}-{index}",
        "status": "preliminary",
        "category": [
            {
                "coding": [
                    {
                        "system": (
                            "http://terminology.hl7.org/CodeSystem/observation-category"
                        ),
                        "code": "exam",
                    }
                ]
            }
        ],
        "code": {"coding": coding, "text": symptom.canonical_name},
        "subject": {"reference": f"Patient/patient-{report.patient_pseudonym}"},
        "encounter": {"reference": f"Encounter/encounter-{report.session_id}"},
    }
    if symptom.severity_nrs is not None:
        obs["valueQuantity"] = {
            "value": symptom.severity_nrs,
            "unit": "NRS",
            "system": "urn:baselithmed:severity",
            "code": "nrs-0-10",
        }
    if symptom.onset is not None:
        obs["effectiveDateTime"] = symptom.onset.isoformat()
    if symptom.body_site:
        obs["bodySite"] = {"text": symptom.body_site}
    return obs


def _clinical_impression_resource(report: TriageReport) -> dict[str, Any]:
    triage = report.triage if isinstance(report.triage, dict) else {}
    return {
        "resourceType": "ClinicalImpression",
        "id": f"impression-{report.session_id}",
        "status": (
            "completed" if report.status.value == "VALIDATED" else "in-progress"
        ),
        "subject": {"reference": f"Patient/patient-{report.patient_pseudonym}"},
        "encounter": {"reference": f"Encounter/encounter-{report.session_id}"},
        "date": report.generated_at.isoformat(),
        "summary": triage.get("rationale"),
        "finding": [
            {"itemCodeableConcept": {"text": h.condition}}
            for h in report.differential.hypotheses
        ],
        "extension": [
            {
                "url": ("http://baselithcore.xyz/fhir/StructureDefinition/triage-code"),
                "valueCode": triage.get("code"),
            },
            {
                "url": (
                    "http://baselithcore.xyz/fhir/StructureDefinition/report-status"
                ),
                "valueCode": report.status.value,
            },
        ],
    }


def _score_observation_resource(
    report: TriageReport, score: dict[str, Any]
) -> dict[str, Any]:
    name = str(score.get("name", "score"))
    safe_id = name.lower().replace(" ", "-")
    obs: dict[str, Any] = {
        "resourceType": "Observation",
        "id": f"score-{report.session_id}-{safe_id}",
        "status": "preliminary" if score.get("computable") else "registered",
        "category": [
            {
                "coding": [
                    {
                        "system": (
                            "http://terminology.hl7.org/CodeSystem/observation-category"
                        ),
                        "code": "survey",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "urn:baselithmed:clinical-score",
                    "code": name,
                    "display": name,
                }
            ],
            "text": name,
        },
        "subject": {"reference": f"Patient/patient-{report.patient_pseudonym}"},
        "encounter": {"reference": f"Encounter/encounter-{report.session_id}"},
    }
    if score.get("computable") and score.get("value") is not None:
        obs["valueInteger"] = score["value"]
    if score.get("band"):
        obs["interpretation"] = [{"text": score["band"]}]
    if score.get("missing_inputs"):
        obs["note"] = [
            {"text": f"Missing inputs: {', '.join(score['missing_inputs'])}"}
        ]
    return obs


def triage_report_to_fhir_bundle(report: TriageReport) -> dict[str, Any]:
    """Return a FHIR R4 ``Bundle`` (type=collection) for ``report``."""
    resources: list[dict[str, Any]] = [
        _patient_resource(report),
        _encounter_resource(report),
        _clinical_impression_resource(report),
    ]
    for i, h in enumerate(report.differential.hypotheses):
        resources.append(_condition_resource(report, i, h))
    for i, s in enumerate(report.symptom_matrix.symptoms):
        resources.append(_observation_resource(report, i, s))
    # Add NEWS2/qSOFA/CURB-65 as survey Observations when vitals are
    # present; non-computable scores still emit a "registered" Observation
    # so the EHR records the attempt + missing inputs.
    for score in compute_all_scores(report.symptom_matrix).values():
        resources.append(_score_observation_resource(report, score))

    entries = [
        {
            "fullUrl": f"urn:uuid:{res['id']}",
            "resource": res,
        }
        for res in resources
    ]
    return {
        "resourceType": "Bundle",
        "id": f"bundle-{report.session_id}",
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": {"profile": [FHIR_BUNDLE_PROFILE]},
        "entry": entries,
    }

"""
Symptom Graph schema: entities and relationships registered with the core
:class:`core.plugins.graph_plugin.GraphPlugin` machinery.

The shape of each dictionary matches the contract documented in
``register_entity_types`` / ``register_relationship_types`` so the core
catalog can validate and persist instances.
"""

from __future__ import annotations

from typing import Any, Final

SYMPTOM_GRAPH_ENTITIES: Final[list[dict[str, Any]]] = [
    {
        "type": "med_patient",
        "display_name": "Patient (pseudonymized)",
        "schema": {
            "pseudonym": str,
            "age_band": str,
            "sex": str,
        },
        "icon": "🧑",
    },
    {
        "type": "med_symptom",
        "display_name": "Symptom",
        "schema": {
            "canonical_name": str,
            "icd10_hint": str,
            "severity_nrs": int,
            "raw_quote": str,
            "source_turn_id": str,
        },
        "icon": "🤒",
    },
    {
        "type": "med_body_site",
        "display_name": "Body Site",
        "schema": {
            "region": str,
            "laterality": str,
        },
        "icon": "🫀",
    },
    {
        "type": "med_onset_event",
        "display_name": "Onset Event",
        "schema": {
            "timestamp": str,
            "trigger": str,
        },
        "icon": "⏱️",
    },
    {
        "type": "med_risk_factor",
        "display_name": "Risk Factor",
        "schema": {
            "name": str,
            "category": str,
        },
        "icon": "⚠️",
    },
    {
        "type": "med_medication",
        "display_name": "Medication",
        "schema": {
            "name": str,
            "dose": str,
            "route": str,
        },
        "icon": "💊",
    },
]


SYMPTOM_GRAPH_RELATIONSHIPS: Final[list[dict[str, Any]]] = [
    {
        "type": "MED_REPORTS",
        "source_types": ["med_patient"],
        "target_types": ["med_symptom"],
        "properties_schema": {"reported_at": str},
        "bidirectional": False,
    },
    {
        "type": "MED_LOCATED_AT",
        "source_types": ["med_symptom"],
        "target_types": ["med_body_site"],
        "properties_schema": {},
        "bidirectional": False,
    },
    {
        "type": "MED_ONSET_AT",
        "source_types": ["med_symptom"],
        "target_types": ["med_onset_event"],
        "properties_schema": {},
        "bidirectional": False,
    },
    {
        "type": "MED_PRECEDES",
        "source_types": ["med_symptom"],
        "target_types": ["med_symptom"],
        "properties_schema": {"delta_minutes": int},
        "bidirectional": False,
    },
    {
        "type": "MED_AGGRAVATES",
        "source_types": ["med_symptom"],
        "target_types": ["med_symptom"],
        "properties_schema": {},
        "bidirectional": False,
    },
    {
        "type": "MED_COMORBID_WITH",
        "source_types": ["med_patient"],
        "target_types": ["med_risk_factor"],
        "properties_schema": {},
        "bidirectional": False,
    },
    {
        "type": "MED_CURRENTLY_TAKES",
        "source_types": ["med_patient"],
        "target_types": ["med_medication"],
        "properties_schema": {"started_on": str},
        "bidirectional": False,
    },
]

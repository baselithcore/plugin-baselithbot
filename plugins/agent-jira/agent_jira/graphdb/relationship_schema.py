"""Central relationship taxonomy and metadata helpers for the graph layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from agent_jira.graphdb.query_builder import sanitize_label

EDGE_SCHEMA_VERSION = 2
DEFAULT_RELATIONSHIP_TYPE = "RELATED_TO"

RELATIONSHIP_ALIASES = {
    "RELATED": "RELATED_TO",
    "RELATES": "RELATES_TO",
    "RELATE": "RELATES_TO",
    "RELATEDTO": "RELATED_TO",
    "RELATESTO": "RELATES_TO",
    "COMPLEMENTS_WITH": "COMPLEMENTS",
    "MENTIONS": "MENTIONS",
}

ALLOWED_RELATIONSHIP_TYPES = {
    DEFAULT_RELATIONSHIP_TYPE,
    "RELATES_TO",
    "DEPENDS_ON",
    "BLOCKS",
    "COMPLEMENTS",
    "MODIFIES",
    "TRIGGERS",
    "DERIVES_FROM",
    "VERIFIES",
    "SATISFIES",
    "BELONGS_TO",
    "LINKED_ISSUE",
    "HAS_STAKEHOLDER",
    "TARGETS_RELEASE",
    "HAS_DEADLINE",
    "STARTS_AT",
    "ENDS_AT",
    "HAS_MEETING",
    "HAS_DECISION",
    "HAS_MILESTONE",
    "USES_TECH",
    "HAS_RISK",
    "MENTIONS",
}


def normalize_relationship_type(relationship: str | None) -> str:
    """Normalize free-form relationship names to the supported taxonomy."""
    raw = str(relationship or "").strip().upper().replace("-", "_").replace(" ", "_")
    sanitized = sanitize_label(raw)
    canonical = RELATIONSHIP_ALIASES.get(sanitized, sanitized)
    if canonical in ALLOWED_RELATIONSHIP_TYPES:
        return canonical
    return DEFAULT_RELATIONSHIP_TYPE


def build_relationship_properties(
    relationship: str | None,
    *,
    properties: Mapping[str, Any] | None = None,
    provenance: str | None = None,
    confidence: float | None = None,
    source_document_id: str | None = None,
    extraction_method: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    """Build a consistent relationship payload with provenance and schema metadata."""
    normalized_relationship = normalize_relationship_type(relationship)
    merged = dict(properties or {})
    now_iso = datetime.now(timezone.utc).isoformat()

    merged["relationship_type"] = normalized_relationship
    merged["edge_schema_version"] = EDGE_SCHEMA_VERSION
    merged["updated_at"] = now_iso
    merged.setdefault("created_at", now_iso)

    if provenance:
        merged["provenance"] = provenance
    else:
        merged.setdefault("provenance", "application")

    if source_document_id:
        merged["source_document_id"] = source_document_id
    if extraction_method:
        merged["extraction_method"] = extraction_method
    if evidence:
        merged["evidence"] = evidence
    if confidence is not None:
        merged["confidence"] = round(float(confidence), 4)

    return merged

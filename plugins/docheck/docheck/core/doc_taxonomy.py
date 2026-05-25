"""Document type taxonomy + per-type structurer node-types + agent applicability.

ADR-0011. Single source of truth for DocType enum and routing rules.
"""

from __future__ import annotations

from enum import StrEnum


class DocType(StrEnum):
    CONTRACT = "contract"
    POLICY = "policy"
    PROCEDURE = "procedure"
    DPIA = "dpia"
    AUDIT_REPORT = "audit_report"
    MANUAL = "manual"
    TECHNICAL_SPEC = "technical_spec"
    REGULATORY_TEXT = "regulatory_text"
    OTHER = "other"


ALL_DOC_TYPES: tuple[str, ...] = tuple(t.value for t in DocType)

# Confidence threshold below which classification is downgraded to OTHER.
LOW_CONFIDENCE_THRESHOLD = 0.55


# Structurer node-type taxonomy per DocType. Generic types ("title","section",
# "table","signature") always allowed; type-specific extend the set.
_BASE_NODE_TYPES: tuple[str, ...] = ("title", "section", "table", "signature")

NODE_TYPES_BY_DOC_TYPE: dict[DocType, tuple[str, ...]] = {
    DocType.CONTRACT: (*_BASE_NODE_TYPES, "article", "clause"),
    DocType.POLICY: (*_BASE_NODE_TYPES, "article", "clause", "obligation"),
    DocType.PROCEDURE: (*_BASE_NODE_TYPES, "step", "prerequisite", "warning"),
    DocType.DPIA: (
        *_BASE_NODE_TYPES,
        "processing_activity",
        "risk_assessment",
        "safeguard",
        "data_category",
    ),
    DocType.AUDIT_REPORT: (
        *_BASE_NODE_TYPES,
        "control",
        "evidence",
        "finding_ref",
        "scope",
    ),
    DocType.MANUAL: (*_BASE_NODE_TYPES, "chapter", "step", "warning"),
    DocType.TECHNICAL_SPEC: (
        *_BASE_NODE_TYPES,
        "requirement",
        "interface",
        "constraint",
    ),
    DocType.REGULATORY_TEXT: (*_BASE_NODE_TYPES, "article", "clause", "recital"),
    DocType.OTHER: (*_BASE_NODE_TYPES, "article", "clause"),
}


# Which agents apply to which DocType. Agent runs only if doc_type ∈ this set.
AGENT_APPLICABILITY: dict[str, frozenset[DocType]] = {
    "legal": frozenset(
        {
            DocType.CONTRACT,
            DocType.POLICY,
            DocType.PROCEDURE,
            DocType.DPIA,
            DocType.AUDIT_REPORT,
            DocType.OTHER,
        }
    ),
    "technical": frozenset(
        {
            DocType.CONTRACT,
            DocType.PROCEDURE,
            DocType.DPIA,
            DocType.AUDIT_REPORT,
            DocType.MANUAL,
            DocType.TECHNICAL_SPEC,
            DocType.OTHER,
        }
    ),
    "pii": frozenset(
        {
            DocType.CONTRACT,
            DocType.POLICY,
            DocType.DPIA,
            DocType.OTHER,
        }
    ),
}


def coerce_doc_type(value: str | None) -> DocType:
    """Parse free-form value to DocType, fallback OTHER."""
    if not value:
        return DocType.OTHER
    v = value.strip().lower()
    for t in DocType:
        if t.value == v:
            return t
    return DocType.OTHER


def node_types_for(doc_type: DocType | str) -> tuple[str, ...]:
    dt = coerce_doc_type(doc_type) if isinstance(doc_type, str) else doc_type
    return NODE_TYPES_BY_DOC_TYPE.get(dt, NODE_TYPES_BY_DOC_TYPE[DocType.OTHER])


def agent_applies(agent_name: str, doc_type: DocType | str) -> bool:
    dt = coerce_doc_type(doc_type) if isinstance(doc_type, str) else doc_type
    allowed = AGENT_APPLICABILITY.get(agent_name)
    if allowed is None:
        return True
    return dt in allowed

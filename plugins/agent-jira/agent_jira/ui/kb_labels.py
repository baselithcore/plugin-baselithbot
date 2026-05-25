"""Re-export UI-safe delle utility label condivise con il backend."""

from agent_jira.kb_labels import (
    DOC_LABEL_MAX_LENGTH,
    DOC_LABEL_PREFIX,
    DOCUMENT_LABEL_HASH_LENGTH,
    DOCUMENT_LABEL_MAX_LENGTH,
    DOCUMENT_LABEL_PREFIX,
    KB_LABEL_MAX_LENGTH,
    KB_LABEL_PREFIX,
    build_doc_label,
    build_document_label_candidates,
    build_kb_label,
    build_legacy_doc_label,
    build_legacy_kb_label,
    build_prefixed_doc_label,
    is_canonical_document_label,
    is_supported_document_label,
)

__all__ = [
    "DOC_LABEL_MAX_LENGTH",
    "DOC_LABEL_PREFIX",
    "DOCUMENT_LABEL_HASH_LENGTH",
    "DOCUMENT_LABEL_MAX_LENGTH",
    "DOCUMENT_LABEL_PREFIX",
    "KB_LABEL_MAX_LENGTH",
    "KB_LABEL_PREFIX",
    "build_doc_label",
    "build_document_label_candidates",
    "build_kb_label",
    "build_prefixed_doc_label",
    "build_legacy_doc_label",
    "build_legacy_kb_label",
    "is_canonical_document_label",
    "is_supported_document_label",
]

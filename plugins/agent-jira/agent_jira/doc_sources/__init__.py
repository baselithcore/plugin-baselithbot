from __future__ import annotations

from .filesystem import FilesystemDocumentSource  # noqa: F401  (trigger registration)
from .models import DocumentItem, DocumentSourceError
from .registry import (
    SourceFactory,
    create_document_sources,
    register_source,
    registered_sources,
)
from .web import WebDocumentSource  # noqa: F401  (trigger registration)

__all__ = [
    "DocumentItem",
    "DocumentSourceError",
    "FilesystemDocumentSource",
    "WebDocumentSource",
    "SourceFactory",
    "create_document_sources",
    "register_source",
    "registered_sources",
]

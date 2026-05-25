"""Document upload utilities used by the Project Manager tab."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from agent_jira.doc_sources import readers
from agent_jira.doc_sources.filesystem import FilesystemDocumentSource
from agent_jira.tenant_context import get_tenant_documents_root
from agent_jira.config import DOCUMENTS_ROOT

from .renderers import build_preview_block

UPLOAD_READERS: Dict[str, Callable[[Path], str]] = {
    ".md": readers.read_markdown,
    ".markdown": readers.read_markdown,
    ".pdf": readers.read_pdf,
    ".docx": readers.read_word,
    ".doc": readers.read_word,
    ".xlsx": readers.read_excel,
    ".xls": readers.read_excel,
    ".pptx": readers.read_powerpoint,
    ".ppt": readers.read_powerpoint,
    ".png": readers.read_image,
    ".jpg": readers.read_image,
    ".jpeg": readers.read_image,
    ".gif": readers.read_image,
    ".webp": readers.read_image,
    ".tif": readers.read_image,
    ".tiff": readers.read_image,
}

SUPPORTED_UPLOAD_TYPES: Tuple[str, ...] = tuple(sorted(set(UPLOAD_READERS.keys())))


def list_kb_documents() -> List[str]:
    root_path = get_tenant_documents_root(DOCUMENTS_ROOT)
    if not root_path.exists():
        return []
    entries: List[str] = []
    root = root_path.resolve()
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_UPLOAD_TYPES:
            entries.append(path.relative_to(root).as_posix())
    return sorted(entries, key=str.lower)


def _resolve_kb_document(document_name: str) -> Path:
    if not document_name:
        raise ValueError("Seleziona un documento presente nella knowledge base.")
    root_path = get_tenant_documents_root(DOCUMENTS_ROOT)
    if not root_path.exists():
        raise ValueError("La knowledge base non contiene documenti disponibili.")
    candidate = (root_path / Path(document_name)).resolve()
    root = root_path.resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError("Percorso documento non valido.")
    if not candidate.is_file():
        raise ValueError(
            "Il documento selezionato non esiste più nella knowledge base."
        )
    if candidate.suffix.lower() not in SUPPORTED_UPLOAD_TYPES:
        raise ValueError("Il documento selezionato ha un formato non supportato.")
    return candidate


def _append_kb_label_to_plan(plan: Any, kb_label: str) -> None:
    if not kb_label:
        return
    user_stories = getattr(plan, "user_stories", None)
    if not user_stories:
        return
    for story in user_stories:
        labels = list(getattr(story, "labels", []) or [])
        labels.append(kb_label)
        deduped = list(dict.fromkeys(label for label in labels if label))
        story.labels = deduped


def resolve_kb_document(document_name: str) -> Path:
    """Public wrapper to validate and resolve a KB document path."""

    return _resolve_kb_document(document_name)


def append_kb_label_to_plan(plan: Any, kb_label: str) -> None:
    """Public wrapper to attach the context label to every user story in a plan."""

    _append_kb_label_to_plan(plan, kb_label)


def load_uploaded_document(file_path: str) -> Tuple[str, Dict[str, Any]]:
    path = Path(file_path)
    if not path.exists():
        raise ValueError("Il file caricato non è più disponibile.")

    suffix = path.suffix.lower()
    reader = UPLOAD_READERS.get(suffix)
    if reader is None:
        raise ValueError(f"Formato '{suffix or 'sconosciuto'}' non supportato.")

    try:
        content = reader(path) or ""
    except Exception as exc:  # pragma: no cover - dipende da backends OCR
        raise ValueError(f"Impossibile leggere il file: {exc}") from exc

    if not content.strip():
        raise ValueError("Il documento non contiene testo analizzabile.")

    metadata: Dict[str, Any] = {
        "display_name": path.stem,  # ← Cambiato da path.name per rimuovere estensione
        "doc_type": FilesystemDocumentSource.EXTENSION_DOC_TYPE.get(suffix, "document"),
        "extension": suffix,
        "char_count": len(content),
        "size_kb": round(path.stat().st_size / 1024, 1),
    }
    preview = build_preview_block(content)
    if preview:
        metadata["preview"] = preview
    return content, metadata


__all__ = [
    "SUPPORTED_UPLOAD_TYPES",
    "append_kb_label_to_plan",
    "list_kb_documents",
    "load_uploaded_document",
    "resolve_kb_document",
]

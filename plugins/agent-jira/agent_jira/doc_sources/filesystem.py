from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

from agent_jira.kb_labels import build_kb_label
from agent_jira.nlp import extract_spacy_metadata, is_spacy_available
from agent_jira.tenant_context import get_tenant_documents_root
from agent_jira.config import DOCUMENTS_EXTENSIONS, DOCUMENTS_ROOT, MULTI_TENANT_ENABLED

from . import readers
from .models import DocumentItem
from .registry import register_source
from .utils import compute_fingerprint


class FilesystemDocumentSource:
    """Legge documenti dal filesystem locale (Markdown, PDF, Office, ...)."""

    MARKDOWN_EXTENSIONS = {".md", ".markdown"}
    WORD_EXTENSIONS = {".docx", ".doc"}
    EXCEL_EXTENSIONS = {".xlsx", ".xls"}
    POWERPOINT_EXTENSIONS = {".pptx", ".ppt"}
    PDF_EXTENSIONS = {".pdf"}
    IMAGE_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".tif",
        ".tiff",
    }

    EXTENSION_DOC_TYPE = {
        ".md": "markdown",
        ".markdown": "markdown",
        ".pdf": "pdf",
        ".docx": "word",
        ".doc": "word",
        ".xlsx": "spreadsheet",
        ".xls": "spreadsheet",
        ".pptx": "presentation",
        ".ppt": "presentation",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".gif": "image",
        ".webp": "image",
        ".tif": "image",
        ".tiff": "image",
    }

    def __init__(
        self,
        root: Path | str | None = None,
        *,
        extensions: Tuple[str, ...] | None = None,
    ) -> None:
        base_path = DOCUMENTS_ROOT if root is None else Path(root).expanduser()
        if not base_path.is_absolute():
            base_path = Path.cwd() / base_path
        self._base_root = base_path
        allowed = extensions or DOCUMENTS_EXTENSIONS
        self._extensions = tuple(ext.lower() for ext in allowed)
        self._spacy_ready = is_spacy_available()

    @property
    def _root(self) -> Path:
        """Root effettiva: tenant-scoped se multi-tenancy attivo e tenant presente.

        In multi-tenant mode senza tenant context restituisce la base_root ma
        _iter_files() rifiuterà di scansionarla per evitare ingestion cross-tenant.
        """
        if MULTI_TENANT_ENABLED:
            from agent_jira.tenant_context import get_current_tenant_id

            if get_current_tenant_id() is not None:
                return get_tenant_documents_root(self._base_root)
        return self._base_root

    def _iter_files(self) -> Iterator[Path]:
        # Hard guard: in multi-tenant mode senza tenant corrente NON si scansiona
        # la root globale (che contiene sottocartelle per-tenant). Questo impedisce
        # che il bootstrap senza context indicizzi dati di tutti i tenant con
        # tenant_id=None, rendendoli di fatto "pubblici".
        if MULTI_TENANT_ENABLED:
            from agent_jira.tenant_context import get_current_tenant_id

            if get_current_tenant_id() is None:
                print(
                    "[filesystem] ⚠️ MULTI_TENANT_ENABLED ma nessun tenant nel contesto: "
                    "scansione saltata per sicurezza (evita cross-tenant leak).",
                    file=sys.stderr,
                )
                return

        root = self._root
        if not root.exists():
            print(
                f"[filesystem] ⚠️ Cartella documenti non trovata: {root}",
                file=sys.stderr,
            )
            return

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self._extensions:
                continue
            yield path

    def _read_file(self, path: Path) -> Optional[str]:
        suffix = path.suffix.lower()
        if suffix in self.MARKDOWN_EXTENSIONS:
            return readers.read_markdown(path)
        if suffix in self.PDF_EXTENSIONS:
            return readers.read_pdf(path)
        if suffix in self.WORD_EXTENSIONS:
            return readers.read_word(path)
        if suffix in self.EXCEL_EXTENSIONS:
            return readers.read_excel(path)
        if suffix in self.POWERPOINT_EXTENSIONS:
            return readers.read_powerpoint(path)
        if suffix in self.IMAGE_EXTENSIONS:
            return readers.read_image(path)
        print(
            f"[filesystem] ⚠️ Estensione non supportata {suffix} per {path}",
            file=sys.stderr,
        )
        return None

    def _derive_title(self, content: str, path: Path) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or path.stem
            if len(stripped) > 8:
                return stripped[:120].strip()
        return path.stem.replace("_", " ").replace("-", " ").strip() or path.stem

    def _document_metadata(self, path: Path, content: str) -> Dict[str, str]:
        doc_type = self.EXTENSION_DOC_TYPE.get(path.suffix.lower(), "document")
        try:
            relative_path = path.relative_to(self._root)
        except ValueError:
            relative_path = path.name

        metadata: Dict[str, str] = {
            "origin": "filesystem",
            "source": str(path),
            "relative_path": str(relative_path).replace("\\", "/"),
            "filename": path.name,
            "title": self._derive_title(content, path),
            "doc_type": doc_type,
        }

        try:
            parent_rel = (
                path.parent.relative_to(self._root)
                if path.parent != self._root
                else None
            )
        except ValueError:
            parent_rel = None
        if parent_rel:
            metadata["category"] = str(parent_rel).replace("\\", "/")

        if self._spacy_ready:
            spacy_metadata = extract_spacy_metadata(content)
            if spacy_metadata:
                metadata.update(spacy_metadata)

        return metadata

    def iter_headers(self) -> Iterator[Tuple[Path, float, int]]:
        """Yields (path, mtime, size_bytes) for all valid files."""
        for path in self._iter_files():
            try:
                stat = path.stat()
                yield path, stat.st_mtime, stat.st_size
            except OSError:
                continue

    def read_item(self, path: Path) -> Optional[DocumentItem]:
        """Reads and parses a single file item given its path."""
        # Security check: ensure path is within root
        try:
            path = path.resolve()
            if not str(path).startswith(str(self._root.resolve())):
                return None
        except Exception:
            return None

        content = self._read_file(path)
        if not content:
            return None

        fingerprint = compute_fingerprint(path, content)
        metadata = self._document_metadata(path, content)

        return DocumentItem(
            uid=build_kb_label(path),
            content=content,
            fingerprint=fingerprint,
            metadata=metadata,
        )

    def iter_items(self) -> Iterator[DocumentItem]:
        for path in self._iter_files():
            item = self.read_item(path)
            if item:
                yield item

    def close(self) -> None:
        return None


register_source("filesystem", FilesystemDocumentSource)

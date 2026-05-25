"""Document parsers dispatched by mime-type. Public API: parse()."""

from pathlib import Path

from ...schemas.state import Chunk
from . import docx, pdf, text, xlsx

_EXT_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".rst": "text/plain",
    ".log": "text/plain",
}


def _resolve_mime(path: Path, mime_type: str) -> str:
    """Trust extension when mime is missing/generic. Browsers often send
    `application/octet-stream` for files they can't classify."""
    mt = (mime_type or "").lower().split(";", 1)[0].strip()
    if mt in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    } or mt.startswith("text/"):
        return mt
    ext = path.suffix.lower()
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]
    return mt


def parse(path: Path, mime_type: str) -> list[Chunk]:
    mt = _resolve_mime(path, mime_type)
    match mt:
        case "application/pdf":
            return pdf.parse(path)
        case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return docx.parse(path)
        case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return xlsx.parse(path)
        case s if s.startswith("text/"):
            return text.parse(path)
        case _:
            raise ValueError(f"Unsupported mime: {mime_type or '(missing)'} (ext={path.suffix})")


__all__ = ["parse"]

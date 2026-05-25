"""Frontmatter schema loader.

The reference project hardcoded a list of insurance-specific frontmatter
keys inside :func:`WikiPage.to_payload`. Here every pack ships its own
``schema.yaml`` declaring the allowed fields, optional per-page-type
constraints, and which subset travels into the Qdrant payload.

The schema YAML is a thin layer over JSON-Schema-style rules: the fields
list covers the 90% case (name + type + required + enum + which page
types it applies to). Richer constraints can be added later under the
``extra`` key as raw JSON Schema and merged at validation time.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from llm_wiki.domain.pack import DomainPack, FrontmatterField
from llm_wiki.domain.registry import get_pack


class FrontmatterValidationError(ValueError):
    """Raised when a page's frontmatter violates the active schema."""

    def __init__(self, page: str, errors: list[str]) -> None:
        super().__init__(f"{page}: {', '.join(errors)}")
        self.page = page
        self.errors = errors


class FrontmatterSchema:
    """Validate and project frontmatter according to a Domain Pack.

    Lifecycle: build once per pack via :func:`get_schema`. Stateless past
    construction, safe to share across threads.
    """

    def __init__(
        self, pack: DomainPack, fields: list[FrontmatterField], extra: dict[str, Any]
    ):
        self._pack = pack
        self._fields = fields
        self._extra = extra
        self._by_name: dict[str, FrontmatterField] = {f.name: f for f in fields}

    @property
    def pack(self) -> DomainPack:
        return self._pack

    @property
    def fields(self) -> list[FrontmatterField]:
        return list(self._fields)

    def applicable_fields(self, page_type: str | None) -> list[FrontmatterField]:
        """Fields that apply to ``page_type`` (or all-pages fields if ``None``)."""
        out: list[FrontmatterField] = []
        for f in self._fields:
            if not f.page_types or (page_type and page_type in f.page_types):
                out.append(f)
        return out

    def payload_keys(self, page_type: str | None = None) -> list[str]:
        """Frontmatter keys safe to project into the Qdrant payload."""
        return [f.name for f in self.applicable_fields(page_type)]

    def validate(self, page_type: str | None, frontmatter: dict[str, Any]) -> list[str]:
        """Return a list of validation errors. Empty list = valid.

        Soft-validation by design: missing optional fields are silently
        ignored, unknown fields produce a warning string but don't raise.
        Callers decide whether to log or escalate.
        """
        errors: list[str] = []
        for field in self.applicable_fields(page_type):
            value = frontmatter.get(field.name)
            if value is None:
                if field.required:
                    errors.append(f"missing required field {field.name!r}")
                continue
            if not _matches_type(field.type, value):
                errors.append(f"{field.name!r} has wrong type: expected {field.type}")
                continue
            if field.enum is not None and value not in field.enum:
                errors.append(f"{field.name!r}={value!r} not in enum {field.enum}")
        return errors


def _matches_type(declared: str, value: Any) -> bool:
    if declared == "string":
        return isinstance(value, str)
    if declared == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if declared == "boolean":
        return isinstance(value, bool)
    if declared == "array":
        return isinstance(value, list)
    if declared == "object":
        return isinstance(value, dict)
    if declared == "date":
        # accept native date objects or YYYY-MM-DD strings; YAML loads dates as date()
        if isinstance(value, str):
            return len(value) >= 8 and value[4] == "-" and value[7] == "-"
        return hasattr(value, "isoformat")
    return True


_lock = threading.Lock()
_cached: FrontmatterSchema | None = None
_cached_pack_root: Path | None = None


def _read_schema_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"frontmatter schema not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping at root")
    return data


def _build_schema(pack: DomainPack) -> FrontmatterSchema:
    raw = _read_schema_yaml(pack.schema_path)
    fields_raw = raw.get("fields") or []
    if not isinstance(fields_raw, list):
        raise ValueError(f"{pack.schema_path}: 'fields' must be a list")

    fields: list[FrontmatterField] = []
    for entry in fields_raw:
        if not isinstance(entry, dict):
            raise ValueError(f"{pack.schema_path}: each field must be a mapping")
        try:
            fields.append(FrontmatterField(**entry))
        except ValidationError as exc:
            raise ValueError(
                f"{pack.schema_path}: invalid field {entry!r}\n{exc}"
            ) from exc

    extra = raw.get("extra") or {}
    if not isinstance(extra, dict):
        raise ValueError(f"{pack.schema_path}: 'extra' must be a mapping")
    return FrontmatterSchema(pack, fields, extra)


def get_schema() -> FrontmatterSchema:
    """Process-wide cached :class:`FrontmatterSchema` for the active pack."""
    global _cached, _cached_pack_root
    pack = get_pack()
    with _lock:
        if _cached is None or _cached_pack_root != pack.root:
            _cached = _build_schema(pack)
            _cached_pack_root = pack.root
        return _cached


def reset_schema_cache() -> None:
    """Test-only: drop the cached schema."""
    global _cached, _cached_pack_root
    with _lock:
        _cached = None
        _cached_pack_root = None

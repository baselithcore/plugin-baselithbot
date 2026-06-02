"""Pydantic request/plan/result models + constants for scaffolding."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DOMAIN_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
RESERVED_NAMES = {"_template", "default", "active"}

# Files in `_template` that must be present before we copy.
TEMPLATE_REQUIRED = ("pack.yaml", "schema.yaml", "prompts")


class ScaffoldError(RuntimeError):
    """Generic scaffolding failure. Caller decides HTTP code."""


class ProviderSettings(BaseModel):
    """Optional LLM provider section persisted in ``.env``.

    All fields optional. When ``vendor`` is set, the corresponding
    model/url/key fields are upserted into ``.env``. Existing values are
    overwritten only for keys explicitly supplied here; everything else
    in ``.env`` is preserved verbatim.

    ``model`` targets the chat/RAG model (``OLLAMA_MODEL`` /
    ``OPENAI_MODEL``). ``ingest_model`` targets the ingestion pipeline
    (``INGEST_OLLAMA_MODEL`` / ``INGEST_OPENAI_MODEL``) — typically a
    larger / more capable model than the chat one, since classify+plan
    quality compounds across every page of every document.

    Per-phase vendor split: when ``rag_vendor`` / ``ingest_vendor`` are
    set independently, the wiki dispatches RAG calls to one provider
    and ingest calls to another. Use case: privacy-sensitive RAG on a
    local Ollama + classify/plan on a capable OpenAI model, or vice
    versa. When omitted both phases inherit from ``vendor``.
    """

    model_config = ConfigDict(extra="forbid")

    vendor: Literal["ollama", "openai"] | None = None
    rag_vendor: Literal["ollama", "openai"] | None = None
    ingest_vendor: Literal["ollama", "openai"] | None = None
    model: str | None = None
    ingest_model: str | None = None
    base_url: str | None = None
    api_key: str | None = None  # only for openai; never returned in responses
    ollama_url: str | None = None
    openai_api_base: str | None = None
    openai_api_key: str | None = None


class ScaffoldRequest(BaseModel):
    """Inputs to :func:`scaffold_pack`. Validated server-side."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=64)
    label: str = Field("", max_length=128)
    description: str = Field("", max_length=512)
    language: str = Field("it", pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
    vault_root: str = Field(
        "",
        description="Absolute path. Empty = `<repo>/vaults/<name>`.",
    )
    write_env: bool = True
    force: bool = False
    activate: bool = Field(
        default=True,
        description="When true and `write_env` is set, point .env APP_DOMAIN to this pack.",
    )
    provider: ProviderSettings | None = None
    from_seed: str | None = Field(
        default=None,
        description=(
            "Optional: slug of an existing seed pack to fork from instead of "
            "the bare `_template`. The new pack inherits the seed's prompts, "
            "page types, schema and examples, but its YAML metadata (name/"
            "label/description/language) is overwritten with the values "
            "supplied in this request. The new pack is *not* marked as seed."
        ),
    )
    synthesize_prompts: bool = Field(
        default=True,
        description=(
            "When true (default) and the pack is NOT forked from a seed, "
            "call the configured LLM at scaffold time to synthesise a "
            "domain-tuned `prompts/system.j2` + `prompts/no_hits.j2` + "
            "`pack.yaml.subtypes` + `pack.yaml.ui.disclaimer` + "
            "`pack.yaml.ui.suggested_questions` from the user-supplied name/"
            "label/description. Failure is non-fatal: the bare `_template` "
            "files are kept and a warning surfaces in the ScaffoldResult."
        ),
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        v = v.strip()
        if not DOMAIN_NAME_RE.match(v):
            raise ValueError(
                "name must match [a-z][a-z0-9_-]* (snake-case ASCII, start with a letter)"
            )
        if v in RESERVED_NAMES:
            raise ValueError(f"name `{v}` is reserved")
        return v

    @field_validator("label", "description")
    @classmethod
    def _reject_control_chars(cls, v: str) -> str:
        if any(ord(c) < 0x20 and c not in ("\t",) for c in v):
            raise ValueError("control characters are not allowed")
        if "\x7f" in v:
            raise ValueError("DEL character is not allowed")
        return v

    @field_validator("vault_root")
    @classmethod
    def _strip_vault(cls, v: str) -> str:
        v = v.strip()
        if any(ord(c) < 0x20 for c in v) or "\x7f" in v:
            raise ValueError("vault_root contains invalid control characters")
        return v


@dataclass(frozen=True)
class FileOp:
    """One filesystem operation in a scaffold plan."""

    kind: Literal["mkdir", "copy", "edit", "env_upsert"]
    target: Path
    note: str = ""


class ScaffoldPlan(BaseModel):
    """Dry-run preview of a scaffold operation.

    The UI uses this to render a "Review" step before applying. Paths are
    rendered relative to the repo root for display purposes; actual writes
    use absolute paths.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    label: str
    description: str
    language: str
    target_pack_dir: Path
    vault_path: Path
    will_overwrite: bool
    pack_dir_exists: bool
    operations: list[dict[str, str]]
    env_diff: list[dict[str, str]]
    next_steps: list[str]


class ScaffoldResult(BaseModel):
    """Outcome of an applied scaffold operation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    target_pack_dir: Path
    vault_path: Path
    env_written: bool
    env_path: Path | None
    activated: bool
    requires_restart: bool = True
    next_steps: list[str]
    synthesis_applied: bool = False
    synthesis_model: str | None = None
    synthesis_warning: str | None = None

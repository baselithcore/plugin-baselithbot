"""Pydantic models + error type + small constant tables."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from llm_wiki.admin.prompt_synthesizer.validators import (
    _NEGATIVE_CONSTRAINT_GROUPS,
    _REQUIRED_SECTIONS,
    _assert_no_jinja_tags,
    _assert_valid_jinja,
    _has_unresolved_placeholders,
    _slugify_subtype,
)


class SynthesisError(RuntimeError):
    """The synthesizer was unable to produce a valid pack — caller falls back."""


_PAGE_TYPE_IDS = ("source", "concept", "entity", "topic")
_ALLOWED_ICONS = (
    "Sparkles",
    "FileSearch",
    "BookOpen",
    "GraduationCap",
    "Stethoscope",
    "Scale",
    "Wrench",
    "Briefcase",
    "Users",
    "Shield",
    "FileText",
    "Search",
    "HelpCircle",
    "Lightbulb",
    "Zap",
    "Building2",
    "ClipboardList",
)


class SuggestedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=80)
    hint: str = Field(min_length=1, max_length=120)
    icon: str = Field(min_length=1, max_length=32)
    prompt: str = Field(min_length=10, max_length=400)

    @field_validator("icon")
    @classmethod
    def _icon_in_allowlist(cls, v: str) -> str:
        if v not in _ALLOWED_ICONS:
            return "Sparkles"
        return v


class SynthesisResult(BaseModel):
    """Validated output of :func:`synthesize_pack`. Caller persists it."""

    model_config = ConfigDict(extra="forbid")

    system_prompt: str = Field(min_length=1500, max_length=12000)
    no_hits: str = Field(min_length=300, max_length=2500)
    subtypes: dict[str, list[str]] = Field(default_factory=dict)
    disclaimer: str = Field(min_length=40, max_length=600)
    suggested_questions: list[SuggestedQuestion] = Field(min_length=4, max_length=6)
    model: str
    vendor: str

    @field_validator("system_prompt")
    @classmethod
    def _system_has_sections(cls, v: str) -> str:
        lower = v.lower()
        missing = [s for s in _REQUIRED_SECTIONS if s not in lower]
        if missing:
            raise ValueError(f"system prompt missing required sections: {missing}")
        unsatisfied = [
            group
            for group in _NEGATIVE_CONSTRAINT_GROUPS
            if not any(variant in lower for variant in group)
        ]
        if unsatisfied:
            preview = ", ".join(group[0] for group in unsatisfied)
            raise ValueError(
                f"system prompt missing anti-hallucination negative constraint(s): "
                f"{preview}. The synthesised body must repeat the engine grounding "
                f"rules verbatim — small models tend to drop them and degrade the "
                f"prompt below the _template baseline."
            )
        _assert_valid_jinja(v, label="system_prompt")
        _assert_no_jinja_tags(v, label="system_prompt")
        if _has_unresolved_placeholders(v):
            raise ValueError("system prompt still contains <…> placeholders")
        return v

    @field_validator("no_hits")
    @classmethod
    def _no_hits_valid(cls, v: str) -> str:
        _assert_valid_jinja(v, label="no_hits")
        _assert_no_jinja_tags(v, label="no_hits")
        return v

    @field_validator("subtypes")
    @classmethod
    def _subtypes_keys(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for k, vals in v.items():
            if k not in _PAGE_TYPE_IDS:
                continue  # silently drop unknown page-type ids
            cleaned: list[str] = []
            seen: set[str] = set()
            for item in vals or []:
                if not isinstance(item, str):
                    continue
                slug = _slugify_subtype(item)
                if slug and slug not in seen:
                    cleaned.append(slug)
                    seen.add(slug)
                if len(cleaned) >= 8:
                    break
            if cleaned:
                out[k] = cleaned
        return out

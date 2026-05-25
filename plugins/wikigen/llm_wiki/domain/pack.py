"""Domain Pack contract.

A pack describes one vertical wiki (Legal, Medical, Insurance, ...). It is
declared on disk as ``domains/<name>/pack.yaml`` and validated into the
pydantic models below. The core engine never reads ``pack.yaml`` directly —
always through :func:`core.domain.registry.load_pack`.

YAML schema (minimal example)::

    name: legal
    label: "Wiki Legale"
    description: "Knowledge base sentenze, normative, contrattualistica"
    language: it
    page_types:
      - id: source
        label: "Fonte"
        prompt_template: source_page.j2
      - id: concept
        label: "Concetto"
        prompt_template: entity_page.j2
    subtypes: []
    frontmatter_schema: schema.yaml
    grouping: []
    ui:
      app_name: "Wiki Legale"
      vault_label: "Vault giuridico"
      empty_state: "Carica una sentenza per iniziare."

Adding fields here is a breaking change for every pack on disk: bump
``schema_version`` and migrate existing packs in lockstep.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = 1


class PageType(BaseModel):
    """One node in the page taxonomy of a domain.

    ``id`` is the canonical key written in frontmatter ``page_type``. Keep it
    snake_case ASCII — it travels through filesystem paths and JSON-schema
    enums fed to the LLM during planning.

    ``prompt_template`` is the filename of the Jinja2 template (relative to
    ``<pack>/prompts/``) used by the generator to draft pages of this type.
    Optional: a strategy can register code-side rendering instead.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(..., min_length=1)
    description: str | None = None
    prompt_template: str | None = None
    plural: str | None = None
    folder: str | None = Field(
        default=None,
        description=(
            "Subdirectory under WIKI_DIR where pages of this type live. "
            "Defaults to plural or `id`s. Example: 'concepts', 'sources'."
        ),
    )


class GroupingRule(BaseModel):
    """Declarative grouping rule served by ``GET /api/groups``.

    Replaces the hardcoded ``/api/editions`` endpoint of the insurance MVP.
    Each rule declares which frontmatter keys identify a group, which page
    type to scan, and how to derive the human label.

    ``key`` selects the rule from the API path ``/api/groups?rule=<key>``.
    ``group_by`` is an ordered list of frontmatter fields used as composite
    key. ``label_from`` is either a frontmatter field or a literal string
    template (``{title}``, ``{<field>}``).
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    page_type: str
    group_by: list[str] = Field(..., min_length=1)
    label_from: str = "{title}"
    sort_by: list[str] = Field(default_factory=list)
    extra_fields: list[str] = Field(default_factory=list)


class UISuggestedQuestion(BaseModel):
    """One starter card on the empty-state hero.

    The frontend renders these as clickable suggestions; ``prompt`` is the
    text that gets sent to the chat when the card is clicked. ``icon`` is
    a lucide-react icon name (e.g. ``Building2``, ``ShieldCheck``); the
    frontend has a default mapping per category if omitted.
    """

    model_config = ConfigDict(extra="forbid")

    label: str
    prompt: str
    hint: str = ""
    category: str = "default"
    icon: str | None = None


class UITheme(BaseModel):
    """Optional per-tenant color overrides applied at runtime by the
    frontend BrandingContext. Hex strings ('#003b5c'). When omitted the
    static ``branding.json`` defaults are used.
    """

    model_config = ConfigDict(extra="forbid")

    primary: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    primary_hover: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    accent: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class UILabels(BaseModel):
    """Branding strings + per-tenant theme sent via ``GET /api/branding``.

    The frontend layout (Tailwind, framer-motion, structure) is global;
    only copy, suggested questions and a few CSS variables vary. Avoid
    putting font sizes or layout values here.
    """

    model_config = ConfigDict(extra="forbid")

    app_name: str
    short_name: str | None = None
    vault_label: str = "Vault"
    tagline: str | None = None
    empty_state: str | None = None
    hero_question: str | None = None
    hero_highlight: str | None = None
    hero_pill: str | None = None
    hero_pill_icon: str | None = None
    disclaimer: str | None = None
    suggested_questions: list[UISuggestedQuestion] = Field(default_factory=list)
    theme: UITheme | None = None
    logo_path: str | None = Field(
        default=None,
        description="Path relative to pack root (e.g. 'assets/logo.svg').",
    )
    page_type_labels: dict[str, str] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class FrontmatterField(BaseModel):
    """One declared frontmatter field used to validate wiki pages.

    Loaded from ``<pack>/schema.yaml`` and consumed by
    :class:`core.domain.schema.FrontmatterSchema`. We keep validation rules
    simple by design: rich JSON-Schema clauses go in ``schema.yaml`` as raw
    JSON Schema and are merged at validation time.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    type: Literal["string", "integer", "number", "boolean", "array", "object", "date"]
    required: bool = False
    page_types: list[str] = Field(
        default_factory=list,
        description="Page types this field applies to. Empty = applies to all.",
    )
    enum: list[Any] | None = None
    description: str | None = None


class GraphEntityType(BaseModel):
    """One node type in the knowledge graph (graphify-inspired).

    Vertical-tuned ontology declared in pack.yaml under ``graph.entity_types``.
    Used by the extraction prompt to enumerate allowed ``kind`` values, and by
    the API ``/api/graph/search?kind=`` filter.

    ``id`` is canonical (snake_case ASCII). ``examples`` seed the few-shot
    LLM prompt.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(..., min_length=1)
    description: str | None = None
    examples: list[str] = Field(default_factory=list)


class GraphRelationType(BaseModel):
    """One edge type in the knowledge graph.

    ``directed`` defaults true. The extraction LLM is instructed to emit
    relations only with these ``id`` values (JSON-schema enum). Engine adds
    structural edges (``MENTIONS``, ``DEFINED_IN``, ``LINKS_TO``) which are
    not declared here.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, pattern=r"^[A-Z][A-Z0-9_]*$")
    label: str = Field(..., min_length=1)
    description: str | None = None
    directed: bool = True
    examples: list[str] = Field(default_factory=list)


class GraphSpec(BaseModel):
    """Knowledge-graph contract for the pack.

    Drives entity/relation extraction from wiki pages. When absent, engine
    falls back to a generic ontology (``concept``/``entity``/``source`` +
    ``RELATES_TO``/``PART_OF``/``DERIVES_FROM``). Defining a pack-specific
    spec is strongly recommended — it tunes the LLM extraction prompt to the
    vertical's vocabulary.

    ``extraction_hints`` is free-form Italian guidance prepended to the
    extraction prompt (e.g. for insurance: "Identifica garanzie, pack,
    franchigie come Concept; Compagnie come Entity; Polizze come Source.").
    """

    model_config = ConfigDict(extra="forbid")

    entity_types: list[GraphEntityType] = Field(default_factory=list)
    relation_types: list[GraphRelationType] = Field(default_factory=list)
    extraction_hints: str = ""

    @field_validator("entity_types")
    @classmethod
    def _unique_entity_ids(cls, v: list[GraphEntityType]) -> list[GraphEntityType]:
        ids = [e.id for e in v]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"duplicate graph.entity_types ids: {dupes}")
        return v

    @field_validator("relation_types")
    @classmethod
    def _unique_relation_ids(cls, v: list[GraphRelationType]) -> list[GraphRelationType]:
        ids = [r.id for r in v]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"duplicate graph.relation_types ids: {dupes}")
        return v


def _default_graph_spec() -> GraphSpec:
    """Generic ontology used when pack.yaml omits ``graph:``.

    Intentionally minimal — covers most verticals out-of-the-box. Packs
    SHOULD override with their own vocabulary for better extraction.
    """
    return GraphSpec(
        entity_types=[
            GraphEntityType(id="concept", label="Concetto", examples=["clausola", "principio"]),
            GraphEntityType(id="entity", label="Entità", examples=["organizzazione", "persona"]),
            GraphEntityType(id="source", label="Fonte", examples=["documento", "sentenza"]),
        ],
        relation_types=[
            GraphRelationType(id="RELATES_TO", label="è correlato a"),
            GraphRelationType(id="PART_OF", label="fa parte di"),
            GraphRelationType(id="DERIVES_FROM", label="deriva da"),
            GraphRelationType(id="DEFINED_BY", label="è definito da"),
        ],
        extraction_hints="",
    )


class DomainPack(BaseModel):
    """The full descriptor for a vertical wiki.

    Attributes
    ----------
    schema_version
        Bumped only when the contract above changes. Refuse to load packs
        with an unknown version — fail fast beats silent drift.
    root
        Absolute path of the pack directory on disk. Set by the registry
        after loading; not present in YAML.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    # Leading underscore is reserved for engine-shipped scaffolds (e.g. `_template`).
    # Domains scaffolded by `wiki-wl init` must start with a lowercase letter.
    name: str = Field(..., pattern=r"^[a-z_][a-z0-9_-]*$")
    label: str
    description: str = ""
    language: str = Field(default="it", pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
    page_types: list[PageType]
    subtypes: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Optional sub-classification within a page type. "
            "Example for insurance: {'concept': ['prodotto-assicurativo', 'garanzia']}."
        ),
    )
    frontmatter_schema: str = Field(
        default="schema.yaml",
        description="Filename of the frontmatter schema, relative to pack root.",
    )
    grouping: list[GroupingRule] = Field(default_factory=list)
    ui: UILabels
    examples_dir: str = "examples"
    prompts_dir: str = "prompts"
    extractors_dir: str | None = None

    seed: bool = Field(
        default=False,
        description=(
            "True for engine-shipped example packs (insurance, legal, …). The "
            "wizard surfaces seeds in a separate 'examples' section and offers "
            "a Fork action; the runtime treats them as non-active until the "
            "user explicitly forks one. Custom packs scaffolded by the wizard "
            "default to false."
        ),
    )

    graph: GraphSpec = Field(
        default_factory=_default_graph_spec,
        description=(
            "Knowledge-graph ontology for entity/relation extraction "
            "(graphify-inspired). Vertical-specific node + edge types drive "
            "the LLM extraction prompt and the /api/graph/* surface. Omit to "
            "use the generic engine default (concept/entity/source)."
        ),
    )

    # set by registry, not stored in YAML
    root: Path | None = Field(default=None, exclude=True)

    @field_validator("page_types")
    @classmethod
    def _unique_page_type_ids(cls, v: list[PageType]) -> list[PageType]:
        ids = [p.id for p in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"duplicate page_type ids: {sorted(set(dupes))}")
        return v

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, v: int) -> int:
        if v != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported pack schema_version {v}; engine expects {SCHEMA_VERSION}"
            )
        return v

    def page_type(self, page_type_id: str) -> PageType | None:
        """Return the :class:`PageType` matching ``page_type_id`` or ``None``."""
        for pt in self.page_types:
            if pt.id == page_type_id:
                return pt
        return None

    def has_page_type(self, page_type_id: str) -> bool:
        return self.page_type(page_type_id) is not None

    @property
    def prompts_path(self) -> Path:
        if self.root is None:
            raise RuntimeError("pack.root not set; load via registry.load_pack()")
        return self.root / self.prompts_dir

    @property
    def examples_path(self) -> Path:
        if self.root is None:
            raise RuntimeError("pack.root not set; load via registry.load_pack()")
        return self.root / self.examples_dir

    @property
    def schema_path(self) -> Path:
        if self.root is None:
            raise RuntimeError("pack.root not set; load via registry.load_pack()")
        return self.root / self.frontmatter_schema

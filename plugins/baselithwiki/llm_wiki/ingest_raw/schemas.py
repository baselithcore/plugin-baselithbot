"""Pydantic models for ingest pipeline output.

Two purposes:
1. **Deterministic post-LLM validation**: every block produced by the
   model is validated here.
2. **JSON-schema constrained decoding**: ``model_json_schema()`` is fed to
   the provider (Ollama ``format=...``, OpenAI ``response_format``) so the
   LLM is forced to return parsable JSON.

Domain-coupling note
--------------------
The reference project hardcoded ``Literal[...]`` types for ``page_type``,
``subtype``, ``source_type``, ``rango`` etc. — listing every value used by
the insurance vertical. White-label drops those: pack-specific enums move
into the active :class:`FrontmatterSchema` and validation happens there.

The generic ``str`` typing here keeps schemas pack-agnostic; LLM
constrained decoding still works because the pack-driven planner injects
allowed enum values at runtime via :func:`build_classification_schema` and
:func:`build_plan_schema`.
"""

from __future__ import annotations

from datetime import date as Date
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    create_model,
    field_validator,
    model_validator,
)

from llm_wiki.domain.pack import DomainPack

# --- structured blocks (kept lossy-string-typed for portability) ------------


class ArticoloRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fonte: str
    articolo: str
    pagina: int | None = None


class TabellaStrutturata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str
    fonte: str
    articolo: str
    pagina: int | None = None
    sezione: str | None = None
    righe: list[dict[str, Any]]


class RegolaCondizionale(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    etichetta: str
    tipo: str
    fonte: str
    articolo: str
    condizione: dict[str, Any]
    effetto: dict[str, Any]
    eccezioni: list[str] = Field(default_factory=list)


class VerbatimQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    testo: str
    fonte: str
    articolo: str
    pagina: int | None = None
    note_curatore: str | None = None


# --- page plan --------------------------------------------------------------


class PagePlan(BaseModel):
    """One wiki page to generate. Output of the planner.

    Page-type and subtype are free strings here; the planner injects
    pack-aware enums when building the JSON schema sent to the LLM.
    """

    model_config = ConfigDict(extra="forbid")

    target_path: str = ""
    page_type: str = ""
    subtype: str | None = None
    title: str = ""
    source_sections: list[str] = Field(default_factory=list)
    wikilinks_expected: list[str] = Field(default_factory=list)
    priority: int = 100
    notes: str | None = None

    # Loose JSON mode (Ollama default): il LLM emette `null` su required
    # fields anche con default pydantic, e None non passa validation
    # contro `list[str]` / `str`. Coerce None → default così il primo
    # tentativo passa invece di bruciare un retry da 30-60s. Campi truly-
    # opzionali (subtype, notes) restano `str | None`.
    @field_validator("target_path", "page_type", "title", mode="before")
    @classmethod
    def _none_str_to_empty(cls, v: Any) -> Any:
        return "" if v is None else v

    @field_validator("source_sections", "wikilinks_expected", mode="before")
    @classmethod
    def _none_list_to_empty(cls, v: Any) -> Any:
        return [] if v is None else v

    @field_validator("priority", mode="before")
    @classmethod
    def _none_int_to_default(cls, v: Any) -> Any:
        return 100 if v is None else v


class IngestPlan(BaseModel):
    """Complete ingest plan: source page + derived pages."""

    model_config = ConfigDict(extra="forbid")

    # Optional: l'orchestrator lo conosce (path del PDF in input), il LLM no.
    # Iniettato post-hoc in `_normalize_plan` da `source_path`. Lasciarlo
    # required forzava il LLM a indovinarlo, fallendo lo schema su modelli
    # piccoli e bruciando un retry su quelli grandi.
    source_file: str = ""
    source_page: PagePlan
    derived_pages: list[PagePlan] = Field(default_factory=list)
    source_type: str | None = None
    edizione: str | None = None
    edizione_iso: Date | None = None
    note: str | None = None
    # Provenance: numero di pagine del documento sorgente originale.
    # Iniettato post-hoc dall'orchestrator (`source_pages_count = doc.n_pages`).
    # Persistito in frontmatter delle source page e propagato a Qdrant
    # payload via `payload.update(meta)` — unlock click-to-source future
    # (UI legge `source_pages_count` per sapere se aprire PDF su page=N).
    source_pages_count: int | None = None

    # Modelli piccoli (qwen 7b, llama3 8b) spesso emettono `source_page`
    # come stringa ("wiki/sources/foo.md") invece dell'oggetto strutturato.
    # Coerce string → ``{"target_path": str}``: il resto del PagePlan ha
    # default sicuri così il primo retry passa invece di bruciare 3 round-trip
    # da 30-60s ciascuno. Stesso trattamento per `derived_pages` element-wise.
    @field_validator("source_page", mode="before")
    @classmethod
    def _coerce_source_page(cls, v: Any) -> Any:
        if isinstance(v, str):
            return {"target_path": v}
        return v

    @model_validator(mode="before")
    @classmethod
    def _wrap_flat_pageplan(cls, data: Any) -> Any:
        """Rewrap PagePlan-flat input.

        qwen 7b a volte emette ``plan`` come PagePlan flat (con
        ``target_path``, ``title``, ``page_type``, ``source_sections``,
        ``wikilinks_expected`` al livello root) invece di nidificarlo
        sotto ``source_page``. Rileva il pattern e ricompone l'oggetto
        corretto. Idempotente: se ``source_page`` esiste già, no-op.
        """
        if not isinstance(data, dict):
            return data
        if "source_page" in data:
            return data
        page_plan_keys = {
            "target_path",
            "title",
            "page_type",
            "subtype",
            "source_sections",
            "wikilinks_expected",
            "priority",
            "notes",
        }
        leaked = {k: data[k] for k in list(data) if k in page_plan_keys}
        if not leaked:
            return data
        # Estrai le chiavi PagePlan dal root e rimpacchettale sotto source_page.
        for k in leaked:
            data.pop(k, None)
        data["source_page"] = leaked
        return data

    @field_validator("derived_pages", mode="before")
    @classmethod
    def _coerce_derived_pages(cls, v: Any) -> Any:
        if v is None:
            return []
        if not isinstance(v, list):
            return v
        out: list[Any] = []
        for item in v:
            if isinstance(item, str):
                out.append({"target_path": item})
            else:
                out.append(item)
        return out


# --- pack-aware schema builders ---------------------------------------------


class Classification(BaseModel):
    """Result of the classify step. Free-form so packs without enums work."""

    source_type: str = ""
    title: str = ""
    edizione: str | None = None
    edizione_iso: Date | None = None
    modello: str | None = None
    author: str | None = None
    riservatezza: str = "bassa"
    rami_o_argomenti: list[str] = Field(default_factory=list)

    # Loose JSON mode (Ollama default) non enforce enum: il LLM può emettere
    # `null` per campi richiesti. Coerce None → "" così la validazione
    # pydantic passa al primo colpo invece di buttare via il round-trip.
    # Il fallback è raccolto da `_normalize_plan` (che propaga
    # classification.source_type → plan.source_type) e dal linter.
    @field_validator("source_type", "title", "riservatezza", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return "" if v is None else v


def build_classification_schema(pack: DomainPack) -> type[Classification]:
    """Specialise :class:`Classification` with the pack's allowed source_type values.

    When the pack declares ``subtypes.source = [...]``, the JSON schema
    emitted to the LLM uses an ``enum`` for ``source_type``. Otherwise the
    field stays a free string.
    """
    allowed = pack.subtypes.get("source") or []
    if not allowed:
        return Classification

    DynamicCls: type[Classification] = create_model(  # type: ignore[call-overload]
        "ClassificationDynamic",
        __base__=Classification,
        source_type=(str, Field(..., json_schema_extra={"enum": list(allowed)})),
    )
    return DynamicCls


def build_plan_schema(pack: DomainPack) -> type[IngestPlan]:
    """Constrain ``page_type`` to the pack's declared page types in the JSON schema."""
    page_type_ids = [pt.id for pt in pack.page_types]
    if not page_type_ids:
        return IngestPlan

    DynamicPagePlan: type[PagePlan] = create_model(  # type: ignore[call-overload]
        "PagePlanDynamic",
        __base__=PagePlan,
        page_type=(
            str,
            Field(..., json_schema_extra={"enum": page_type_ids}),  # type: ignore[dict-item]
        ),
    )

    DynamicPlan: type[IngestPlan] = create_model(  # type: ignore[call-overload]
        "IngestPlanDynamic",
        __base__=IngestPlan,
        source_page=(DynamicPagePlan, ...),
        derived_pages=(list[DynamicPagePlan], Field(default_factory=list)),  # type: ignore[valid-type]
    )
    return DynamicPlan


# --- batched classify+plan --------------------------------------------------


class ClassifyAndPlan(BaseModel):
    """Output combinato per la call batched."""

    model_config = ConfigDict(extra="forbid")

    classification: Classification
    plan: IngestPlan


def build_classify_and_plan_schema(pack: DomainPack) -> type[ClassifyAndPlan]:
    """Schema combinato pack-aware: enum applicati a classification.source_type
    e plan.derived_pages[*].page_type tramite i builder esistenti."""
    cls_schema = build_classification_schema(pack)
    plan_schema = build_plan_schema(pack)
    Combined: type[ClassifyAndPlan] = create_model(  # type: ignore[call-overload]
        "ClassifyAndPlanDynamic",
        __base__=ClassifyAndPlan,
        classification=(cls_schema, ...),
        plan=(plan_schema, ...),
    )
    return Combined

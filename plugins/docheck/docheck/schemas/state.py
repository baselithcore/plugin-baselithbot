from typing import TypedDict

from pydantic import BaseModel, ConfigDict

from .finding import Finding, ReasoningStep


class Chunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    page: int
    line_start: int
    line_end: int
    bbox: tuple[float, float, float, float]
    token_count: int


class StructureNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    label: str
    parent_id: str | None
    page: int
    line_start: int
    line_end: int
    chunk_ids: list[str]


class CheckState(TypedDict, total=False):
    doc_id: str
    lang: str
    chunks: list[Chunk]
    structure: list[StructureNode]
    selected_policies: list[str]
    findings: list[Finding]
    trace: list[ReasoningStep]
    errors: list[str]
    # ADR-0011: classification populated by ClassifierAgent before structurer.
    doc_type: str
    doc_type_confidence: float
    doc_type_low_confidence: bool
    doc_type_rationale: str

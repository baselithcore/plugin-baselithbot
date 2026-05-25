from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["FAIL", "WARN", "PASS", "INFO"]


class PolicyRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    policy_id: str
    version: str
    title: str
    excerpt: str = Field(..., min_length=1)


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    page: int
    line_start: int
    line_end: int
    bbox: tuple[float, float, float, float]
    text: str
    match_start: int | None = None
    match_end: int | None = None
    snippet: str | None = None


class ReasoningStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int
    agent: str
    action: str | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    thought: str | None = None


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Severity
    rule_id: str
    policy_ref: PolicyRef
    evidence: Citation
    explanation: str
    suggestion: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: list[ReasoningStep]


class DocMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    sha256: str
    lang: str
    pages: int


class AuditMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    user_email: str
    ts: str
    engine_version: str
    model: str
    embedding_model: str


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    doc: DocMeta
    policies_applied: list[str]
    score: int = Field(..., ge=0, le=100)
    summary: str
    by_severity: dict[Severity, int]
    findings: list[Finding]
    audit: AuditMeta
    signature: str

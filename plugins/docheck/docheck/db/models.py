from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """Mixin for multi-tenant scoped tables. `default` for single-tenant MVP."""

    tenant_id: Mapped[str] = mapped_column(String, nullable=False, default="default", server_default="default")


class User(Base, TenantMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    pw_hash: Mapped[str | None] = mapped_column(String)
    oidc_sub: Mapped[str | None] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id"), primary_key=True)


class Permission(Base):
    __tablename__ = "permissions"
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id"), primary_key=True)
    resource: Mapped[str] = mapped_column(String, primary_key=True)
    action: Mapped[str] = mapped_column(String, primary_key=True)


class Document(Base, TenantMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    pages: Mapped[int | None] = mapped_column(Integer)
    lang: Mapped[str | None] = mapped_column(String)
    storage_uri: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    purge_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="uploaded", nullable=False)
    # ADR-0011: classification populated by ClassifierAgent at parse time.
    doc_type: Mapped[str | None] = mapped_column(String)
    doc_type_confidence: Mapped[float | None] = mapped_column(Float)

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('uploaded','parsed','indexed','failed','purged')"),
        Index("idx_doc_status", "status"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    doc_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer)
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embed_ref: Mapped[str | None] = mapped_column(String)

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (Index("idx_chunk_doc", "doc_id", "ord"),)


class Policy(Base, TenantMixin):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    lang: Mapped[str] = mapped_column(String, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String)
    active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # ADR-0011: applicability matrix. JSON-encoded list of DocType values
    # (empty/null = applies to all). Frameworks (GDPR/ISO27001/NIS2/AIAct/...).
    applicable_doc_types: Mapped[str | None] = mapped_column(Text)
    frameworks: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (CheckConstraint("scope IN ('global_default','eu','world','custom')"),)


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    policy_id: Mapped[str] = mapped_column(String, nullable=False)
    policy_version: Mapped[str] = mapped_column(String, nullable=False)
    rule_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    matcher: Mapped[str | None] = mapped_column(Text)
    embed_ref: Mapped[str | None] = mapped_column(String)

    __table_args__ = (
        CheckConstraint("rule_type IN ('presence','absence','format','numeric_limit','semantic')"),
        CheckConstraint("severity IN ('fail','warn','info')"),
        Index("idx_rule_policy", "policy_id", "policy_version"),
    )


class Report(Base, TenantMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    doc_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    engine_version: Mapped[str] = mapped_column(String, nullable=False)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    policies_applied: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FindingRow(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    report_id: Mapped[str] = mapped_column(
        String, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String, ForeignKey("policy_rules.id"), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String, ForeignKey("document_chunks.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("severity IN ('FAIL','WARN','PASS','INFO')"),
        CheckConstraint("confidence >= 0 AND confidence <= 1"),
    )


class FindingDecision(Base, TenantMixin):
    """User-issued accept/reject for a finding, tied to a signed report.

    finding_id is the synthesizer-assigned id within the report payload (not the FindingRow PK,
    which may not exist when findings are persisted only in payload).
    """

    __tablename__ = "finding_decisions"

    report_id: Mapped[str] = mapped_column(String, ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True)
    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("decision IN ('accepted','rejected','muted')"),
        Index("idx_decision_report", "report_id"),
    )


class AuditLog(Base, TenantMixin):
    __tablename__ = "audit_log"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String, nullable=False, index=True)
    resource: Mapped[str | None] = mapped_column(String)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)
    payload_uri: Mapped[str | None] = mapped_column(String)
    prev_hash: Mapped[str] = mapped_column(String, nullable=False)
    entry_hash: Mapped[str] = mapped_column(String, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)


class VerdictCache(Base):
    __tablename__ = "verdict_cache"
    cache_key: Mapped[str] = mapped_column(String, primary_key=True)
    finding_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    text_hash: Mapped[str] = mapped_column(String, primary_key=True)
    model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vector_uri: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

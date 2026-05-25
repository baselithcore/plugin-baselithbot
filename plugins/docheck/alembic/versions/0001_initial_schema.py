"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("display_name", sa.String, nullable=False),
        sa.Column("pw_hash", sa.String, nullable=True),
        sa.Column("oidc_sub", sa.String, unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("disabled_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("label", sa.String, nullable=False),
    )
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role_id", sa.String, sa.ForeignKey("roles.id"), primary_key=True),
    )
    op.create_table(
        "permissions",
        sa.Column("role_id", sa.String, sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("resource", sa.String, primary_key=True),
        sa.Column("action", sa.String, primary_key=True),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("owner_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("mime_type", sa.String, nullable=False),
        sa.Column("sha256", sa.String, nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("pages", sa.Integer, nullable=True),
        sa.Column("lang", sa.String, nullable=True),
        sa.Column("storage_uri", sa.String, nullable=False),
        sa.Column("uploaded_at", sa.DateTime, nullable=False),
        sa.Column("purge_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="uploaded"),
        sa.CheckConstraint(
            "status IN ('uploaded','parsed','indexed','failed','purged')"
        ),
    )
    op.create_index("idx_doc_owner", "documents", ["owner_id"])
    op.create_index("idx_doc_sha", "documents", ["sha256"])
    op.create_index("idx_doc_status", "documents", ["status"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "doc_id",
            sa.String,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ord", sa.Integer, nullable=False),
        sa.Column("page", sa.Integer, nullable=True),
        sa.Column("line_start", sa.Integer, nullable=True),
        sa.Column("line_end", sa.Integer, nullable=True),
        sa.Column("bbox", sa.Text, nullable=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("embed_ref", sa.String, nullable=True),
    )
    op.create_index("idx_chunk_doc", "document_chunks", ["doc_id", "ord"])

    op.create_table(
        "policies",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("version", sa.String, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("scope", sa.String, nullable=False),
        sa.Column("lang", sa.String, nullable=False),
        sa.Column("source_uri", sa.String, nullable=True),
        sa.Column("active", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("scope IN ('global_default','eu','world','custom')"),
    )
    op.create_table(
        "policy_rules",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("policy_id", sa.String, nullable=False),
        sa.Column("policy_version", sa.String, nullable=False),
        sa.Column("rule_type", sa.String, nullable=False),
        sa.Column("severity", sa.String, nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("matcher", sa.Text, nullable=True),
        sa.Column("embed_ref", sa.String, nullable=True),
        sa.CheckConstraint(
            "rule_type IN ('presence','absence','format','numeric_limit','semantic')"
        ),
        sa.CheckConstraint("severity IN ('fail','warn','info')"),
    )
    op.create_index("idx_rule_policy", "policy_rules", ["policy_id", "policy_version"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("doc_id", sa.String, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("engine_version", sa.String, nullable=False),
        sa.Column("model_id", sa.String, nullable=False),
        sa.Column("embedding_model", sa.String, nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("policies_applied", sa.Text, nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("signature", sa.Text, nullable=False),
        sa.Column("signed_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_report_doc", "reports", ["doc_id"])
    op.create_index("idx_report_user", "reports", ["user_id"])

    op.create_table(
        "findings",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "report_id",
            sa.String,
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_id", sa.String, sa.ForeignKey("policy_rules.id"), nullable=False
        ),
        sa.Column(
            "chunk_id", sa.String, sa.ForeignKey("document_chunks.id"), nullable=False
        ),
        sa.Column("severity", sa.String, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("suggestion", sa.Text, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.CheckConstraint("severity IN ('FAIL','WARN','PASS','INFO')"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1"),
    )
    op.create_index("idx_finding_report", "findings", ["report_id"])

    op.create_table(
        "audit_log",
        sa.Column("seq", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime, nullable=False),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("resource", sa.String, nullable=True),
        sa.Column("payload_hash", sa.String, nullable=False),
        sa.Column("payload_uri", sa.String, nullable=True),
        sa.Column("prev_hash", sa.String, nullable=False),
        sa.Column("entry_hash", sa.String, nullable=False),
        sa.Column("signature", sa.Text, nullable=False),
    )
    op.create_index("idx_audit_ts", "audit_log", ["ts"])
    op.create_index("idx_audit_user", "audit_log", ["user_id"])

    op.execute(
        "CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log "
        "BEGIN SELECT RAISE(FAIL, 'audit_log is immutable'); END;"
    )
    op.execute(
        "CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log "
        "BEGIN SELECT RAISE(FAIL, 'audit_log is immutable'); END;"
    )

    op.create_table(
        "verdict_cache",
        sa.Column("cache_key", sa.String, primary_key=True),
        sa.Column("finding_json", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "embedding_cache",
        sa.Column("text_hash", sa.String, primary_key=True),
        sa.Column("model_id", sa.String, nullable=False),
        sa.Column("vector_uri", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.String, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # Seed roles + permissions
    op.execute(
        "INSERT INTO roles (id, label) VALUES "
        "('admin','Administrator'),"
        "('compliance_officer','Compliance Officer'),"
        "('dpo','Data Protection Officer'),"
        "('reader','Reader');"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_no_update;")
    op.execute("DROP TRIGGER IF EXISTS audit_no_delete;")
    for tbl in [
        "settings",
        "embedding_cache",
        "verdict_cache",
        "audit_log",
        "findings",
        "reports",
        "policy_rules",
        "policies",
        "document_chunks",
        "documents",
        "permissions",
        "user_roles",
        "roles",
        "users",
    ]:
        op.drop_table(tbl)

"""Baseline: feedback table with indexes and jsonb sources.

Revision ID: 001
Revises: None
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id BIGSERIAL PRIMARY KEY,
            query TEXT NOT NULL,
            answer TEXT NOT NULL,
            feedback TEXT CHECK (feedback IN ('positive','negative')) NOT NULL,
            conversation_id TEXT,
            sources JSONB,
            comment TEXT,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # Migra sources da TEXT a JSONB se la tabella esiste già con tipo TEXT
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'feedback'
                  AND column_name = 'sources'
                  AND data_type = 'text'
            ) THEN
                ALTER TABLE feedback
                ALTER COLUMN sources TYPE JSONB
                USING CASE
                    WHEN sources IS NOT NULL AND sources != '' THEN sources::jsonb
                    ELSE NULL
                END;
            END IF;
        END $$
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback (timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_conversation_id "
        "ON feedback (conversation_id) WHERE conversation_id IS NOT NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback (feedback)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_feedback_type")
    op.execute("DROP INDEX IF EXISTS idx_feedback_conversation_id")
    op.execute("DROP INDEX IF EXISTS idx_feedback_timestamp")
    op.execute("DROP TABLE IF EXISTS feedback")

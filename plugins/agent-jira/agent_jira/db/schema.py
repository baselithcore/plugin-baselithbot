from __future__ import annotations

from typing import Final

from psycopg import Cursor

from agent_jira.config import POSTGRES_ENABLED

from .connection import get_connection

_EXTRA_COLUMNS: Final[tuple[tuple[str, str], ...]] = (
    ("conversation_id", "TEXT"),
    ("sources", "TEXT"),
    ("comment", "TEXT"),
    ("tenant_id", "TEXT"),
)

_INDEXES: Final[tuple[tuple[str, str], ...]] = (
    (
        "idx_feedback_timestamp",
        "CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback (timestamp DESC)",
    ),
    (
        "idx_feedback_conversation_id",
        "CREATE INDEX IF NOT EXISTS idx_feedback_conversation_id ON feedback (conversation_id) WHERE conversation_id IS NOT NULL",
    ),
    (
        "idx_feedback_type",
        "CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback (feedback)",
    ),
    (
        "idx_feedback_tenant_id",
        "CREATE INDEX IF NOT EXISTS idx_feedback_tenant_id ON feedback (tenant_id) WHERE tenant_id IS NOT NULL",
    ),
)


def ensure_schema(cursor: Cursor[object]) -> None:
    """
    Garantisce che la tabella `feedback` esista con tutte le colonne richieste.
    Aggiorna inoltre lo schema aggiungendo eventuali colonne mancanti.
    """

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id BIGSERIAL PRIMARY KEY,
            query TEXT NOT NULL,
            answer TEXT NOT NULL,
            feedback TEXT CHECK (feedback IN ('positive','negative')) NOT NULL,
            conversation_id TEXT,
            sources TEXT,
            comment TEXT,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    for column_name, definition in _EXTRA_COLUMNS:
        cursor.execute(
            f"ALTER TABLE feedback ADD COLUMN IF NOT EXISTS {column_name} {definition}"
        )

    # Migra sources da TEXT a JSONB se necessario
    cursor.execute(
        """
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'feedback' AND column_name = 'sources'
        """
    )
    col_info = cursor.fetchone()
    if col_info and col_info[0] == "text":
        cursor.execute(
            """
            ALTER TABLE feedback
            ALTER COLUMN sources TYPE JSONB
            USING CASE
                WHEN sources IS NOT NULL AND sources != '' THEN sources::jsonb
                ELSE NULL
            END
            """
        )

    # Crea indici per le query di analytics
    for _index_name, index_ddl in _INDEXES:
        cursor.execute(index_ddl)


def _run_alembic_migrations() -> bool:
    """Tenta di eseguire le migrazioni Alembic. Ritorna True se riuscito."""

    import sys
    from pathlib import Path

    try:
        from alembic import command as alembic_command
        from alembic.config import Config as AlembicConfig

        project_root = Path(__file__).resolve().parents[2]
        ini_path = project_root / "alembic.ini"
        if not ini_path.exists():
            return False

        alembic_cfg = AlembicConfig(str(ini_path))
        alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
        alembic_command.upgrade(alembic_cfg, "head")
        print("[db] Migrazioni Alembic applicate con successo.", file=sys.stderr)
        return True
    except Exception as exc:
        print(
            f"[db] Alembic non disponibile, fallback a ensure_schema: {exc}",
            file=sys.stderr,
        )
        return False


def init_db() -> None:
    """
    Inizializza il database dei feedback assicurandosi che lo schema sia aggiornato.
    Prova prima Alembic, poi fallback a ensure_schema per compatibilità.

    Uses a PostgreSQL advisory lock to prevent multiple workers from running
    migrations concurrently at startup.
    """

    if not POSTGRES_ENABLED:
        return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Advisory lock prevents concurrent migration attempts from multiple workers.
            cursor.execute("SELECT pg_advisory_lock(42)")
            try:
                if not _run_alembic_migrations():
                    ensure_schema(cursor)
                    conn.commit()
            finally:
                cursor.execute("SELECT pg_advisory_unlock(42)")

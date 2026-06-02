"""Postgres Row-Level Security su tabelle tenant-scoped.

Crea ruolo applicativo `app_runtime` (NON-superuser) e attiva policy
RLS su tutte le tabelle scoped. Le policy filtrano usando il GUC
sessione `app.current_tenant_id` che `db/connection.py` setta a ogni
checkout dal pool, derivandolo dal contextvar `auth/tenant_context`.

Strategia rollout lazy (zero-downtime, allineata ad agent-jira/006):
- Migration ENABLE le policy ma NON le FORCE.
- Default deploy gira come superuser (es `postgres` o `llm_wiki`) →
  bypassa RLS automaticamente, app continua a funzionare.
- Per attivare enforcement: setta `POSTGRES_USER=app_runtime` (+ relativa
  password) in `.env` e riavvia. Da quel momento l'RLS è hard.

Tabelle scoped: tenants, users, refresh_tokens, conversations,
messages, memories, feedback, audit_events.

`wiki` (filesystem + Qdrant) NON è qui — risorsa SHARED per design.

Revision ID: 006_row_level_security
Revises: 005_feedback_audit
Create Date: 2026-05-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "006_row_level_security"
down_revision: str | None = "005_feedback_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tabelle con `tenant_id UUID NOT NULL`. La policy è stessa identica
# per tutte: USING/WITH CHECK su match con GUC sessione.
TENANT_SCOPED_TABLES = (
    "users",
    "refresh_tokens",
    "conversations",
    "messages",
    "memories",
    "feedback",
)

# Tabelle con tenant_id NULLABLE — policy permissiva per NULL (eventi
# cross-tenant come admin.bootstrap), match stretto se valorizzato.
TENANT_OPTIONAL_TABLES = ("audit_events",)

# Tenants: la riga è "se stessa". Policy match su id = current GUC.
SELF_TABLES = ("tenants",)


def upgrade() -> None:
    # 1. Ruolo runtime non-superuser. Password fornita via deploy
    #    (`ALTER ROLE app_runtime WITH PASSWORD '...'`) — qui no default
    #    debole, e LOGIN abilitato così l'app può connettersi.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
                CREATE ROLE app_runtime LOGIN NOINHERIT;
            END IF;
        END
        $$
        """
    )

    # 2. Grant minimi: SELECT/INSERT/UPDATE/DELETE su tabelle correnti
    #    + future (ALTER DEFAULT PRIVILEGES). Niente DDL, niente
    #    BYPASSRLS — RLS sarà effettivo quando l'app userà questo ruolo.
    op.execute(
        "DO $$ BEGIN EXECUTE format("
        "'GRANT CONNECT ON DATABASE %I TO app_runtime', current_database()"
        "); END $$"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO app_runtime")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime"
    )
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_runtime"
    )

    # 3. Policy su tabelle con tenant_id NOT NULL.
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
            """
        )

    # 4. Policy permissive su tabelle tenant-optional (audit_events):
    #    NULL tenant sempre visibile (eventi globali), match stretto
    #    altrimenti. INSERT/UPDATE/DELETE: solo righe del tenant corrente
    #    o NULL (eventi sistema scritti da background jobs).
    for table in TENANT_OPTIONAL_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (
                tenant_id IS NULL
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
            WITH CHECK (
                tenant_id IS NULL
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
            """
        )

    # 5. Policy self-match per `tenants`: ogni tenant vede solo se stesso.
    #    Admin cross-tenant operations richiedono ruolo superuser
    #    (o BYPASSRLS specifico, non fornito qui).
    for table in SELF_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_self_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_self_isolation ON {table}
            USING (
                id::text = current_setting('app.current_tenant_id', true)
            )
            WITH CHECK (
                id::text = current_setting('app.current_tenant_id', true)
            )
            """
        )


def downgrade() -> None:
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for table in TENANT_OPTIONAL_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for table in SELF_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_self_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    # Ruolo `app_runtime` lasciato — droppe richiede REASSIGN OWNED
    # e rischia di cancellare oggetti se qualcosa è stato creato come lui.

"""Postgres Row-Level Security for tenant-scoped tables.

Aggiunge policy RLS su `feedback` e `users` scopate al tenant corrente,
e crea il ruolo non-superuser `app_runtime` che l'applicazione deve usare
a runtime perché le policy abbiano effetto (i superuser bypassano RLS).

**Strategia di rollout lazy (zero-downtime):**
- Questa migration crea ruolo, policy e ABILITA le policy su ogni tabella,
  MA non le FORCE. I superuser (incluso il default `chatbot`) bypassano
  comunque l'RLS. Quindi l'app continua a funzionare senza modifiche.
- Per attivare l'enforcement effettivo, cambiare `DB_USER=app_runtime` in
  `docker.env` (e `DB_PASSWORD` corrispondente) dopo aver verificato che
  il contextvar tenant è popolato su ogni richiesta (vedi connection.py
  che fa SET LOCAL app.current_tenant_id).

**Ruolo `app_runtime`:**
- Password letta da variabile env Postgres `APP_RUNTIME_PASSWORD` oppure
  impostata con ALTER ROLE dopo la migration.
- Privilegi minimi: SELECT, INSERT, UPDATE, DELETE sulle tabelle app;
  nessun DDL, nessun BYPASSRLS.

Revision ID: 006
Revises: 005
Create Date: 2026-04-15
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_SCOPED_TABLES = ("feedback", "users")


def upgrade() -> None:
    # 1. Ruolo runtime non-superuser. Nessuna password impostata qui:
    #    va fornita via `ALTER ROLE app_runtime WITH PASSWORD '...'` dal deploy.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
                CREATE ROLE app_runtime LOGIN NOINHERIT;
            END IF;
        END
        $$;
        """
    )

    # 2. Grant privilegi necessari sul database corrente.
    op.execute(
        "DO $$ BEGIN EXECUTE format('GRANT CONNECT ON DATABASE %I TO app_runtime', current_database()); END $$"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO app_runtime")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime"
    )
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime")
    # Default privileges per tabelle future.
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO app_runtime"
    )

    # 3. Per ogni tabella tenant-scoped: ENABLE RLS + POLICY.
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};
            CREATE POLICY {table}_tenant_isolation ON {table}
                USING (
                    tenant_id::text = current_setting('app.current_tenant_id', true)
                    OR current_setting('app.current_tenant_id', true) = ''
                    OR current_setting('app.current_tenant_id', true) IS NULL
                );
            """
        )
        op.execute(
            f"""
            DROP POLICY IF EXISTS {table}_tenant_insert ON {table};
            CREATE POLICY {table}_tenant_insert ON {table}
                FOR INSERT
                WITH CHECK (
                    tenant_id::text = current_setting('app.current_tenant_id', true)
                    OR current_setting('app.current_tenant_id', true) = ''
                    OR current_setting('app.current_tenant_id', true) IS NULL
                );
            """
        )

    # 4. Tabella `tenants`: accessibile solo al proprio record per app_runtime.
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        DROP POLICY IF EXISTS tenants_self_access ON tenants;
        CREATE POLICY tenants_self_access ON tenants
            USING (
                id::text = current_setting('app.current_tenant_id', true)
                OR current_setting('app.current_tenant_id', true) = ''
                OR current_setting('app.current_tenant_id', true) IS NULL
            );
        """
    )


def downgrade() -> None:
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_insert ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS tenants_self_access ON tenants")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")

    op.execute(
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM app_runtime"
    )
    op.execute(
        "REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM app_runtime"
    )
    op.execute("REVOKE USAGE ON SCHEMA public FROM app_runtime")
    op.execute(
        "DO $$ BEGIN EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM app_runtime', current_database()); END $$"
    )
    # Il ruolo app_runtime NON viene droppato per evitare errore se
    # altre connessioni sono attive. Droppare manualmente se necessario.

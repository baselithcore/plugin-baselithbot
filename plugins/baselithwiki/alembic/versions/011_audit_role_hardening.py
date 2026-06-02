"""Revoke UPDATE/DELETE/TRUNCATE on audit_events from app_runtime.

Defense-in-depth oltre il trigger di mig 010. Il trigger blocca a livello
riga/transazione, ma `TRUNCATE` non passa per trigger di riga (passa per
trigger statement-level, che non abbiamo). Soluzione: revocare i privilegi
da app_runtime in modo che la query SQL stessa fallisca con
``permission_denied`` prima di toccare il trigger.

Risultato per ``app_runtime``:

- ``audit_events`` : SELECT, INSERT  (no UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER)
- ``prune_audit_events()`` : EXECUTE bloccato (non serve all'app)

Il job di pruning (``scripts/audit_retention.sh``) si connette come
ruolo proprietario (``llm_wiki`` superuser DB tipico) — separazione di
duty.

Revision ID: 011_audit_role_hardening
Revises: 010_audit_append_only
Create Date: 2026-05-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "011_audit_role_hardening"
down_revision: str | None = "010_audit_append_only"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Crea il ruolo se non esiste (mig 006 lo crea già; safety net qui
    # per ambienti dove l'ordine migrations è stato saltato manualmente).
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

    # Revoke ALL su audit_events, poi grant minimi.
    op.execute("REVOKE ALL ON audit_events FROM app_runtime")
    op.execute("GRANT SELECT, INSERT ON audit_events TO app_runtime")

    # Revoke EXECUTE su prune_audit_events — solo DBA / job dedicato lo
    # invoca con credenziali separate. app_runtime non deve poter
    # nemmeno provare il pruning.
    op.execute("REVOKE ALL ON FUNCTION prune_audit_events(INT) FROM app_runtime")
    op.execute("REVOKE ALL ON FUNCTION prune_audit_events(INT) FROM PUBLIC")


def downgrade() -> None:
    # Ripristina permessi base (allineato a mig 006).
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON audit_events TO app_runtime")
    op.execute("GRANT EXECUTE ON FUNCTION prune_audit_events(INT) TO app_runtime")

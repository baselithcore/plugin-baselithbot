"""Enforce audit_events append-only at DB level + retention helper.

Misura di hardening richiesta da molti standard di compliance
(ISO 27001 A.12.4 — audit log integrity, SOC2 CC7.2). Anche se il
codice applicativo già scrive solo INSERT su ``audit_events`` (vedi
``llm_wiki.auth.audit.write_event``), un attaccante con SQL access
diretto potrebbe altrimenti UPDATE/DELETE per coprire le tracce.

Strategia:

1. Trigger ``BEFORE UPDATE OR DELETE`` che solleva eccezione.
2. Stored function ``prune_audit_events(retention_days)`` con
   ``SECURITY DEFINER`` — unico canale legittimo per cancellare
   audit oltre la retention. Eseguita dal job di pruning
   (``scripts/audit_retention.sh``) che imposta una flag di
   sessione riconosciuta dal trigger.

Retention default: 730 giorni (2 anni). Valore consigliato per
GDPR + ISO 27001 A.18.1.3 (records retention). Override via env
``AUDIT_RETENTION_DAYS`` lato script di pruning.

Revision ID: 010_audit_append_only
Revises: 009_invitations_pwchange
Create Date: 2026-05-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "010_audit_append_only"
down_revision: str | None = "009_invitations_pwchange"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Trigger function: blocca UPDATE/DELETE salvo flag di sessione.
    # ``set_config('audit.allow_prune', 'true', true)`` viene impostato
    # solo dalla stored procedure ``prune_audit_events`` (SECURITY DEFINER).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_events_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Eccezione 1: prune controllato (vedi prune_audit_events).
            IF current_setting('audit.allow_prune', true) = 'true' THEN
                RETURN OLD;
            END IF;

            -- Eccezione 2: FK CASCADE SET NULL su user_id / tenant_id.
            -- Quando users / tenants sono cancellati (es. DSAR delete),
            -- le righe di audit_events sopravvivono anonimizzate. Solo
            -- queste 2 colonne possono passare da non-NULL a NULL; tutto
            -- il resto deve restare invariato.
            IF TG_OP = 'UPDATE' THEN
                IF (NEW.id = OLD.id
                    AND NEW.kind = OLD.kind
                    AND NEW.payload IS NOT DISTINCT FROM OLD.payload
                    AND NEW.ip_address IS NOT DISTINCT FROM OLD.ip_address
                    AND NEW.user_agent IS NOT DISTINCT FROM OLD.user_agent
                    AND NEW.created_at = OLD.created_at
                    AND ((NEW.user_id IS NULL AND OLD.user_id IS NOT NULL)
                         OR NEW.user_id IS NOT DISTINCT FROM OLD.user_id)
                    AND ((NEW.tenant_id IS NULL AND OLD.tenant_id IS NOT NULL)
                         OR NEW.tenant_id IS NOT DISTINCT FROM OLD.tenant_id))
                THEN
                    RETURN NEW;
                END IF;
            END IF;

            RAISE EXCEPTION 'audit_events is append-only (operation=%, table=%)',
                TG_OP, TG_TABLE_NAME
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events")
    op.execute(
        """
        CREATE TRIGGER audit_events_no_update
            BEFORE UPDATE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_delete
            BEFORE DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
        """
    )

    # Stored function di pruning. SECURITY DEFINER esegue con i diritti
    # del proprietario della funzione (postgres) bypassando il trigger
    # via set_config in transazione locale.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prune_audit_events(retention_days INT)
        RETURNS INT AS $$
        DECLARE
            removed INT;
        BEGIN
            IF retention_days IS NULL OR retention_days < 30 THEN
                RAISE EXCEPTION 'retention_days must be >= 30 (got %)', retention_days;
            END IF;
            PERFORM set_config('audit.allow_prune', 'true', true);
            DELETE FROM audit_events
                WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL;
            GET DIAGNOSTICS removed = ROW_COUNT;
            -- log the prune itself for accountability (chain of custody)
            INSERT INTO audit_events (kind, payload)
                VALUES ('audit.prune',
                        jsonb_build_object('removed', removed,
                                           'retention_days', retention_days));
            RETURN removed;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS prune_audit_events(INT)")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_append_only()")

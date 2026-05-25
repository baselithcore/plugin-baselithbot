"""Strict 1:1 user ↔ tenant invariant.

Ogni utente registrato possiede esattamente un tenant/workspace dedicato
e viceversa. Questa migration:

1. Valida che non esistano tenant con più utenti (in caso raise, il rollout
   blocca e va sanato manualmente prima di riprovare).
2. Forza `users.tenant_id` NOT NULL.
3. Ricrea la FK `users.tenant_id -> tenants(id)` con ON DELETE CASCADE
   (cancellazione tenant cancella l'utente proprietario).
4. Aggiunge UNIQUE su `users.tenant_id` per rendere 1:1 enforcement a DB.

Revision ID: 005
Revises: 004
Create Date: 2026-04-15
"""

from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard 1: non deve esistere alcun tenant con >1 utente.
    op.execute(
        """
        DO $$
        DECLARE violating_count INT;
        BEGIN
            SELECT COUNT(*) INTO violating_count FROM (
                SELECT tenant_id FROM users
                WHERE tenant_id IS NOT NULL
                GROUP BY tenant_id
                HAVING COUNT(*) > 1
            ) t;
            IF violating_count > 0 THEN
                RAISE EXCEPTION
                    'Migration 005 bloccata: % tenant con piu'' di un utente. '
                    'Il modello richiede 1:1 user<->tenant. '
                    'Risolvi manualmente riassegnando gli utenti in tenant dedicati '
                    'prima di ri-applicare la migration.',
                    violating_count;
            END IF;
        END
        $$;
        """
    )

    # Guard 2: non deve esistere alcun utente senza tenant.
    op.execute(
        """
        DO $$
        DECLARE orphan_count INT;
        BEGIN
            SELECT COUNT(*) INTO orphan_count FROM users WHERE tenant_id IS NULL;
            IF orphan_count > 0 THEN
                RAISE EXCEPTION
                    'Migration 005 bloccata: % utenti senza tenant. '
                    'Associa ogni utente ad un tenant dedicato prima di ri-applicare.',
                    orphan_count;
            END IF;
        END
        $$;
        """
    )

    # FK ricreata con ON DELETE CASCADE.
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_tenant_id_fkey")
    op.execute(
        """
        ALTER TABLE users
        ADD CONSTRAINT users_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        """
    )

    # NOT NULL (dopo i guard è safe).
    op.execute("ALTER TABLE users ALTER COLUMN tenant_id SET NOT NULL")

    # UNIQUE 1:1.
    op.execute(
        """
        ALTER TABLE users
        ADD CONSTRAINT users_tenant_id_unique UNIQUE (tenant_id)
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_tenant_id_unique")
    op.execute("ALTER TABLE users ALTER COLUMN tenant_id DROP NOT NULL")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_tenant_id_fkey")
    op.execute(
        """
        ALTER TABLE users
        ADD CONSTRAINT users_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        """
    )

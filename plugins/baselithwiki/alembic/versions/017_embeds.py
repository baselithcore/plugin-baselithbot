"""Embeddable chat widgets — tenant-scoped public chat tokens.

Tabella ``embeds`` + permesso ``admin.embed.manage``.

Model
-----

Ogni record rappresenta UN widget chat embeddabile su un sito terzo:

- ``token_hash`` (sha256 hex del plaintext) — lookup primario lato server
  pubblico. Plaintext mostrato UNA volta sola a creazione/rotazione.
- ``origin_allowlist`` — array di origin esatti (es. ``https://acme.com``).
  Il middleware CORS dinamico abbina ``Origin`` header del browser; tutto
  fuori allowlist → reject. Senza origin (es. cURL) → reject.
- ``theme`` (jsonb) — branding override per il widget (primary_color,
  position, welcome_message, font, dark mode hint). Sovrascrive
  ``/branding.json`` lato widget mini-app.
- ``rate_limit_per_minute`` — limite per ``(token, ip)`` indipendente
  dal rate-limit utente loggato.

RLS deliberatamente OFF
=======================

Lookup pubblico (``verify_token``) avviene PRIMA di qualunque tenant
context: il chiamante invia solo il token in body, l'app non ha modo di
sapere il tenant_id senza prima decodificare il token. Con RLS attiva il
SELECT ritornerebbe 0 righe (current_setting('app.current_tenant_id')
vuoto). Soluzione operativamente più semplice: RLS OFF, sicurezza
garantita da:

1. ``token_hash`` è sha256 di un secret 32 byte random → unguessable.
2. Endpoint admin (list/create/...) filtrano ``WHERE tenant_id = %s``
   esplicitamente dal JWT actor.
3. ``origin_allowlist`` blocca uso del token fuori dai siti autorizzati
   anche se il token leak.

Permesso ``admin.embed.manage`` seedato a ``superuser`` + ``admin``.
Separato da ``admin.tenant.manage`` per consentire profili admin più
stretti in futuro ("integration-admin" che gestisce solo embed).

Revision ID: 017_embeds
Revises: 016_conv_write_perm
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "017_embeds"
down_revision: str | None = "016_conv_write_perm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSION_SLUG = "admin.embed.manage"
PERMISSION_DESC = "Gestione widget chat embeddabili su siti terzi"
GRANT_TO_SLUGS = ("superuser", "admin")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS embeds (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL,
            token_prefix TEXT NOT NULL,
            origin_allowlist TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            theme JSONB NOT NULL DEFAULT '{}'::jsonb,
            welcome_message TEXT NOT NULL DEFAULT '',
            suggested_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
            rate_limit_per_minute INTEGER NOT NULL DEFAULT 30,
            is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            last_used_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_embeds_tenant_slug ON embeds (tenant_id, slug)"
    )
    # Lookup pubblico va via token_hash — indicizzato + UNIQUE per
    # difesa "stesso secret riusato due volte" (impossibile con secrets
    # 32 byte ma fail-fast comunque).
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_embeds_token_hash ON embeds (token_hash)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_embeds_tenant ON embeds (tenant_id)")

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_embeds_updated_at ON embeds;
        CREATE TRIGGER trg_embeds_updated_at
        BEFORE UPDATE ON embeds
        FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()
        """
    )

    # RLS OFF deliberata — vedi docstring modulo.

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO permissions (slug, description) VALUES (:slug, :desc) "
            "ON CONFLICT (slug) DO UPDATE SET description = EXCLUDED.description"
        ),
        {"slug": PERMISSION_SLUG, "desc": PERMISSION_DESC},
    )
    grant_stmt = sa.text(
        """
        INSERT INTO role_permissions (role_id, permission_slug)
        SELECT id, :perm FROM roles
        WHERE slug = :slug AND tenant_id IS NULL AND is_system = TRUE
        ON CONFLICT DO NOTHING
        """
    )
    for role_slug in GRANT_TO_SLUGS:
        bind.execute(grant_stmt, {"perm": PERMISSION_SLUG, "slug": role_slug})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM role_permissions WHERE permission_slug = :slug"),
        {"slug": PERMISSION_SLUG},
    )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE slug = :slug"),
        {"slug": PERMISSION_SLUG},
    )
    op.execute("DROP TRIGGER IF EXISTS trg_embeds_updated_at ON embeds")
    op.execute("DROP INDEX IF EXISTS idx_embeds_tenant")
    op.execute("DROP INDEX IF EXISTS uq_embeds_token_hash")
    op.execute("DROP INDEX IF EXISTS uq_embeds_tenant_slug")
    op.execute("DROP TABLE IF EXISTS embeds")

"""SSO provider + federated-identity persistence (OIDC / SAML)."""

import json
import uuid
from typing import Any, Dict, List, Optional

from psycopg.rows import dict_row

from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)


class SsoPersistenceMixin:
    """Identity providers and the local accounts linked to them."""

    # ---- Providers ---------------------------------------------------------

    def list_sso_providers(self, enabled_only: bool = False) -> List[dict]:
        """List configured SSO providers."""
        clause = "WHERE enabled = TRUE" if enabled_only else ""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT id, slug, name, protocol, enabled, config, default_roles,
                       auto_provision, created_at, updated_at,
                       (secret_enc IS NOT NULL) AS has_secret
                FROM auth_sso_providers {clause} ORDER BY name
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def get_sso_provider(self, slug: str) -> Optional[dict]:
        """Fetch a provider by slug, including its encrypted secret."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM auth_sso_providers WHERE slug = %s", (slug,))
            row = cur.fetchone()
            return dict(row) if row else None

    def upsert_sso_provider(
        self,
        slug: str,
        name: str,
        protocol: str,
        config: Dict[str, Any],
        secret_enc: Optional[str],
        default_roles: List[str],
        enabled: bool = True,
        auto_provision: bool = True,
    ) -> dict:
        """Create or update a provider (secret only overwritten when provided)."""
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO auth_sso_providers
                        (id, slug, name, protocol, enabled, config, secret_enc,
                         default_roles, auto_provision)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        protocol = EXCLUDED.protocol,
                        enabled = EXCLUDED.enabled,
                        config = EXCLUDED.config,
                        secret_enc = COALESCE(EXCLUDED.secret_enc, auth_sso_providers.secret_enc),
                        default_roles = EXCLUDED.default_roles,
                        auto_provision = EXCLUDED.auto_provision,
                        updated_at = NOW()
                    RETURNING id, slug, name, protocol, enabled, config,
                              default_roles, auto_provision
                    """,
                    (
                        str(uuid.uuid4()),
                        slug,
                        name,
                        protocol,
                        enabled,
                        json.dumps(config),
                        secret_enc,
                        default_roles,
                        auto_provision,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row)

    def delete_sso_provider(self, slug: str) -> bool:
        """Delete a provider and its linked identities."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM auth_sso_providers WHERE slug = %s", (slug,))
                ok = cur.rowcount > 0
            conn.commit()
        return ok

    # ---- Identities --------------------------------------------------------

    def get_sso_identity(self, provider_id: str, subject: str) -> Optional[dict]:
        """Look up a linked identity by (provider, subject)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM auth_sso_identities "
                "WHERE provider_id = %s AND subject = %s",
                (provider_id, subject),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def link_sso_identity(
        self,
        provider_id: str,
        user_id: str,
        subject: str,
        email: Optional[str],
    ) -> None:
        """Create or refresh the link between an IdP subject and a local user."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_sso_identities
                        (id, provider_id, user_id, subject, email, last_login)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (provider_id, subject) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        email = EXCLUDED.email,
                        last_login = NOW()
                    """,
                    (str(uuid.uuid4()), provider_id, user_id, subject, email),
                )
            conn.commit()

    def list_user_sso_identities(self, user_id: str) -> List[dict]:
        """List federated identities linked to a user (for My Account)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT i.id, i.subject, i.email, i.last_login,
                       p.slug AS provider_slug, p.name AS provider_name
                FROM auth_sso_identities i
                JOIN auth_sso_providers p ON p.id = i.provider_id
                WHERE i.user_id = %s ORDER BY i.last_login DESC
                """,
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]

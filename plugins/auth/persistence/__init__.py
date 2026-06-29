"""
Auth Plugin Persistence Layer.

PostgreSQL storage for users, tokens, and MFA backup codes.
Uses the core connection pool. The public ``AuthPersistence`` API is composed
from cohesive mixins kept in sibling modules to honour the 500 LOC cap.
"""

from pathlib import Path
from typing import Optional

from core.db.connection import get_connection
from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.persistence._apikeys import ApiKeyPersistenceMixin
from plugins.auth.persistence._cost_governance import CostGovernanceMixin
from plugins.auth.persistence._history import HistoryPersistenceMixin
from plugins.auth.persistence._plugin_tenancy import PluginTenancyOverrideMixin
from plugins.auth.persistence._recovery import RecoveryPersistenceMixin
from plugins.auth.persistence._security_policy import SecurityPolicyMixin
from plugins.auth.persistence._sso import SsoPersistenceMixin
from plugins.auth.persistence._tenancy import TenancyPersistenceMixin
from plugins.auth.persistence._tokens import TokenPersistenceMixin
from plugins.auth.persistence._users import UserPersistenceMixin
from plugins.auth.persistence._webauthn import WebAuthnPersistenceMixin

logger = get_logger(__name__)


class AuthPersistence(
    UserPersistenceMixin,
    TokenPersistenceMixin,
    RecoveryPersistenceMixin,
    HistoryPersistenceMixin,
    WebAuthnPersistenceMixin,
    ApiKeyPersistenceMixin,
    SsoPersistenceMixin,
    SecurityPolicyMixin,
    CostGovernanceMixin,
    TenancyPersistenceMixin,
    PluginTenancyOverrideMixin,
):
    """PostgreSQL persistence for authentication data."""

    def __init__(self) -> None:
        self._schema_path = Path(__file__).parent.parent / "schema.sql"
        self._config = ServiceRegistry.get(AuthConfig)

    def create_tables(self) -> None:
        """Create auth tables if they don't exist."""
        if not self._schema_path.exists():
            logger.error(f"Schema file not found: {self._schema_path}")
            return

        schema_sql = self._schema_path.read_text()

        with get_connection() as conn:
            with conn.cursor() as cur:
                # Serialize concurrent initializers. Multiple uvicorn workers call
                # create_tables() at boot; running the same DDL at once deadlocks on
                # Postgres catalog locks (e.g. pg_proc for the CREATE FUNCTIONs).
                # get_connection() is autocommit, so a *session*-level advisory lock is
                # required (a txn-level one would release immediately). One worker runs
                # the schema while the rest wait, then re-run it idempotently.
                lock_key = 0x41757468  # "Auth"
                cur.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
                try:
                    cur.execute(schema_sql)  # nosec B608 - trusted schema file
                finally:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
            conn.commit()
            logger.info("Auth database tables created/verified")


# Global instance
_persistence: Optional[AuthPersistence] = None


def get_auth_persistence() -> AuthPersistence:
    """Get or create the global auth persistence instance."""
    global _persistence
    if _persistence is None:
        _persistence = AuthPersistence()
    return _persistence


__all__ = ["AuthPersistence", "get_auth_persistence"]

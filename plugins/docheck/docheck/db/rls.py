"""Postgres RLS session GUC binding. Sets `app.current_tenant` per request.

SQLAlchemy event listener: on each checkout, execute SET LOCAL using
`current_tenant()` ContextVar. SQLite no-op.
"""

from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection

from ..core.config import settings
from ..core.tenant import current_tenant
from .session import engine


def install_rls_hook() -> None:
    if settings.db_backend != "postgres":
        return

    @event.listens_for(engine.sync_engine, "checkout")
    def _set_tenant_guc(dbapi_connection: Any, _conn_record: Any, _conn_proxy: Any) -> None:
        tenant = current_tenant()
        cur = dbapi_connection.cursor()
        try:
            cur.execute("SET app.current_tenant = %s", (tenant,))
        finally:
            cur.close()


def set_tenant_on_session_sync(sync_conn: Connection, tenant: str) -> None:
    """Used in tests / scripts where checkout hook isn't active."""
    sync_conn.execute(text("SET app.current_tenant = :t"), {"t": tenant})

from __future__ import annotations

import random
import time
from contextlib import contextmanager
from typing import Iterator, Optional

from psycopg import Connection, Cursor
from psycopg.rows import RowFactory
from psycopg_pool import ConnectionPool

from agent_jira.config import (
    APP_TIMEZONE_NAME,
    DB_CONNINFO,
    DB_POOL_MAX_SIZE,
    DB_POOL_MIN_SIZE,
    DB_POOL_TIMEOUT,
    POSTGRES_ENABLED,
)

_POOL: Optional[ConnectionPool] = None
if POSTGRES_ENABLED:
    _POOL = ConnectionPool(
        conninfo=DB_CONNINFO,
        min_size=DB_POOL_MIN_SIZE,
        max_size=DB_POOL_MAX_SIZE,
        timeout=DB_POOL_TIMEOUT,
    )


@contextmanager
def get_connection() -> Iterator[Connection[object]]:
    """
    Restituisce una connessione al database PostgreSQL dal connection pool condiviso.

    Imposta SESSION-local GUC `app.current_tenant_id` in base al contextvar tenant,
    così le policy RLS della migration 006 possono filtrare per tenant. Il GUC è
    resettato al `putconn` per evitare cross-contamination tra richieste sullo
    stesso connection slot.

    Retry con backoff solo per errori di connessione, non per errori SQL del chiamante.
    """

    if not POSTGRES_ENABLED or _POOL is None:
        raise RuntimeError("PostgreSQL è disabilitato (POSTGRES_ENABLED=false).")

    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            conn = _POOL.getconn(timeout=DB_POOL_TIMEOUT)
            break
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(0.1 * (2**attempt) + random.random() * 0.05)
                continue
            raise
    else:
        if last_exc:
            raise last_exc

    tenant_id: Optional[str] = None
    try:
        # Import locale per evitare cicli (tenant_context non dipende da connection).
        from agent_jira.tenant_context import get_current_tenant_id

        tenant_id = get_current_tenant_id()
    except Exception:
        tenant_id = None

    try:
        if getattr(conn, "_app_timezone", None) != APP_TIMEZONE_NAME:
            with conn.cursor() as _cursor:
                _cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            setattr(conn, "_app_timezone", APP_TIMEZONE_NAME)

        # SESSION GUC per RLS: la policy usa current_setting('app.current_tenant_id').
        # Usiamo SET (non SET LOCAL) perché il chiamante può usare la stessa
        # connessione su più transazioni (autocommit, rollback esplicito, ecc.).
        # Il reset a stringa vuota sul putconn evita leak cross-request.
        with conn.cursor() as _cursor:
            _cursor.execute(
                "SELECT set_config('app.current_tenant_id', %s, false)",
                (tenant_id or "",),
            )

        yield conn
    finally:
        # Reset del GUC prima di rimettere la connessione nel pool per evitare
        # che una request successiva erediti il tenant_id della precedente.
        try:
            with conn.cursor() as _cursor:
                _cursor.execute("SELECT set_config('app.current_tenant_id', '', false)")
        except Exception:
            pass
        _POOL.putconn(conn)


@contextmanager
def get_cursor(
    *,
    row_factory: Optional[RowFactory] = None,
) -> Iterator[Cursor[object]]:
    """
    Restituisce un cursore pronto all'uso, opzionalmente configurato con una row factory.
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=row_factory) as cursor:
            yield cursor


def close_pool() -> None:
    """Chiude esplicitamente il connection pool (utile in fase di shutdown dei worker)."""

    if _POOL is not None:
        _POOL.close()

"""Postgres connection pool (psycopg3) + RLS GUC wiring.

Pattern portato da ``agent-jira/app/db/connection.py``, adattato al
config layout di llm-wiki (modulo ``llm_wiki.config``, contextvar in
``llm_wiki.auth.tenant_context``).

Comportamento chiave
====================

Ogni :func:`get_connection` esegue, prima di passare la connessione al
chiamante:

1. ``SET TIME ZONE 'UTC'`` (una volta per slot di pool).
2. ``SELECT set_config('app.current_tenant_id', <uuid|''>, false)`` —
   GUC sessione che le policy RLS della migration 006 leggono via
   ``current_setting('app.current_tenant_id')``. Niente ``WHERE
   tenant_id = ...`` nei moduli CRUD: il filtro è applicato dal DB.

Al ``putconn`` resetta il GUC a stringa vuota, così la prossima request
che pesca lo stesso slot non eredita il tenant precedente — fix per
cross-request leak su connection reuse.

Niente async: psycopg3 sync è il default di stack llm-wiki (RAGAgent,
embedder, qdrant client già sync). FastAPI esegue handler sync nel
threadpool — nessun problema di concurrency con pool dedicato.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from llm_wiki import config
from llm_wiki.db.url import resolve_database_url

logger = logging.getLogger(__name__)


_POOL = None  # type: ignore[var-annotated]


def _build_pool():  # noqa: ANN202 — psycopg_pool import lazy
    """Costruisce il pool. Import psycopg lazy: l'app deve poter
    avviarsi anche senza psycopg installato (modalità setup/no-DB)."""
    try:
        from psycopg_pool import ConnectionPool
    except ImportError as exc:  # pragma: no cover — manca dep
        raise RuntimeError(
            "psycopg[binary,pool] non installato. "
            'Esegui `pip install -e ".[auth]"` (o aggiungi psycopg manualmente).'
        ) from exc

    conninfo = resolve_database_url()
    pool = ConnectionPool(
        conninfo=conninfo,
        min_size=config.DB_POOL_MIN_SIZE,
        max_size=config.DB_POOL_MAX_SIZE,
        timeout=config.DB_POOL_TIMEOUT,
        # `open=False` posticipa l'apertura: evita di bloccare l'import
        # se Postgres non è ancora up. Il primo `getconn()` apre.
        open=False,
    )
    return pool


def _get_or_create_pool():  # noqa: ANN202
    global _POOL
    if not config.POSTGRES_ENABLED:
        raise RuntimeError(
            "Postgres disabilitato (POSTGRES_ENABLED=false e nessun "
            "DATABASE_URL/POSTGRES_HOST in env)."
        )
    if _POOL is None:
        _POOL = _build_pool()
        try:
            _POOL.open(wait=False)
        except Exception as exc:
            logger.warning("[db] pool.open ha fallito (riprovo on-demand): %s", exc)
    return _POOL


@contextmanager
def get_connection() -> Iterator[Any]:
    """Restituisce una connessione psycopg3 dal pool con GUC tenant
    impostato. Retry con backoff sui soli errori di acquisizione del
    pool (non sugli errori SQL del chiamante — quelli rilanciano).
    """
    pool = _get_or_create_pool()

    last_exc: Exception | None = None
    conn = None
    for attempt in range(3):
        try:
            conn = pool.getconn(timeout=config.DB_POOL_TIMEOUT)
            break
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(0.1 * (2**attempt) + random.random() * 0.05)
                continue
            raise
    if conn is None:
        raise last_exc or RuntimeError("impossibile ottenere connessione dal pool")

    # Lazy import del contextvar: rompe il ciclo db ↔ auth.
    try:
        from llm_wiki.auth.tenant_context import get_current_tenant_id

        tenant_id = get_current_tenant_id()
    except Exception:
        tenant_id = None

    try:
        # Timezone una volta per slot — `_app_timezone` attribute marker.
        if getattr(conn, "_app_timezone", None) != config.APP_TIMEZONE_NAME:
            with conn.cursor() as _cur:
                _cur.execute(f"SET TIME ZONE '{config.APP_TIMEZONE_NAME}'")
            conn._app_timezone = config.APP_TIMEZONE_NAME

        # GUC sessione (non SET LOCAL) per sopravvivere a transazioni
        # multiple sulla stessa connection. Reset al putconn evita leak.
        with conn.cursor() as _cur:
            _cur.execute(
                "SELECT set_config('app.current_tenant_id', %s, false)",
                (tenant_id or "",),
            )

        yield conn
    finally:
        try:
            with conn.cursor() as _cur:
                _cur.execute("SELECT set_config('app.current_tenant_id', '', false)")
            # Il SELECT sopra apre una transazione implicita — chiudila
            # prima del putconn, altrimenti il pool logga
            # "rolling back returned connection [INTRANS]" ad ogni checkin.
            conn.rollback()
        except Exception:
            # Connessione probabilmente broken — il pool la scarterà.
            pass
        try:
            pool.putconn(conn)
        except Exception as exc:  # pragma: no cover
            logger.warning("[db] putconn fallito: %s", exc)


@contextmanager
def get_cursor(*, row_factory=None) -> Iterator[Any]:  # noqa: ANN001
    """Shortcut: ``with get_cursor() as cur:``. ``row_factory`` opzionale
    (es. ``psycopg.rows.dict_row`` per dict invece che tuple)."""
    with get_connection() as conn:
        if row_factory is not None:
            with conn.cursor(row_factory=row_factory) as cur:
                yield cur
        else:
            with conn.cursor() as cur:
                yield cur


def close_pool() -> None:
    """Chiude il pool (chiamato da lifespan shutdown)."""
    global _POOL
    if _POOL is not None:
        try:
            _POOL.close()
        except Exception as exc:  # pragma: no cover
            logger.warning("[db] close_pool error: %s", exc)
        _POOL = None


def health_check() -> bool:
    """``SELECT 1`` veloce per smoke test (status endpoint, lifespan)."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception as exc:
        logger.warning("[db] health_check failed: %s", exc)
        return False


__all__ = ["get_connection", "get_cursor", "close_pool", "health_check"]

"""Durable, multi-worker-safe persistence for the per-plugin LLM cost ledger.

The in-memory :class:`.llm_cost.LlmCostLedger` is the hot-path write buffer — LLM
attribution never touches the database. This module folds that buffer's *deltas*
into a Postgres table on a timer via an **additive UPSERT**, so several uvicorn
workers (each with its own in-memory ledger) sum into one correct total instead
of clobbering one another. Reads come from the table — the cross-worker source of
truth — so the dashboard's figures are cumulative and survive restarts.

Money is stored as integer **micro-USD** (1 USD = 1_000_000) so sub-cent LLM
calls accumulate exactly. Everything degrades to the pure in-memory ledger when
no database is configured: the dashboard still works, it just resets on restart.

No core source is modified and no migration is required — the table is created
lazily with ``CREATE TABLE IF NOT EXISTS`` on first use (opt-in, in-memory by
default), mirroring the lightweight-persistence pattern used by other plugins.
"""

from __future__ import annotations

import atexit
import threading
from typing import Any

from core.observability.logging import get_logger

logger = get_logger(__name__)

_TABLE = "baselithcontrol_llm_usage"

_DDL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    tenant VARCHAR(200) NOT NULL,
    plugin VARCHAR(200) NOT NULL,
    model VARCHAR(200) NOT NULL,
    prompt_tokens BIGINT NOT NULL DEFAULT 0,
    completion_tokens BIGINT NOT NULL DEFAULT 0,
    cost_micros BIGINT NOT NULL DEFAULT 0,
    calls BIGINT NOT NULL DEFAULT 0,
    first_active TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant, plugin, model)
)
"""

_UPSERT = f"""
INSERT INTO {_TABLE} AS u
    (tenant, plugin, model, prompt_tokens, completion_tokens, cost_micros, calls, last_active)
VALUES (%(tenant)s, %(plugin)s, %(model)s, %(pt)s, %(ct)s, %(cm)s, %(calls)s, NOW())
ON CONFLICT (tenant, plugin, model) DO UPDATE SET
    prompt_tokens = u.prompt_tokens + EXCLUDED.prompt_tokens,
    completion_tokens = u.completion_tokens + EXCLUDED.completion_tokens,
    cost_micros = u.cost_micros + EXCLUDED.cost_micros,
    calls = u.calls + EXCLUDED.calls,
    last_active = NOW()
"""

_MICROS = 1_000_000


class CostStore:
    """Postgres-backed durable totals for the per-plugin LLM cost ledger."""

    def __init__(self) -> None:
        self._available: bool | None = None  # tri-state until first probe
        self._probe_lock = threading.Lock()
        self._flusher: threading.Thread | None = None
        self._stop = threading.Event()
        self._interval = 15.0

    # -- availability / schema -------------------------------------------
    def _ensure_schema(self) -> bool:
        """Probe the DB once and create the table; cache the verdict."""
        if self._available is not None:
            return self._available
        with self._probe_lock:
            if self._available is not None:
                return self._available
            try:
                from core.db.connection import get_cursor

                with get_cursor() as cur:
                    cur.execute(_DDL)
                self._available = True
                logger.info("BaselithControl cost persistence enabled (%s)", _TABLE)
            except Exception as exc:  # noqa: BLE001 — no DB → degrade to memory
                self._available = False
                logger.info("BaselithControl cost persistence off (no DB): %s", exc)
            return self._available

    def available(self) -> bool:
        """Whether durable persistence is usable (DB reachable + table ready)."""
        return self._ensure_schema()

    # -- write (sync; called from the flusher thread / the route's pre-read) --
    def flush(self, deltas: list[dict[str, Any]]) -> None:
        """Fold a batch of usage deltas into the durable totals (additive)."""
        if not deltas or not self._ensure_schema():
            return
        params = [
            {
                "tenant": d["tenant"],
                "plugin": d["plugin"],
                "model": d["model"],
                "pt": int(d["prompt_tokens"]),
                "ct": int(d["completion_tokens"]),
                "cm": int(round(float(d["cost_usd"]) * _MICROS)),
                "calls": int(d["calls"]),
            }
            for d in deltas
        ]
        try:
            from core.db.connection import get_cursor

            with get_cursor() as cur:
                cur.executemany(_UPSERT, params)
        except Exception as exc:  # noqa: BLE001 — never lose the app over a flush
            logger.warning("BaselithControl cost flush failed: %s", exc)

    # -- read (async; called from the /cost/usage route) -----------------
    async def read(self, tenant: str | None) -> tuple[float, list[dict[str, Any]]]:
        """Aggregate durable usage by ``(plugin, model)``, scoped to ``tenant``.

        ``tenant=None`` sums across every tenant (the admin/global view). Returns
        ``(since_epoch, rows)`` with the same row shape the in-memory snapshot
        produces, so the route handles both sources identically.
        """
        from psycopg.rows import dict_row

        from core.db.connection import get_async_cursor

        where = "" if tenant is None else "WHERE tenant = %(tenant)s"
        sql = f"""
            SELECT plugin, model,
                   SUM(prompt_tokens) AS prompt_tokens,
                   SUM(completion_tokens) AS completion_tokens,
                   SUM(cost_micros) AS cost_micros,
                   SUM(calls) AS calls,
                   MAX(EXTRACT(EPOCH FROM last_active)) AS last_active,
                   MIN(EXTRACT(EPOCH FROM first_active)) AS first_active
            FROM {_TABLE} {where}
            GROUP BY plugin, model
        """
        params = {} if tenant is None else {"tenant": tenant}
        async with get_async_cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, params)
            raw = await cur.fetchall()

        rows: list[dict[str, Any]] = []
        firsts: list[float] = []
        for r in raw:
            if r["first_active"]:
                firsts.append(float(r["first_active"]))
            rows.append(
                {
                    "plugin": r["plugin"],
                    "model": r["model"],
                    "prompt_tokens": int(r["prompt_tokens"] or 0),
                    "completion_tokens": int(r["completion_tokens"] or 0),
                    "cost_usd": (int(r["cost_micros"] or 0)) / _MICROS,
                    "calls": int(r["calls"] or 0),
                    "last_active": float(r["last_active"] or 0.0),
                }
            )
        return (min(firsts) if firsts else 0.0), rows

    # -- background flusher ----------------------------------------------
    def start(self, interval: float = 15.0) -> None:
        """Start the periodic delta flusher (idempotent; no-op without a DB)."""
        if self._flusher is not None:
            return
        self._interval = max(2.0, interval)
        if not self._ensure_schema():
            return  # no DB → nothing to flush; route falls back to memory
        thread = threading.Thread(target=self._loop, name="blc-cost-flush", daemon=True)
        self._flusher = thread
        thread.start()
        atexit.register(self._final_flush)
        logger.info(
            "BaselithControl cost flusher started (every %.0fs)", self._interval
        )

    def _loop(self) -> None:
        from .llm_cost import get_llm_ledger

        while not self._stop.wait(self._interval):
            try:
                self.flush(get_llm_ledger().drain_deltas())
            except Exception as exc:  # noqa: BLE001 — keep the loop alive
                logger.warning("BaselithControl cost flush loop error: %s", exc)

    def _final_flush(self) -> None:
        """Drain once more at process exit so the last interval isn't lost."""
        self._stop.set()
        try:
            from .llm_cost import get_llm_ledger

            self.flush(get_llm_ledger().drain_deltas())
        except Exception:  # noqa: BLE001 — best-effort on shutdown
            pass


_STORE: CostStore | None = None
_STORE_LOCK = threading.Lock()


def get_cost_store() -> CostStore:
    """Return the process-wide singleton cost store (built on first use)."""
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:
                _STORE = CostStore()
    return _STORE


__all__ = ["CostStore", "get_cost_store"]

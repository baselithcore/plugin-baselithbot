"""Infrastructure monitoring + governed destructive ops, projected from the CLI.

* ``db status`` reuses the CLI's connectivity checks.
* ``cache stats``/``cache clear``/``db reset`` reuse the CLI's own
  ``run_cache``/``run_db`` (JSON mode) verbatim via stdout capture — the
  destructive Redis/Qdrant logic lives in exactly one place.
* ``queue status`` is read natively over Redis + RQ (the CLI command renders to a
  terminal only and exposes no JSON path).
"""

from __future__ import annotations

import asyncio
from typing import Any

from ...cli_models import (
    ActionOutcome,
    CacheStats,
    DbStatus,
    DbStore,
    QueueStatus,
    QueueWorker,
)
from .capture import run_capturing_json


def _db_status_sync() -> DbStatus:
    from core.cli.commands.doctor import (
        check_graph_db,
        check_postgres,
        check_qdrant,
        check_redis,
    )

    raw = [check_redis(), check_qdrant(), check_postgres(), check_graph_db()]
    stores = [
        DbStore(database=c.name, online=c.passed, message=c.message, details=c.details)
        for c in raw
    ]
    return DbStatus(stores=stores)


def _cache_stats_sync() -> CacheStats:
    from core.cli.commands.cache import run_cache

    payload = run_capturing_json(lambda: run_cache("stats", json_output=True))
    if payload.get("status") != "ok":
        return CacheStats(ok=False, error=str(payload.get("message", "unknown error")))
    return CacheStats(
        ok=True,
        total_keys=_as_int(payload.get("total_keys")),
        used_memory_human=_as_str(payload.get("used_memory_human")),
        peak_memory_human=_as_str(payload.get("peak_memory_human")),
        fragmentation_ratio=_as_str(payload.get("fragmentation_ratio")),
    )


def _cache_clear_sync() -> ActionOutcome:
    from core.cli.commands.cache import run_cache

    payload = run_capturing_json(lambda: run_cache("clear", json_output=True))
    ok = payload.get("status") == "ok"
    return ActionOutcome(ok=ok, message=str(payload.get("message", "")))


def _db_reset_sync() -> ActionOutcome:
    from core.cli.commands.db import run_db

    payload = run_capturing_json(lambda: run_db("reset", json_output=True))
    ok = payload.get("status") == "ok"
    return ActionOutcome(ok=ok, message=str(payload.get("message", "")))


def _queue_status_sync() -> QueueStatus:
    try:
        from core.config import get_storage_config
        from redis import Redis
        from rq import Queue, Worker
        from rq.registry import (
            FailedJobRegistry,
            FinishedJobRegistry,
            StartedJobRegistry,
        )
    except ImportError as exc:
        return QueueStatus(available=False, error=f"RQ/Redis not installed: {exc}")

    try:
        config = get_storage_config()
        conn = Redis.from_url(config.queue_redis_url)
        queue = Queue("default", connection=conn)
        workers = Worker.all(connection=conn)
        return QueueStatus(
            available=True,
            workers=len(workers),
            pending=len(queue),
            running=StartedJobRegistry("default", connection=conn).count,
            completed=FinishedJobRegistry("default", connection=conn).count,
            failed=FailedJobRegistry("default", connection=conn).count,
            worker_details=[
                QueueWorker(name=w.name, state=str(w.state)) for w in workers
            ],
        )
    except Exception as exc:  # noqa: BLE001 — surfaced as unavailable
        return QueueStatus(available=False, error=str(exc))


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    return None if value is None else str(value)


async def db_status() -> DbStatus:
    """Connectivity of every persistent datastore (off-thread)."""
    return await asyncio.to_thread(_db_status_sync)


async def cache_stats() -> CacheStats:
    """Redis cache memory snapshot (off-thread)."""
    return await asyncio.to_thread(_cache_stats_sync)


async def cache_clear() -> ActionOutcome:
    """Flush the Redis cache DB (off-thread, governed by the route)."""
    return await asyncio.to_thread(_cache_clear_sync)


async def db_reset() -> ActionOutcome:
    """Wipe vector stores + cache (off-thread, governed by the route)."""
    return await asyncio.to_thread(_db_reset_sync)


async def queue_status() -> QueueStatus:
    """RQ task-queue snapshot (off-thread)."""
    return await asyncio.to_thread(_queue_status_sync)


__all__ = [
    "db_status",
    "cache_stats",
    "cache_clear",
    "db_reset",
    "queue_status",
]

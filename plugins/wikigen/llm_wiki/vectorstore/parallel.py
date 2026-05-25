"""Helper di parallelismo per il pipeline di retrieval.

In modalità server/gRPC il client Qdrant è thread-safe → possiamo fan-out
le N varianti di query e gli scroll di espansione su un ``ThreadPoolExecutor``
condiviso, riducendo la latenza wall-clock da O(N · RTT) a O(RTT) sotto i
limiti del pool.

In modalità ``QDRANT_MODE=embedded`` il client è file-backed (sqlite
underlying) e NON è thread-safe per richieste concorrenti — auto-fallback
all'esecuzione serial indipendentemente dall'env ``RETRIEVAL_PARALLEL_ENABLED``.

Il pool è singleton process-wide. Workers daemonizzati, idle keepalive
breve, evitano accumulo durante long-running serve.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from llm_wiki.config import (
    QDRANT_MODE,
    RETRIEVAL_PARALLEL_ENABLED,
    RETRIEVAL_PARALLEL_MAX_WORKERS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is not None:
        return _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=RETRIEVAL_PARALLEL_MAX_WORKERS,
                thread_name_prefix="retrieval",
            )
    return _executor


def is_parallel_safe() -> bool:
    """True se possiamo fan-out su Qdrant (server mode + flag ON)."""
    return RETRIEVAL_PARALLEL_ENABLED and QDRANT_MODE != "embedded"


def parallel_map(fn: Callable[[T], R], items: Iterable[T]) -> list[R]:
    """Mappa ``fn`` su ``items`` in parallelo su pool condiviso.

    Garanzie:
    - Ordine preservato (output[i] = fn(items[i])).
    - Fallback serial quando ``is_parallel_safe()`` è False oppure
      ``len(items) <= 1``.
    - Eccezioni propagate dal primo task fallito (futures.result() rilancia).
      Caller responsabile di wrap try/except se serve fallback-safe.
    """
    materialized = list(items)
    if len(materialized) <= 1 or not is_parallel_safe():
        return [fn(x) for x in materialized]

    pool = _get_executor()
    futures = [pool.submit(fn, x) for x in materialized]
    return [f.result() for f in futures]


def shutdown_executor() -> None:
    """Tear-down (chiamato in lifespan shutdown opzionale)."""
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=False, cancel_futures=True)
            _executor = None


__all__ = [
    "is_parallel_safe",
    "parallel_map",
    "shutdown_executor",
]

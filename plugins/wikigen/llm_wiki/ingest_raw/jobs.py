"""Registry job per ingest raw via HTTP.

In-process, thread-safe. Persistenza append-only JSONL per sopravvivere a restart
(solo metadata, niente event log — quello resta in `log.md` via orchestrator).

Flusso:
- `create_job(filename)` → `Job` (`queued`).
- `start(job_id)` → stato `running`, event-queue aperta per streaming NDJSON.
- worker thread chiama `emit_event(job_id, {...})` per ogni step.
- `finish(job_id, result|error)` → stato terminale, queue chiusa con sentinel.
- `subscribe(job_id)` → async generator yielda eventi live + history.

Safety:
- Lock per filename evita due ingest concorrenti sullo stesso file.
- Queue bounded (1000 eventi) evita leak se frontend non consuma.
- Eventi serializzati a JSON prima di enqueue → no oggetti mutabili condivisi.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from llm_wiki.config import WIKI_ROOT

logger = logging.getLogger(__name__)

_JOBS_FILE = WIKI_ROOT / ".ingest_jobs.jsonl"
_MAX_EVENT_QUEUE = 1000
_MAX_JOBS_IN_MEMORY = 50

JobStatus = str  # "queued" | "running" | "done" | "error"


@dataclass
class Job:
    id: str
    filename: str
    status: JobStatus = "queued"
    options: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    backend: str | None = None
    pages_written: int = 0
    pages_needs_review: int = 0
    pages_conflict: int = 0
    pages_error: int = 0
    errors: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _JobRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._filename_locks: dict[str, threading.Lock] = {}
        self._event_queues: dict[str, asyncio.Queue[dict[str, Any] | None]] = {}
        self._event_history: dict[str, list[dict[str, Any]]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def create(self, filename: str, options: dict[str, Any]) -> Job:
        with self._lock:
            job = Job(id=uuid.uuid4().hex[:12], filename=filename, options=options)
            self._jobs[job.id] = job
            self._event_history[job.id] = []
            self._trim_if_needed()
            return job

    def _trim_if_needed(self) -> None:
        if len(self._jobs) <= _MAX_JOBS_IN_MEMORY:
            return
        # drop oldest terminal jobs
        terminal = sorted(
            (j for j in self._jobs.values() if j.status in ("done", "error")),
            key=lambda j: j.finished_at or j.created_at,
        )
        for j in terminal[: len(self._jobs) - _MAX_JOBS_IN_MEMORY]:
            self._jobs.pop(j.id, None)
            self._event_history.pop(j.id, None)
            self._event_queues.pop(j.id, None)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> list[Job]:
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )[:limit]

    def acquire_filename(self, filename: str) -> bool:
        """Prova ad acquisire lock esclusivo per un filename. False se già in uso."""
        with self._lock:
            lk = self._filename_locks.get(filename)
            if lk is None:
                lk = threading.Lock()
                self._filename_locks[filename] = lk
            return lk.acquire(blocking=False)

    def release_filename(self, filename: str) -> None:
        with self._lock:
            lk = self._filename_locks.get(filename)
        if lk is not None:
            try:
                lk.release()
            except RuntimeError:
                pass

    def start(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "running"
            job.started_at = time.time()
            self._event_queues[job_id] = asyncio.Queue(maxsize=_MAX_EVENT_QUEUE)

    def emit(self, job_id: str, event: dict[str, Any]) -> None:
        """Enqueue evento. Safe from non-async thread via `call_soon_threadsafe`."""
        with self._lock:
            q = self._event_queues.get(job_id)
            hist = self._event_history.get(job_id)
            if hist is not None:
                hist.append(event)
                # cap history to prevent leak
                if len(hist) > _MAX_EVENT_QUEUE:
                    del hist[: len(hist) - _MAX_EVENT_QUEUE]
        if q is None or self._loop is None:
            return
        try:
            self._loop.call_soon_threadsafe(self._safe_put, q, event)
        except RuntimeError:
            # loop closed
            pass

    @staticmethod
    def _safe_put(
        q: asyncio.Queue[dict[str, Any] | None], event: dict[str, Any]
    ) -> None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("job event queue full, dropping event")

    def finish(
        self,
        job_id: str,
        *,
        status: JobStatus,
        summary: str = "",
        backend: str | None = None,
        pages_written: int = 0,
        pages_needs_review: int = 0,
        pages_conflict: int = 0,
        pages_error: int = 0,
        errors: list[str] | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            job.finished_at = time.time()
            job.summary = summary
            job.backend = backend
            job.pages_written = pages_written
            job.pages_needs_review = pages_needs_review
            job.pages_conflict = pages_conflict
            job.pages_error = pages_error
            if errors:
                job.errors = errors
            q = self._event_queues.get(job_id)
        if q is not None and self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(q.put_nowait, None)  # sentinel
            except RuntimeError:
                pass
        _persist(job)

    async def subscribe(self, job_id: str):
        """Async generator: replay history + stream live events fino a sentinel."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            history = list(self._event_history.get(job_id, []))
            q = self._event_queues.get(job_id)
        for ev in history:
            yield ev
        if job.status in ("done", "error"):
            return
        if q is None:
            return
        while True:
            next_ev = await q.get()
            if next_ev is None:
                return
            yield next_ev


_registry = _JobRegistry()


def get_registry() -> _JobRegistry:
    return _registry


def _persist(job: Job) -> None:
    """Append job terminale a `.ingest_jobs.jsonl`. Best-effort, non blocking."""
    try:
        _JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _JOBS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(job.to_dict(), ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("persist job failed: %s", exc)


def load_recent_jobs(limit: int = 20) -> list[dict[str, Any]]:
    """Carica ultimi N job dal file di persistenza (per popolare history a freddo)."""
    if not _JOBS_FILE.exists():
        return []
    try:
        lines = _JOBS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out

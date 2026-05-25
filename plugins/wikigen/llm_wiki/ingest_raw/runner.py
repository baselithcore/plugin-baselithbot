"""Bridge fra `ingest_raw_file` (sync, lungo) e FastAPI (async, event-driven).

Aggancia un handler di logging al logger `llm_wiki.ingest_raw` per catturare gli
step della pipeline (extract / classify / plan / generate / lint / write / reindex)
e li inoltra al job registry come eventi strutturati. Il thread worker esegue
l'orchestrator sync senza toccare il loop asyncio.

Regressioni evitate:
- nessuna modifica all'orchestrator; logger handler è scoped al run.
- se handler fallisce, l'orchestrator continua (handler non solleva).
- filename lock impedisce doppio ingest sullo stesso file.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

from llm_wiki.config import WIKI_ROOT
from llm_wiki.ingest_raw.jobs import Job, get_registry
from llm_wiki.ingest_raw.orchestrator import IngestResult, ingest_raw_file, reindex_result

logger = logging.getLogger(__name__)

_PHASE_PATTERNS = [
    (re.compile(r"^extract:"), "extract"),
    (re.compile(r"^classify:"), "classify"),
    (re.compile(r"^plan:"), "plan"),
    (re.compile(r"^classify\+plan"), "classify_plan"),
    (re.compile(r"^generate:"), "generate"),
    (re.compile(r"^extracted:"), "extract"),
    (re.compile(r"^resume:"), "resume"),
    (re.compile(r"^skip:"), "skip"),
    (re.compile(r"^errore generando"), "generate"),
]
_PHASE_TIMING_RE = re.compile(r"^phase=(\w+) done \(([0-9.]+)s\)")


class _JobLogHandler(logging.Handler):
    """Cattura record dal logger `llm_wiki.ingest_raw.*` e li emette al job."""

    def __init__(self, job_id: str) -> None:
        super().__init__(level=logging.INFO)
        self.job_id = job_id

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            msg = record.getMessage()
            phase = _detect_phase(msg, record.levelname)
            event: dict[str, Any] = {
                "type": "log",
                "phase": phase,
                "level": record.levelname.lower(),
                "logger": record.name,
                "message": msg,
                "t": time.time(),
            }
            timing = _PHASE_TIMING_RE.match(msg)
            if timing:
                event["type"] = "timing"
                event["phase"] = timing.group(1)
                event["duration_s"] = float(timing.group(2))
            get_registry().emit(self.job_id, event)
        except Exception:  # pragma: no cover — never break orchestrator
            pass


def _detect_phase(msg: str, level: str) -> str:
    if level in ("WARNING", "ERROR", "CRITICAL"):
        return "error" if level != "WARNING" else "warn"
    for rx, phase in _PHASE_PATTERNS:
        if rx.match(msg):
            return phase
    return "info"


def run_ingest_job(
    *,
    job_id: str,
    raw_path: Path,
    options: dict[str, Any],
) -> None:
    """Entrypoint worker thread: esegue `ingest_raw_file` con logging bridged."""
    registry = get_registry()
    job = registry.get(job_id)
    if job is None:
        logger.error("run_ingest_job: job %s non trovato", job_id)
        return

    filename = job.filename
    acquired = registry.acquire_filename(filename)
    if not acquired:
        registry.finish(
            job_id,
            status="error",
            summary="file già in ingest — attendi il completamento del job precedente",
            errors=[f"filename lock busy: {filename}"],
        )
        return

    handler = _JobLogHandler(job_id)
    target_loggers = [
        logging.getLogger("llm_wiki.ingest_raw"),
        logging.getLogger("llm_wiki.ingest_raw.orchestrator"),
        logging.getLogger("llm_wiki.ingest_raw.extractor"),
        logging.getLogger("llm_wiki.ingest_raw.planner"),
        logging.getLogger("llm_wiki.ingest_raw.generator"),
        logging.getLogger("llm_wiki.ingest_raw.critic"),
        logging.getLogger("llm_wiki.ingest_raw.linter"),
        logging.getLogger("llm_wiki.wiki.ingest"),
    ]
    for lg in target_loggers:
        lg.addHandler(handler)

    registry.start(job_id)
    registry.emit(
        job_id,
        {
            "type": "status",
            "status": "running",
            "message": f"avvio ingest: {filename}",
            "t": time.time(),
        },
    )

    try:
        # Reindex eseguito DOPO il finalize event così l'UI vede `done`
        # subito, senza attendere l'embed BGE-M3 + upsert Qdrant. Il tempo
        # totale del thread è uguale; solo la latenza percepita migliora.
        do_reindex = bool(options.get("reindex", True)) and not bool(options.get("dry_run", False))
        result: IngestResult = ingest_raw_file(
            raw_path,
            model=options.get("model"),
            dry_run=bool(options.get("dry_run", False)),
            overwrite=bool(options.get("overwrite", False)),
            reindex=False,
            only_source_page=bool(options.get("only_source_page", False)),
        )
        _finalize_from_result(job_id, result)
        if do_reindex:
            _run_reindex_phase(job_id, result)
    except Exception as exc:
        logger.exception("ingest job %s failed", job_id)
        registry.emit(
            job_id,
            {
                "type": "status",
                "status": "error",
                "message": f"errore fatale: {exc}",
                "t": time.time(),
            },
        )
        registry.finish(
            job_id,
            status="error",
            summary=str(exc),
            errors=[str(exc)],
        )
    finally:
        for lg in target_loggers:
            try:
                lg.removeHandler(handler)
            except Exception:
                pass
        registry.release_filename(filename)


def _run_reindex_phase(job_id: str, result: IngestResult) -> None:
    """Run reindex in a daemon thread DOPO che il job è già `done`.

    Il job event queue è chiuso a `_finalize_from_result`; l'UI vede
    completamento subito senza attendere embed BGE-M3 + upsert Qdrant
    (~5–15s per ingest tipico). Eventuali errori di reindex sono loggati
    ma non riaprono il job (semantica fire-and-forget).
    """

    def _worker() -> None:
        t0 = time.monotonic()
        try:
            n = reindex_result(result)
            dt = time.monotonic() - t0
            logger.info("reindex completato (background): %d pagine", n)
            # Stesso formato di `_timed` in orchestrator → runner emit
            # come timing event per omogeneità con altre phase.
            logger.info("phase=reindex done (%.2fs)", dt)
        except Exception:
            logger.exception("reindex (background) failed for job %s", job_id)

    threading.Thread(
        target=_worker,
        name=f"ingest-reindex-{job_id}",
        daemon=True,
    ).start()


def _finalize_from_result(job_id: str, result: IngestResult) -> None:
    registry = get_registry()

    pages_written = sum(1 for p in result.pages if p.status == "written")
    pages_needs_review = sum(1 for p in result.pages if p.status == "needs-review")
    pages_conflict = sum(1 for p in result.pages if p.status == "conflict")
    pages_error = sum(1 for p in result.pages if p.status == "error")

    # evento per pagina (UI può listarle)
    for p in result.pages:
        try:
            rel = p.target_path.relative_to(WIKI_ROOT)
        except ValueError:
            rel = p.target_path
        registry.emit(
            job_id,
            {
                "type": "page",
                "path": str(rel),
                "status": p.status,
                "iterations": p.iterations,
                "bytes": p.bytes_written,
                "message": p.message,
                "t": time.time(),
            },
        )

    status = "done" if pages_error == 0 else "error"
    summary = result.summary()
    registry.emit(
        job_id,
        {
            "type": "status",
            "status": status,
            "message": summary,
            "t": time.time(),
        },
    )
    registry.finish(
        job_id,
        status=status,
        summary=summary,
        backend=result.backend,
        pages_written=pages_written,
        pages_needs_review=pages_needs_review,
        pages_conflict=pages_conflict,
        pages_error=pages_error,
        errors=list(result.errors),
    )

    if pages_written > 0 or pages_needs_review > 0:
        _maybe_regenerate_doc_questions()


def _maybe_regenerate_doc_questions() -> None:
    """Fire the doc-grounded starter-question generator (best-effort).

    Marker file in the pack dir enforces one-shot semantics across
    worker threads, so this is safe to call from every ingest finalize.
    Never raises — failures surface as warning logs only; the chips
    written by scaffold-time synth remain in place.
    """
    try:
        from llm_wiki import config as _cfg

        if not getattr(_cfg, "QUESTIONS_FROM_DOCS_ENABLED", True):
            return
        from llm_wiki.admin.questions_from_docs import regenerate_questions_from_docs
        from llm_wiki.domain.registry import get_pack
    except Exception as exc:  # noqa: BLE001 — optional dep / import-time failure
        logger.debug("[questions-from-docs] hook unavailable: %s", exc)
        return

    try:
        pack = get_pack()
    except Exception as exc:  # noqa: BLE001 — no active pack
        logger.debug("[questions-from-docs] no active pack: %s", exc)
        return

    pack_dir: Path | None = getattr(pack, "root", None)
    if pack_dir is None or not pack_dir.is_dir():
        return

    try:
        wiki_dir = WIKI_ROOT / "wiki"
    except Exception:  # noqa: BLE001 — defensive
        return

    try:
        outcome = regenerate_questions_from_docs(pack_dir, wiki_dir)
    except Exception:  # noqa: BLE001 — generator itself swallows; this is paranoia
        logger.exception("[questions-from-docs] generator raised unexpectedly")
        return

    if outcome.applied:
        logger.info(
            "[questions-from-docs] %d question(s) written for pack at %s",
            outcome.questions_written,
            pack_dir,
        )
    elif outcome.warning:
        logger.warning("[questions-from-docs] %s", outcome.warning)


def spawn_worker(job: Job, raw_path: Path, options: dict[str, Any]) -> None:
    """Lancia worker thread daemon. Non bloccante."""
    t = threading.Thread(
        target=run_ingest_job,
        kwargs={"job_id": job.id, "raw_path": raw_path, "options": options},
        name=f"ingest-raw-{job.id}",
        daemon=True,
    )
    t.start()

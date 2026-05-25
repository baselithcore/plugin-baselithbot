"""Dataclasses + tiny utilities used across orchestrator submodules."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from llm_wiki.ingest_raw.linter import LintReport
from llm_wiki.ingest_raw.schemas import IngestPlan

logger = logging.getLogger(__name__)


class RawDirWriteAttempt(RuntimeError):
    """Attempt to write into ``raw/`` — forbidden by design."""


@dataclass
class PageResult:
    target_path: Path
    status: str
    lint_report: LintReport | None = None
    iterations: int = 0
    bytes_written: int = 0
    message: str = ""


@dataclass
class IngestResult:
    source_path: Path
    backend: str
    plan: IngestPlan | None = None
    pages: list[PageResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    source_hash: str | None = None
    skipped_reason: str | None = None
    timings: dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        ok = sum(1 for p in self.pages if p.status == "written")
        need = sum(1 for p in self.pages if p.status == "needs-review")
        dry = sum(1 for p in self.pages if p.status == "dry-run")
        skip = sum(1 for p in self.pages if p.status == "skipped")
        timing = " ".join(f"{k}={v:.1f}s" for k, v in self.timings.items())
        return (
            f"source={self.source_path.name} backend={self.backend} "
            f"written={ok} needs-review={need} dry-run={dry} skipped={skip} "
            f"errors={len(self.errors)}" + (f" | timings: {timing}" if timing else "")
        )


@contextmanager
def _timed(result: IngestResult, phase: str) -> Iterator[None]:
    """Context manager: misura durata e accumula in ``result.timings``.

    Output a logger.info come ``phase=<name> done (Xs)`` così il
    runner.py loop pattern lo cattura come evento e l'UI può mostrare
    breakdown senza endpoint dedicato.
    """
    t0 = time.monotonic()
    try:
        yield
    finally:
        dt = time.monotonic() - t0
        result.timings[phase] = result.timings.get(phase, 0.0) + dt
        logger.info("phase=%s done (%.2fs)", phase, dt)

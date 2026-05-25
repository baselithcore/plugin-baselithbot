"""Raw-dir invariants + resume / skip-unchanged checks."""

from __future__ import annotations

import logging
from pathlib import Path

from llm_wiki.config import RAW_DIR, WIKI_DIR
from llm_wiki.domain.registry import get_pack
from llm_wiki.ingest_raw.cache import read_source_hash
from llm_wiki.ingest_raw.orchestrator.models import (
    IngestResult,
    PageResult,
    RawDirWriteAttempt,
)
from llm_wiki.ingest_raw.planner import slug_from_raw

logger = logging.getLogger(__name__)


def _current_pack_name() -> str | None:
    try:
        return get_pack().name
    except Exception:
        return None


def _assert_in_raw(path: Path) -> None:
    try:
        path.relative_to(RAW_DIR)
    except ValueError as exc:
        raise ValueError(f"`raw_path` must live under {RAW_DIR}. Got: {path}") from exc


def _assert_not_raw(path: Path) -> None:
    try:
        path.relative_to(RAW_DIR)
    except ValueError:
        return
    raise RawDirWriteAttempt(f"attempted write inside `raw/`: {path}")


def _try_skip_unchanged(raw_path: Path, source_hash: str, result: IngestResult) -> bool:
    """Short-circuit la pipeline se il PDF è identico a un'ingest precedente.

    Necessario per ``AUTO_INGEST_ON_STARTUP``: a ogni boot la lifespan
    riavvia ingest su tutti i PDF in ``raw/`` privi di source page. Senza
    skip, un riavvio (es. dopo cambio config) ri-genera ogni pagina —
    minuti di LLM inutili.
    """
    try:
        pack = get_pack()
    except Exception:
        return False
    sources_pt = pack.page_type("source")
    sources_folder = (sources_pt.folder if sources_pt else None) or "sources"
    slug = slug_from_raw(str(raw_path))
    page_path = WIKI_DIR / sources_folder / f"{slug}.md"
    existing_hash = read_source_hash(page_path)
    if existing_hash != source_hash:
        return False
    logger.info("skip: %s — source_hash invariato (%s)", raw_path.name, source_hash)
    result.skipped_reason = f"source_hash invariato: {source_hash}"
    result.pages.append(
        PageResult(
            target_path=page_path,
            status="skipped",
            message="source_hash invariato — pipeline saltata",
        )
    )
    return True

"""Cache helpers per ingest: skip su PDF invariati + extract cache.

Due ottimizzazioni complementari, entrambe chiavate sull'sha256 del PDF:

1. **Skip totale**: la source page conserva ``source_hash`` nel
   frontmatter. Se il file ``raw/`` non è cambiato (hash identico) e
   ``overwrite=False``, salta classify/plan/generate/lint — tutta la
   pipeline LLM. Ogni successivo restart o auto-ingest costa quanto
   leggere l'header di un file.
2. **Extract cache**: il backend docling impiega 5–60s per PDF. Cache
   l'``ExtractedDocument`` su disco indicizzato per hash; il secondo run
   sullo stesso file (anche se la source page è stata cancellata) salta
   l'estrazione. Cache invalidate naturalmente: hash diverso = miss.

Cache vive sotto ``WIKI_ROOT/.cache/extract/`` — stesso trust boundary
del vault. Serializzazione JSON: solo dati primitivi (no pickle), così
una directory cache trovata casualmente non può eseguire codice.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict
from pathlib import Path

from llm_wiki.config import WIKI_ROOT
from llm_wiki.ingest_raw.extractor import (
    ExtractedDocument,
    ExtractedTable,
    PageContent,
)

logger = logging.getLogger(__name__)

_HASH_LEN = 16  # sha256 troncato; 64 bit anti-collisione, leggibile
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SOURCE_HASH_RE = re.compile(r"^source_hash:\s*['\"]?([a-f0-9]+)['\"]?\s*$", re.MULTILINE)
# v2: pages persistono solo come count (gli unici consumatori di
# ExtractedDocument.pages a valle della cache leggono `n_pages`, non i corpi).
# Su PDF grandi taglia ~50% dimensione cache + load più veloce.
_CACHE_VERSION = 2


def compute_source_hash(path: Path) -> str:
    """sha256 troncato del file. Streaming: gestisce anche PDF da 100MB+."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:_HASH_LEN]


def read_source_hash(page_path: Path) -> str | None:
    """Estrai ``source_hash`` dal frontmatter di una source page, se presente."""
    if not page_path.is_file():
        return None
    try:
        text = page_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    h = _SOURCE_HASH_RE.search(m.group(1))
    return h.group(1) if h else None


def _cache_dir() -> Path:
    return WIKI_ROOT / ".cache" / "extract"


def cached_extract_path(source_hash: str) -> Path:
    return _cache_dir() / f"{source_hash}.json"


def load_cached_extract(source_hash: str) -> ExtractedDocument | None:
    """Carica ExtractedDocument da cache JSON. None su miss o payload invalido."""
    p = cached_extract_path(source_hash)
    if not p.is_file():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("extract cache: load fallito (%s), ignoro", exc)
        return None
    if not isinstance(payload, dict) or payload.get("v") != _CACHE_VERSION:
        return None
    try:
        return _decode(payload)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("extract cache: payload invalido (%s), ignoro", exc)
        return None


def save_cached_extract(source_hash: str, doc: ExtractedDocument) -> None:
    """Salva ExtractedDocument come JSON. Best-effort: errori non sono fatali."""
    p = cached_extract_path(source_hash)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(_encode(doc), ensure_ascii=False), encoding="utf-8")
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("extract cache: save fallito (%s)", exc)


def _encode(doc: ExtractedDocument) -> dict:
    return {
        "v": _CACHE_VERSION,
        "source_path": str(doc.source_path),
        "backend": doc.backend,
        "markdown": doc.markdown,
        "n_pages": len(doc.pages),
        "tables": [asdict(t) for t in doc.tables],
        "metadata": _coerce_metadata(doc.metadata),
    }


def _coerce_metadata(meta: dict) -> dict:
    """metadata può contenere oggetti non-JSON (es. da marker). str() come fallback."""
    out: dict = {}
    for k, v in meta.items():
        try:
            json.dumps(v)
            out[k] = v
        except (TypeError, ValueError):
            out[k] = str(v)
    return out


def _decode(payload: dict) -> ExtractedDocument:
    # `pages` ricostruito come stub vuoti — i consumatori a valle leggono
    # solo `n_pages` (vedi `_CACHE_VERSION` 2). Numero coerente per
    # `_cap_derived_pages` e analoghi.
    n_pages = int(payload.get("n_pages") or len(payload.get("pages") or []) or 1)
    return ExtractedDocument(
        source_path=Path(payload["source_path"]),
        backend=payload["backend"],
        markdown=payload["markdown"],
        pages=[PageContent(number=i + 1, markdown="", text="") for i in range(n_pages)],
        tables=[ExtractedTable(**t) for t in payload.get("tables", [])],
        metadata=payload.get("metadata", {}),
    )


# --- ingest state (per resume di job interrotti) ----------------------------

_STATE_VERSION = 1


def _state_dir() -> Path:
    return WIKI_ROOT / ".cache" / "state"


def state_path(source_hash: str) -> Path:
    return _state_dir() / f"{source_hash}.json"


def load_ingest_state(source_hash: str, pack_name: str) -> dict | None:
    """Carica stato di ingest interrotto. None se assente, corrotto, o pack
    diverso (cambio strategie/prompts invalida le pagine già generate)."""
    p = state_path(source_hash)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("ingest state: load fallito (%s)", exc)
        return None
    if not isinstance(data, dict):
        return None
    if data.get("v") != _STATE_VERSION:
        return None
    if data.get("source_hash") != source_hash:
        return None
    if data.get("pack_name") != pack_name:
        logger.info(
            "ingest state: pack mismatch (saved=%s current=%s) — restart pulito",
            data.get("pack_name"),
            pack_name,
        )
        return None
    return data


def save_ingest_state(
    source_hash: str,
    *,
    pack_name: str,
    raw_path: str,
    plan_dict: dict,
    page_status: dict[str, str] | None = None,
) -> None:
    """Salva stato post-plan per consentire resume su crash/timeout futuri."""
    p = state_path(source_hash)
    payload = {
        "v": _STATE_VERSION,
        "source_hash": source_hash,
        "pack_name": pack_name,
        "raw_path": raw_path,
        "plan": plan_dict,
        "page_status": page_status or {},
    }
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("ingest state: save fallito (%s)", exc)


def update_page_status(source_hash: str, target_path: str, status: str) -> None:
    """Aggiorna lo status di una singola pagina nello state file. Best-effort."""
    p = state_path(source_hash)
    if not p.is_file():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        page_status = data.get("page_status") or {}
        page_status[target_path] = status
        data["page_status"] = page_status
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.debug("ingest state: update fallito (%s)", exc)


def clear_ingest_state(source_hash: str) -> None:
    """Rimuove state file dopo successo completo."""
    p = state_path(source_hash)
    try:
        p.unlink(missing_ok=True)
    except OSError as exc:
        logger.debug("ingest state: clear fallito (%s)", exc)

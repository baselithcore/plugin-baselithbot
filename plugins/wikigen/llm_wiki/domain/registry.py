"""Domain Pack registry.

Loads exactly one :class:`DomainPack` per process. Single-tenant: an HTTP
server, a CLI invocation or a worker thread all share the same pack — the
choice is made at scaffolding time via ``APP_DOMAIN`` and frozen for the
process lifetime.

Discovery order
---------------
1. ``DOMAIN_PACK_DIR`` env var — explicit absolute path (test-friendly).
2. ``<repo_root>/domains/<APP_DOMAIN>/``.

The first ``pack.yaml`` found wins. Missing pack raises
:class:`DomainPackNotFoundError` immediately at import time of any module
that calls :func:`load_pack` — fail-fast beats silently shipping a wiki
with default placeholders.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Final

import yaml
from pydantic import ValidationError

from llm_wiki.domain.pack import DomainPack

logger = logging.getLogger(__name__)

PACK_FILENAME: Final[str] = "pack.yaml"


class DomainPackError(RuntimeError):
    """Base class for pack loading failures."""


class DomainPackNotFoundError(DomainPackError):
    """No pack matches the requested ``APP_DOMAIN``."""


class DomainPackInvalidError(DomainPackError):
    """Pack file exists but failed schema validation."""


_lock = threading.Lock()
_cached: DomainPack | None = None
_cached_root: Path | None = None


def _repo_root() -> Path:
    """Project root, used as default search base for ``domains/`` lookup.

    Resolution: walk up from this file until a directory containing both
    ``pyproject.toml`` and ``domains/`` is found. Falls back to two levels
    up (``llm_wiki/domain/registry.py`` → ``<repo_root>``) if the walk fails.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "domains").exists():
            return parent
    return here.parents[2]


def _candidate_paths(app_domain: str) -> list[Path]:
    paths: list[Path] = []
    explicit = os.getenv("DOMAIN_PACK_DIR", "").strip()
    if explicit:
        paths.append(Path(explicit).expanduser().resolve())
    paths.append(_repo_root() / "domains" / app_domain)
    return paths


def _read_pack_yaml(pack_dir: Path) -> dict:
    pack_file = pack_dir / PACK_FILENAME
    if not pack_file.is_file():
        raise DomainPackNotFoundError(f"missing {PACK_FILENAME} at {pack_dir}")
    try:
        with pack_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise DomainPackInvalidError(f"invalid YAML in {pack_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise DomainPackInvalidError(f"{pack_file} must contain a YAML mapping at root")
    return data


def load_pack(app_domain: str | None = None, *, force: bool = False) -> DomainPack:
    """Materialise the active :class:`DomainPack`.

    Parameters
    ----------
    app_domain
        Override the ``APP_DOMAIN`` env var. Mostly useful for tests.
    force
        Bypass the in-process cache and reload from disk.

    Raises
    ------
    DomainPackNotFoundError
        ``APP_DOMAIN`` is unset or no pack directory matches.
    DomainPackInvalidError
        ``pack.yaml`` exists but does not satisfy the schema.
    """
    global _cached, _cached_root

    name = (app_domain or os.getenv("APP_DOMAIN", "") or "").strip()
    if not name:
        raise DomainPackNotFoundError(
            "APP_DOMAIN env var is unset; pick a pack from `domains/` or run "
            "`python -m llm_wiki init --domain <name>` to scaffold one."
        )

    with _lock:
        if not force and _cached is not None:
            return _cached

        last_error: Exception | None = None
        for candidate in _candidate_paths(name):
            try:
                data = _read_pack_yaml(candidate)
            except DomainPackNotFoundError as exc:
                last_error = exc
                continue

            data.setdefault("name", name)
            try:
                pack = DomainPack(**data)
            except ValidationError as exc:
                raise DomainPackInvalidError(
                    f"pack at {candidate} failed validation:\n{exc}"
                ) from exc

            if pack.name != name:
                raise DomainPackInvalidError(
                    f"pack name mismatch: APP_DOMAIN={name!r} but pack.yaml "
                    f"declares name={pack.name!r} at {candidate}"
                )

            pack.root = candidate.resolve()
            _cached = pack
            _cached_root = pack.root
            _auto_enable_graph_flags(pack)
            return pack

        raise DomainPackNotFoundError(
            f"no pack found for APP_DOMAIN={name!r}. "
            f"Searched: {', '.join(str(p) for p in _candidate_paths(name))}. "
            f"Last error: {last_error}"
        )


_DEFAULT_GRAPH_ENTITY_IDS: Final[frozenset[str]] = frozenset({"concept", "entity", "source"})
_DEFAULT_GRAPH_RELATION_IDS: Final[frozenset[str]] = frozenset(
    {"RELATES_TO", "PART_OF", "DERIVES_FROM", "DEFINED_BY"}
)


def _has_custom_graph_spec(pack: DomainPack) -> bool:
    """True quando il pack dichiara una GraphSpec personalizzata (non solo
    i default engine). Usato dall'auto-enable per evitare di attivare il
    KG su pack che non hanno realmente curato l'ontologia.

    Trigger se almeno uno fra:
        - entity_types non identico al default {concept, entity, source};
        - relation_types non identico al default {RELATES_TO, PART_OF,
          DERIVES_FROM, DEFINED_BY};
        - extraction_hints non vuoto.
    """
    if pack.graph.extraction_hints.strip():
        return True
    et_ids = {e.id for e in pack.graph.entity_types}
    if et_ids and et_ids != _DEFAULT_GRAPH_ENTITY_IDS:
        return True
    rt_ids = {r.id for r in pack.graph.relation_types}
    if rt_ids and rt_ids != _DEFAULT_GRAPH_RELATION_IDS:
        return True
    return False


def _auto_enable_graph_flags(pack: DomainPack) -> None:
    """Auto-attiva i flag KG quando il pack dichiara una GraphSpec custom.

    Override esplicito via env sempre vincente: la funzione muta solo i
    flag a default. Set di env-name precedente (per fallback su flag
    non-toccati) ricavato dalla presenza nella ``os.environ``.

    Coerente con graphify principle "always-queryable index": un pack con
    ontologia custom HA fatto il lavoro di modellazione → l'engine dovrebbe
    attivare estrazione + retrieval graph-aware automaticamente. Senza
    questo, l'admin deve ricordarsi di toggle tre env var separati ad
    ogni deploy nuovo.

    Mute log su pack con default-only graph (rumore zero).
    """
    if not _has_custom_graph_spec(pack):
        return
    # Lazy import: config carica .env a module-load; modificare i suoi
    # globali è OK perché tutti i lookup avvengono via lookup attributo.
    from llm_wiki import config as _config

    activated: list[str] = []
    if not os.getenv("GRAPH_EXTRACT_ENABLED") and not _config.GRAPH_EXTRACT_ENABLED:
        _config.GRAPH_EXTRACT_ENABLED = True
        activated.append("GRAPH_EXTRACT_ENABLED")
    if not os.getenv("GRAPH_RAG_ENABLED") and not _config.GRAPH_RAG_ENABLED:
        _config.GRAPH_RAG_ENABLED = True
        activated.append("GRAPH_RAG_ENABLED")
    if (
        not os.getenv("GRAPH_CHUNK_ENTITY_TAGGING_ENABLED")
        and not _config.GRAPH_CHUNK_ENTITY_TAGGING_ENABLED
    ):
        _config.GRAPH_CHUNK_ENTITY_TAGGING_ENABLED = True
        activated.append("GRAPH_CHUNK_ENTITY_TAGGING_ENABLED")
    if activated:
        logger.info(
            "[graph.auto-enable] pack '%s' ha GraphSpec custom — attivati: %s",
            pack.name,
            ", ".join(activated),
        )


def get_pack() -> DomainPack:
    """Return the currently loaded pack.

    Convenience wrapper for callers that already trust the bootstrap path.
    Equivalent to ``load_pack()`` but skips the env read on the hot path.
    """
    if _cached is not None:
        return _cached
    return load_pack()


def reset_pack_cache() -> None:
    """Drop the cached pack. Test-only — production runs are single-tenant."""
    global _cached, _cached_root
    with _lock:
        _cached = None
        _cached_root = None

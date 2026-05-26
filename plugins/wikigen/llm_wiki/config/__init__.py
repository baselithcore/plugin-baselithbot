"""Env-based configuration for the white-label wiki engine.

Pattern inherited from the reference project: every setting is resolved at
import time from environment variables with sensible defaults and safe
coercion. No singleton clients are exposed at module level (build them
on-demand inside the relevant helpers).

White-label additions
---------------------
``APP_DOMAIN`` selects which Domain Pack drives prompts, schema, page
taxonomy and UI labels. ``DOMAIN_PACK_DIR`` lets you override the on-disk
location (useful for tests and out-of-tree packs). ``COLLECTION_NAME`` now
defaults to ``<APP_DOMAIN>-wiki`` so two co-located deployments do not
collide on a shared Qdrant instance.

Modular layout (>500 LOC budget):
- :mod:`._coerce` — env coercion helpers + dotenv guards
- :mod:`._static` — tunables that don't change after process start
- This module — tenant-coupled vars (APP_DOMAIN / WIKI_ROOT / LLM provider)
  plus :func:`refresh_paths` and :func:`print_banner`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from llm_wiki.config._coerce import (
    _bool,
    _drop_stale_empty_inheritance,
    _float,  # noqa: F401 — used by submodules importing via package namespace
    _int,
    _optional_str,
    _str,
    _warn_shell_env_conflicts,
)

# Skip the stale-inheritance pre-clean when pytest is active so test
# fixtures using ``monkeypatch.setenv("APP_DOMAIN", "")`` to simulate
# setup mode keep their explicit empty value even when the developer's
# `.env` happens to carry a real domain.
if "pytest" not in sys.modules and "_pytest" not in sys.modules:
    _drop_stale_empty_inheritance("APP_DOMAIN", "WIKI_ROOT", "DOMAIN_PACK_DIR")

# Carica PRIMA il ``.env`` del plugin (path assoluto rispetto al
# modulo) — necessario quando il backend è lanciato da una cwd diversa
# dal dir del plugin (es. ``baselith run`` dalla repo root). Falla
# silenziosamente se il file manca: l'env del processo resta autoritativo.
# ``override=False`` rispetta variabili già settate (Docker, CI, prod).
from pathlib import Path as _Path

_PLUGIN_ENV = _Path(__file__).resolve().parents[2] / ".env"
if _PLUGIN_ENV.is_file():
    load_dotenv(_PLUGIN_ENV, override=False)

# Fallback: prova anche un ``.env`` in cwd (back-compat con il flusso
# di sviluppo che lancia il backend da ``plugins/wikigen``).
load_dotenv(override=False)


# --- white-label selector --------------------------------------------------

# Process-wide vertical selector. Empty value is allowed at import time so
# tooling that doesn't load a pack (linters, alembic-style CLI, etc.) can
# still parse the module — but `core.domain.registry.load_pack()` will
# refuse to materialise a pack when this is unset.
APP_DOMAIN = _str("APP_DOMAIN", "")

# Optional override for the Domain Pack root. When unset the registry
# defaults to `<repo_root>/domains/<APP_DOMAIN>/`.
DOMAIN_PACK_DIR = _optional_str("DOMAIN_PACK_DIR")


# --- vault -----------------------------------------------------------------


def _resolve_wiki_root() -> str:
    """Wiki SHARED model (Fase 4 multi-tenancy refactor).

    Resolution order:
    1. ``WIKI_ROOT`` esplicito — path canonico nelle nuove deploy.
    2. Per-pack legacy ``WIKI_ROOT_<APP_DOMAIN>`` — backward-compat.
    3. Repo root — fallback per tooling senza pack attivo.
    """
    explicit = _optional_str("WIKI_ROOT")
    if explicit:
        return explicit
    if APP_DOMAIN:
        legacy_key = "WIKI_ROOT_" + APP_DOMAIN.upper().replace("-", "_")
        legacy = _optional_str(legacy_key)
        if legacy:
            return legacy
    return str(Path(__file__).resolve().parent.parent.parent)


WIKI_ROOT = Path(_resolve_wiki_root())
WIKI_DIR = WIKI_ROOT / _str("WIKI_DIR", "wiki")
# `raw/` is read-only by convention: exposed for detect/skip, never written.
RAW_DIR = WIKI_ROOT / _str("RAW_DIR", "raw")

# Override for Obsidian's vault registry name when it differs from the
# WIKI_ROOT directory basename (Obsidian lets users rename a vault on
# registration). Empty = derive from `WIKI_ROOT.name`.
OBSIDIAN_VAULT_NAME = _str("OBSIDIAN_VAULT_NAME", "")


# --- LLM provider (tenant-coupled — sees refresh_paths) --------------------

LLM_VENDOR = _str("LLM_VENDOR", "ollama").lower()
# Per-phase vendor split: chat (RAG) and ingest can pick independently
# from each other. Both default to ``LLM_VENDOR`` so single-vendor
# deployments work unchanged.
RAG_VENDOR = (_str("RAG_VENDOR", "") or LLM_VENDOR).lower()
INGEST_VENDOR = (_str("INGEST_VENDOR", "") or LLM_VENDOR).lower()

OLLAMA_URL = _str("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = _str("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_EMBED_MODEL = _optional_str("OLLAMA_EMBED_MODEL")

OPENAI_API_KEY = _optional_str("OPENAI_API_KEY")
OPENAI_API_BASE = _str("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = _str("OPENAI_MODEL", "gpt-4o-mini")

# Modello dedicato a classify/plan/generate durante ingest.
INGEST_OLLAMA_MODEL = _str("INGEST_OLLAMA_MODEL", "") or "llama3.2:latest"
INGEST_OPENAI_MODEL = _str("INGEST_OPENAI_MODEL", "") or OPENAI_MODEL

# Modello dedicato a `prompt_synthesizer` (scaffold-time domain prompt
# generation). Vuoto = fallback automatico (vedi prompt_synthesizer).
SYNTHESIS_MODEL = _str("SYNTHESIS_MODEL", "")

# Max concurrent ingest LLM calls. Default 1 per Ollama (single-model
# inference is serialized in-daemon), 8 per OpenAI (managed endpoint
# load-balances server-side).
_DEFAULT_INGEST_CONCURRENT = 8 if INGEST_VENDOR == "openai" else 1
INGEST_MAX_CONCURRENT = max(
    1, _int("INGEST_MAX_CONCURRENT", _DEFAULT_INGEST_CONCURRENT)
)
# Quando True, classify/plan partono con `format="json"` invece dello schema
# JSON pieno. Default True su Ollama, False su OpenAI.
INGEST_LOOSE_JSON = _bool("INGEST_LOOSE_JSON", INGEST_VENDOR == "ollama")


# --- tenant-derived constants ----------------------------------------------

# Qdrant
QDRANT_PATH = WIKI_ROOT / _str("QDRANT_PATH", "./qdrant_data")
# Default scoping: ``<APP_DOMAIN>-wiki`` quando il pack è caricato.
COLLECTION_NAME = _str(
    "COLLECTION_NAME", f"{APP_DOMAIN}-wiki" if APP_DOMAIN else "wiki"
)

# Graph
GRAPH_DB_NAME = _str("GRAPH_DB_NAME", COLLECTION_NAME)
GRAPH_EXTRACT_MODEL = _str("GRAPH_EXTRACT_MODEL", "")
GRAPH_REPORT_DIR = _str("GRAPH_REPORT_DIR", str(WIKI_ROOT / ".graphify"))

# Feedback (path-dependent)
FEEDBACK_LOG_PATH = _str("FEEDBACK_LOG_PATH", str(WIKI_ROOT / ".feedback.jsonl"))


# --- static (re-export) ----------------------------------------------------

# Force-reload the static submodule whenever the package is reloaded
# (``importlib.reload(config)``) so test fixtures that flip env vars
# defined in ``_static.py`` (POSTGRES_ENABLED, ACCESS_TOKEN_TTL_MINUTES,
# …) actually observe the new values. First import is a no-op since
# ``_static`` isn't yet in ``sys.modules``.
import importlib as _importlib  # noqa: E402

if "llm_wiki.config._static" in sys.modules:
    _importlib.reload(sys.modules["llm_wiki.config._static"])

from llm_wiki.config._static import *  # noqa: E402,F401,F403


def refresh_paths() -> None:
    """Re-resolve ``APP_DOMAIN``/``WIKI_ROOT``/``WIKI_DIR``/``RAW_DIR``
    and provider/ingest constants from the current ``os.environ``.

    The setup wizard mutates ``os.environ`` (``APP_DOMAIN``, ``WIKI_ROOT``,
    ``LLM_VENDOR``, provider keys) in the running worker so subsequent
    same-process reads pick up the new tenant without a restart.
    Module-level constants above are evaluated once at import — this
    helper updates them in place so downstream consumers (``RAW_DIR``
    in ``autostart_pending_ingest``, ``WIKI_DIR`` in the wiki parser,
    ``LLM_VENDOR`` in ``ingest_raw.llm_client``, etc.) see the
    post-scaffold values.

    Idempotent. Safe to call from any thread; assignments to module
    globals are atomic in CPython.
    """
    global \
        APP_DOMAIN, \
        DOMAIN_PACK_DIR, \
        WIKI_ROOT, \
        WIKI_DIR, \
        RAW_DIR, \
        OBSIDIAN_VAULT_NAME
    global LLM_VENDOR, RAG_VENDOR, INGEST_VENDOR
    global OLLAMA_URL, OLLAMA_MODEL, OLLAMA_EMBED_MODEL
    global OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL
    global INGEST_OLLAMA_MODEL, INGEST_OPENAI_MODEL, INGEST_LOOSE_JSON
    global SYNTHESIS_MODEL, GRAPH_EXTRACT_MODEL

    APP_DOMAIN = _str("APP_DOMAIN", "")
    DOMAIN_PACK_DIR = _optional_str("DOMAIN_PACK_DIR")
    WIKI_ROOT = Path(_resolve_wiki_root())
    WIKI_DIR = WIKI_ROOT / _str("WIKI_DIR", "wiki")
    RAW_DIR = WIKI_ROOT / _str("RAW_DIR", "raw")
    OBSIDIAN_VAULT_NAME = _str("OBSIDIAN_VAULT_NAME", "")

    LLM_VENDOR = _str("LLM_VENDOR", "ollama").lower()
    RAG_VENDOR = (_str("RAG_VENDOR", "") or LLM_VENDOR).lower()
    INGEST_VENDOR = (_str("INGEST_VENDOR", "") or LLM_VENDOR).lower()
    OLLAMA_URL = _str("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = _str("OLLAMA_MODEL", "llama3.1:8b")
    OLLAMA_EMBED_MODEL = _optional_str("OLLAMA_EMBED_MODEL")
    OPENAI_API_KEY = _optional_str("OPENAI_API_KEY")
    OPENAI_API_BASE = _str("OPENAI_API_BASE", "https://api.openai.com/v1")
    OPENAI_MODEL = _str("OPENAI_MODEL", "gpt-4o-mini")
    INGEST_OLLAMA_MODEL = _str("INGEST_OLLAMA_MODEL", "") or "llama3.2:latest"
    INGEST_OPENAI_MODEL = _str("INGEST_OPENAI_MODEL", "") or OPENAI_MODEL
    INGEST_LOOSE_JSON = _bool("INGEST_LOOSE_JSON", INGEST_VENDOR == "ollama")
    SYNTHESIS_MODEL = _str("SYNTHESIS_MODEL", "")
    GRAPH_EXTRACT_MODEL = _str("GRAPH_EXTRACT_MODEL", "")


# --- banner ----------------------------------------------------------------


def print_banner() -> None:
    """Print a diagnostic banner to stderr with the active configuration."""
    _warn_shell_env_conflicts()
    print(f"[wiki] domain: {APP_DOMAIN or '<unset>'}", file=sys.stderr)
    print(f"[wiki] vault: {WIKI_ROOT}", file=sys.stderr)
    print(f"[wiki] LLM: {LLM_VENDOR} → ", end="", file=sys.stderr)
    if LLM_VENDOR == "openai":
        print(f"{OPENAI_API_BASE} / {OPENAI_MODEL}", file=sys.stderr)
    else:
        print(f"{OLLAMA_URL} / {OLLAMA_MODEL}", file=sys.stderr)
    print(f"[wiki] Embedder: {EMBEDDER_MODEL}", file=sys.stderr)  # noqa: F405 — from _static *
    print(
        f"[wiki] Qdrant: {QDRANT_MODE} → "  # noqa: F405
        f"{QDRANT_PATH if QDRANT_MODE == 'embedded' else QDRANT_URL} / {COLLECTION_NAME}",  # noqa: F405
        file=sys.stderr,
    )
    print(f"[wiki] Graph: {'on' if GRAPH_DB_ENABLED else 'off'}", file=sys.stderr)  # noqa: F405


# Silence "unused import" — kept to preserve legacy ``import os``/``sys``
# access via ``llm_wiki.config.os`` if any caller relied on it.
_ = os

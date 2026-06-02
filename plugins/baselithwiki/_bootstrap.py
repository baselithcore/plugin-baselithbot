"""Import + environment bootstrap for the vendored ``llm_wiki`` engine.

The BaselithWiki plugin embeds the upstream *Wiki White-Label* engine
(`/Users/giovanni/dev/lavoro/llm-wiki-grafiphy`) **verbatim** under
``plugins/baselithwiki/llm_wiki`` and ``plugins/baselithwiki/_wiki_main.py``.

Two things must happen *before* ``llm_wiki.config`` is imported anywhere
(its module body reads ``os.getenv`` eagerly):

1. **sys.path** — make the vendored package importable as a top-level
   ``llm_wiki`` / ``_wiki_main`` without renaming a single source file.

2. **Environment isolation** — the host BaselithCore ``.env`` ships generic
   keys (``POSTGRES_ENABLED``, ``APP_DOMAIN``, ``AUTH_REQUIRED``, ``SECRET_KEY``
   …) whose names collide with the ones ``llm_wiki`` reads. Inheriting them
   verbatim would silently point the wiki engine at the *core* Postgres
   database (schema clash) or flip it out of setup mode. We therefore:

   * promote any ``BASELITHWIKI_<KEY>`` override to the bare ``<KEY>`` the
     engine expects (the operator's explicit, scoped opt-in channel), and
   * force the high-impact toggles to safe *setup-mode* defaults unless the
     operator opted in via that prefix.

This keeps the vendored source byte-identical: all coexistence logic lives
here in the wrapper, never in ``llm_wiki/``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent

#: Toggles that must NOT be inherited from the host environment. Each maps to
#: the value forced when no ``BASELITHWIKI_<KEY>`` override is present. This is
#: what pins the plugin to a self-contained "setup mode" out of the box.
_SETUP_MODE_DEFAULTS: dict[str, str] = {
    "APP_DOMAIN": "",
    "POSTGRES_ENABLED": "false",
    "AUTH_REQUIRED": "false",
}

_OVERRIDE_PREFIX = "BASELITHWIKI_"

_done = False


def _load_plugin_dotenv() -> None:
    """Load ``plugins/baselithwiki/.env`` if present (operator config file).

    The vendored engine's ``python-dotenv`` only reads a ``.env`` from the
    process CWD (the host repo root), so a plugin-local one would never be
    picked up. We load it here — *before* isolation — so its ``BASELITHWIKI_*``
    keys flow through the promotion + setup-mode logic below. Existing
    environment variables win (``override=False``) so deployment-time exports
    still take precedence over the committed file.
    """
    env_file = PLUGIN_DIR / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
    except Exception:  # noqa: BLE001 — missing python-dotenv must not break boot
        pass


def _apply_env_isolation() -> None:
    """Promote ``BASELITHWIKI_*`` overrides and pin setup-mode defaults.

    Idempotent. Any ``BASELITHWIKI_FOO=bar`` becomes ``FOO=bar`` for the
    vendored engine; the three setup-mode toggles fall back to their safe
    defaults when neither a prefixed override nor an explicit opt-in exists.
    """
    # 1. Promote scoped overrides (operator's explicit control channel).
    promoted: set[str] = set()
    for key, value in list(os.environ.items()):
        if key.startswith(_OVERRIDE_PREFIX):
            bare = key[len(_OVERRIDE_PREFIX) :]
            if bare:
                os.environ[bare] = value
                promoted.add(bare)

    # 2. Pin setup-mode defaults unless explicitly overridden above.
    for key, default in _SETUP_MODE_DEFAULTS.items():
        if key not in promoted:
            os.environ[key] = default


def ensure_ready() -> None:
    """Idempotently prepare ``sys.path`` and the isolated environment."""
    global _done
    if _done:
        return
    if str(PLUGIN_DIR) not in sys.path:
        # Append (not insert-0) so the host project keeps import priority;
        # ``llm_wiki`` / ``_wiki_main`` are unique names with no collision.
        sys.path.append(str(PLUGIN_DIR))
    _load_plugin_dotenv()
    _apply_env_isolation()
    _done = True

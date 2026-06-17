"""Import + environment bootstrap for the BaselithBrain plugin.

Two responsibilities, both idempotent and side-effect-safe so the plugin can
boot inside the host BaselithCore process without touching global state it does
not own:

1. **sys.path** — append the plugin dir so ``backend`` imports resolve as a
   first-class package without polluting the host namespace (appended, never
   inserted at 0, so host imports keep priority).

2. **Environment isolation** — promote any ``BASELITHBRAIN_<KEY>`` override to
   the bare ``<KEY>`` the local :mod:`config` settings reader expects, and pin
   safe local-first defaults. This keeps the plugin self-contained: it never
   inherits the host's generic ``.env`` keys, and it works out of the box with
   zero external infrastructure (notes live on local disk; the search/graph
   index is derived in-memory).

All coexistence logic lives here so the backend stays a clean, portable app.
"""

from __future__ import annotations

import os
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent

#: Default vault location when the operator sets no override. Local-first: the
#: Markdown files on disk are the single source of truth.
_DEFAULT_VAULT = PLUGIN_DIR / "vault"

_OVERRIDE_PREFIX = "BASELITHBRAIN_"

_done = False


def _load_plugin_dotenv() -> None:
    """Load ``plugins/baselithbrain/.env`` if present (operator config file).

    Existing process env wins (``override=False``) so deploy-time exports take
    precedence over the committed file. A missing ``python-dotenv`` must never
    break boot — the plugin has no hard dependency on it.
    """
    env_file = PLUGIN_DIR / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
    except Exception:  # noqa: BLE001 — optional convenience only
        pass


def _apply_env_isolation() -> None:
    """Promote ``BASELITHBRAIN_*`` overrides and pin local-first defaults."""
    for key, value in list(os.environ.items()):
        if key.startswith(_OVERRIDE_PREFIX):
            bare = key[len(_OVERRIDE_PREFIX) :]
            if bare:
                os.environ.setdefault(bare, value)

    # Pin the vault root to a self-contained, writable default unless the
    # operator opted into another location.
    os.environ.setdefault("VAULT_ROOT", str(_DEFAULT_VAULT))


def ensure_ready() -> None:
    """Idempotently prepare the isolated env and the vault directory.

    No ``sys.path`` manipulation: the backend is a subpackage imported
    relatively (``plugins.baselithbrain.backend``), so it never needs the
    plugin dir on the global path — which also avoids shadowing the repo-root
    ``backend.py`` / a top-level ``config`` module.
    """
    global _done
    if _done:
        return
    _load_plugin_dotenv()
    _apply_env_isolation()
    Path(os.environ["VAULT_ROOT"]).mkdir(parents=True, exist_ok=True)
    _done = True

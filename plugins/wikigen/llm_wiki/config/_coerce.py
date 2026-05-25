"""Env-var coercion helpers + dotenv bootstrap utilities.

Kept side-effect free except for ``_drop_stale_empty_inheritance`` and
``_warn_shell_env_conflicts``, both of which mutate or inspect
``os.environ`` and the on-disk ``.env`` respectively.
"""

from __future__ import annotations

import os
import sys

from dotenv import dotenv_values


def _str(key: str, default: str) -> str:
    raw = os.getenv(key)
    if raw is None:
        return default
    s = raw.strip()
    return s if s else default


def _optional_str(key: str) -> str | None:
    raw = os.getenv(key)
    if raw is None:
        return None
    s = raw.strip()
    return s or None


def _int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() not in {"false", "0", "no", "off", ""}


def _drop_stale_empty_inheritance(*keys: str) -> None:
    """Drop empty inherited env vars when ``.env`` has a real value.

    Forked uvicorn ``--reload`` workers inherit the parent's empty
    pre-wizard env; without this pre-clean they ignore the ``.env``
    edits the wizard wrote. Tests that explicitly set empty values
    bypass this via the pytest gate in ``__init__``.
    """
    try:
        file_values = dotenv_values()
    except Exception:
        return
    for k in keys:
        env_v = os.environ.get(k)
        if env_v is not None and not env_v.strip():
            file_v = (file_values.get(k) or "").strip()
            if file_v:
                del os.environ[k]


def _warn_shell_env_conflicts() -> None:
    """Log a loud warning if a shell-exported var differs from ``.env``.

    Diagnoses "wizard ran but I'm still on insurance" confusion:
    scaffold rewrites the file but a stale shell export beats it because
    dotenv defaults to ``override=False``.
    """
    try:
        env_file_values = dotenv_values()
    except Exception:
        return
    suspicious = ("APP_DOMAIN", "WIKI_ROOT", "LLM_VENDOR", "OLLAMA_MODEL", "OPENAI_MODEL")
    for key in suspicious:
        env_val = os.environ.get(key)
        file_val = env_file_values.get(key)
        if file_val is not None and env_val is not None and env_val != file_val:
            print(
                f"[wiki] WARNING: {key}={env_val!r} from shell overrides .env "
                f"value {file_val!r}. Run `unset {key}` then restart, or edit "
                f"the export, otherwise the scaffold wizard's choice is ignored.",
                file=sys.stderr,
            )

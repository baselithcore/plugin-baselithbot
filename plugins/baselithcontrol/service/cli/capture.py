"""Capture JSON emitted to stdout by a CLI command function.

Several framework CLI commands (``cache``/``db``) already emit machine-readable
JSON via ``print(json.dumps(...))`` when ``json_output=True``. Reusing them
verbatim keeps a single source of truth for destructive infra mutations (e.g.
``db reset`` deletes Qdrant collections + flushes Redis) instead of duplicating
that logic in the plugin.

``redirect_stdout`` is process-global, so calls are serialized behind a lock.
Callers must invoke this from a worker thread (``asyncio.to_thread``) — the CLI
functions do blocking socket/Redis I/O.
"""

from __future__ import annotations

import contextlib
import io
import json
import threading
from typing import Any, Callable

_lock = threading.Lock()


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the outermost JSON object out of captured stdout."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {"status": "error", "message": "no JSON output captured"}
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"could not parse CLI output: {exc}"}
    if not isinstance(obj, dict):
        return {"status": "error", "message": "unexpected CLI output shape"}
    return obj


def run_capturing_json(fn: Callable[[], Any]) -> dict[str, Any]:
    """Run ``fn`` (which prints JSON to stdout) and return the parsed object.

    Never raises: any failure is surfaced as an ``{"status": "error", ...}``
    payload so the route can map it onto a graceful response.
    """
    buffer = io.StringIO()
    with _lock:
        with contextlib.redirect_stdout(buffer):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 — surfaced as error payload
                return {"status": "error", "message": str(exc)}
    return _extract_json(buffer.getvalue())


__all__ = ["run_capturing_json"]

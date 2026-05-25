"""Vendor / model resolution + JSON payload parser."""

from __future__ import annotations

import json
import re
from typing import Any

from llm_wiki.admin.prompt_synthesizer.models import SynthesisError


def _synthesis_vendor() -> str:
    """Synthesis runs at scaffold-time and is conceptually an ingest task
    (planning quality on prompt body matters far more than chat latency).
    Inherit from ``INGEST_VENDOR`` so a hybrid Ollama-RAG / OpenAI-ingest
    deployment routes synthesis to the capable cloud model."""
    import os as _os

    from llm_wiki import config as _cfg

    return (
        _os.environ.get("INGEST_VENDOR")
        or _cfg.INGEST_VENDOR
        or _cfg.LLM_VENDOR
        or "ollama"
    ).lower()


def _resolve_synthesis_model() -> str:
    import os as _os

    from llm_wiki import config as _cfg_mod

    explicit = _os.environ.get("SYNTHESIS_MODEL") or _cfg_mod.SYNTHESIS_MODEL
    if explicit:
        return explicit
    vendor = _synthesis_vendor()
    if vendor == "openai":
        return (
            _os.environ.get("INGEST_OPENAI_MODEL")
            or _os.environ.get("OPENAI_MODEL")
            or _cfg_mod.OPENAI_MODEL
        )
    return _os.environ.get("INGEST_OLLAMA_MODEL") or _cfg_mod.INGEST_OLLAMA_MODEL


def _parse_json_payload(raw: str) -> dict[str, Any]:
    """Parse the LLM response. Tolerates code-fences and stray prefix."""
    cleaned = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    first = cleaned.find("{")
    if first > 0:
        cleaned = cleaned[first:]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SynthesisError(f"LLM output is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise SynthesisError(
            f"LLM output is not a JSON object (got {type(data).__name__})"
        )
    return data

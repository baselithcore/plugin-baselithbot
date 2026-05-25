"""Thin wrapper over :mod:`llm_wiki.utils.llm` adding:

- structured output via JSON schema (Ollama ``format=<schema>``,
  OpenAI ``response_format=json_schema``)
- retry with exponential backoff
- safe JSON parsing (tolerates ```json fences ```)

Why a separate client: ``utils/llm.generate()`` only exposes
``json_mode: bool`` which on Ollama maps to ``format="json"``.
Ollama 0.5+ supports **JSON schema constrained** decoding (``format=<dict>``)
giving 100% parsable output — much better for this pipeline. On
OpenAI-compatible endpoints this maps to ``response_format=json_schema``.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from llm_wiki import config as _config
from llm_wiki.config import (
    INGEST_MAX_CONCURRENT,
    INGEST_OLLAMA_NUM_CTX,
    LLM_KEEP_ALIVE,
)
from llm_wiki.utils.llm import _ollama_client, _openai_client  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

# Global semaphore: serialize Ollama calls across worker threads. Single-model
# inference is GPU/CPU-bound — N parallel requests queue inside the daemon and
# the late ones timeout before they're served. Cap concurrency here instead.
_LLM_SEMAPHORE = threading.BoundedSemaphore(value=INGEST_MAX_CONCURRENT)

T = TypeVar("T", bound=BaseModel)


def _ollama_options(temperature: float) -> dict[str, Any]:
    """Costruisce le `options` Ollama, inclusi `num_ctx` se configurato.

    Senza `num_ctx` esplicito Ollama usa 2048 e tronca silenziosamente
    prompt più lunghi → output incoerente. Vedi `INGEST_OLLAMA_NUM_CTX`.
    """
    opts: dict[str, Any] = {"temperature": temperature}
    if INGEST_OLLAMA_NUM_CTX > 0:
        opts["num_ctx"] = INGEST_OLLAMA_NUM_CTX
    return opts


def generate_structured(
    schema: type[T],
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_retries: int = 3,
    temperature: float = 0.1,
) -> T:
    model_id = model or (
        _config.INGEST_OPENAI_MODEL
        if _config.INGEST_VENDOR == "openai"
        else _config.INGEST_OLLAMA_MODEL
    )
    schema_dict = schema.model_json_schema()
    last_err: Exception | None = None
    prompt_chars = sum(len(str(m.get("content", ""))) for m in messages)
    logger.info(
        "generate_structured: model=%s schema=%s prompt_chars=%d",
        model_id,
        schema.__name__,
        prompt_chars,
    )

    # `loose_json` flips the call from grammar-constrained
    # (`format=<schema>`) to plain `format="json"`. Schema-constrained
    # decoding on Ollama is 2-4x slower than free JSON because every token
    # is constrained against the grammar. Default by vendor (`INGEST_LOOSE_JSON`):
    # Ollama → True (speed wins, retry handles parse failures); OpenAI → False
    # (`response_format=json_schema` is fast and reliable). Timeout fallback
    # below still flips to loose if a strict-mode call exceeds the deadline.
    loose_json = _config.INGEST_LOOSE_JSON
    timeout_count = 0
    base_messages = list(messages)
    last_raw: str = ""
    for attempt in range(1, max_retries + 1):
        try:
            raw = _call_json(
                messages=messages,
                model=model_id,
                schema=schema_dict,
                temperature=temperature,
                loose_json=loose_json,
            )
            last_raw = raw
            parsed = _parse_json(raw)
            return schema.model_validate(parsed)
        except (ValidationError, json.JSONDecodeError) as exc:
            last_err = exc
            feedback = _format_repair_feedback(exc, raw=last_raw, schema=schema_dict)
            # First line for human scan; full feedback at DEBUG for
            # post-mortem (which field / type / path the LLM got wrong).
            logger.warning(
                "generate_structured attempt %d failed (%s) — schema=%s — repair feedback: %s",
                attempt,
                type(exc).__name__,
                schema.__name__,
                feedback.splitlines()[0] if feedback else "n/a",
            )
            logger.debug("generate_structured full repair feedback:\n%s", feedback)
            # Bound conversation growth: keep only base_messages + last
            # assistant raw + new structured feedback. Senza questo cap
            # ogni round aggiunge ~500-2000 char e la 3a iter sfora num_ctx.
            messages = [
                *base_messages,
                {"role": "assistant", "content": last_raw[:4000] if last_raw else ""},
                {"role": "user", "content": feedback},
            ]
            time.sleep(0.5 * attempt)
        except Exception as exc:
            last_err = exc
            if _is_timeout(exc):
                timeout_count += 1
                logger.warning(
                    "generate_structured TIMEOUT #%d (prompt_chars=%d, loose=%s): %s",
                    timeout_count,
                    prompt_chars,
                    loose_json,
                    exc,
                )
                if timeout_count == 1 and not loose_json:
                    # First timeout: drop grammar-constrained decoding and try
                    # again. Faster path; parsing tolerates fences via _parse_json.
                    loose_json = True
                    logger.info("retrying without schema constraint (format='json')")
                    time.sleep(0.5)
                    continue
                raise RuntimeError(
                    f"LLM timeout on {prompt_chars}-char prompt. Raise LLM_TIMEOUT, "
                    f"reduce INGEST_MAX_CONCURRENT, use a faster model, "
                    f"or shrink the prompt. Original: {exc}"
                ) from exc
            logger.warning("generate_structured attempt %d error: %s", attempt, exc)
            time.sleep(0.5 * attempt)

    raise RuntimeError(f"generate_structured failed after {max_retries} attempts: {last_err}")


def _is_timeout(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return (
        "timeout" in name
        or "timed out" in msg
        or "timeout" in msg
        or "readtimeout" in name
        or "connecttimeout" in name
    )


def generate_text(
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    model_id = model or (
        _config.INGEST_OPENAI_MODEL
        if _config.INGEST_VENDOR == "openai"
        else _config.INGEST_OLLAMA_MODEL
    )
    if _config.INGEST_VENDOR == "openai":
        client = _openai_client()
        resp = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()
    client = _ollama_client()
    with _LLM_SEMAPHORE:
        try:
            resp = client.chat(
                model=model_id,
                messages=messages,
                options=_ollama_options(temperature),
                keep_alive=LLM_KEEP_ALIVE,
            )
        except TypeError:
            resp = client.chat(
                model=model_id,
                messages=messages,
                options=_ollama_options(temperature),
            )
    if isinstance(resp, dict):
        return (resp.get("message", {}).get("content") or "").strip()
    msg = getattr(resp, "message", None)
    return (getattr(msg, "content", "") or "").strip()


def _call_json(
    *,
    messages: list[dict[str, Any]],
    model: str,
    schema: dict[str, Any],
    temperature: float,
    loose_json: bool = False,
) -> str:
    if _config.INGEST_VENDOR == "openai":
        client = _openai_client()
        if loose_json:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        else:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.get("title", "Output"),
                        "strict": False,
                        "schema": schema,
                    },
                },
            )
        return resp.choices[0].message.content or ""

    client = _ollama_client()
    # `keep_alive` keeps the model resident across calls so the next ingest
    # job skips the 30-60s cold-load. Passed via kwargs so old SDKs ignore.
    base_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "options": _ollama_options(temperature),
        "keep_alive": LLM_KEEP_ALIVE,
    }
    # Serialize Ollama traffic: parallel worker threads otherwise queue on the
    # daemon and the late ones blow past LLM_TIMEOUT.
    fmt: Any = "json" if loose_json else schema
    with _LLM_SEMAPHORE:
        try:
            resp = client.chat(format=fmt, **base_kwargs)
        except TypeError:
            logger.info("ollama SDK too old: falling back to format='json' (no keep_alive)")
            resp = client.chat(
                model=model,
                messages=messages,
                format="json",
                options=_ollama_options(temperature),
            )

    if isinstance(resp, dict):
        return resp.get("message", {}).get("content", "") or ""
    msg = getattr(resp, "message", None)
    return getattr(msg, "content", "") or ""


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _format_repair_feedback(exc: Exception, *, raw: str, schema: dict[str, Any]) -> str:
    """Genera feedback strutturato per il repair-loop LLM.

    Per :class:`ValidationError` enumera i field invalidi (path + tipo +
    messaggio + valore offendente), così il modello sa esattamente cosa
    correggere — niente "rigenera tutto, era sbagliato". Per
    :class:`JSONDecodeError` mostra la finestra di testo intorno alla
    posizione dell'errore.

    Output sempre in italiano (coerente con istruzioni.md / pack
    italiano-only) e termina con il nome dello schema atteso, così il
    modello ri-aggancia il contratto se ha derivato.
    """
    schema_name = schema.get("title", "schema")
    if isinstance(exc, ValidationError):
        lines = [
            "L'output JSON precedente non rispetta lo schema. Errori per campo:",
            "",
        ]
        for err in exc.errors()[:8]:  # cap: oltre 8 il prompt esplode
            loc = ".".join(str(p) for p in err.get("loc", ())) or "<root>"
            etype = err.get("type", "?")
            msg = err.get("msg", "")
            inp = err.get("input")
            inp_repr = repr(inp)
            if len(inp_repr) > 120:
                inp_repr = inp_repr[:117] + "…"
            lines.append(f"- `{loc}` ({etype}): {msg}. Valore ricevuto: {inp_repr}")
        lines.extend(
            [
                "",
                f"Rigenera SOLO l'oggetto JSON conforme allo schema `{schema_name}`.",
                "Mantieni i valori già corretti, correggi unicamente i campi elencati sopra.",
                "Niente preambolo, niente code fence: la prima riga deve iniziare con `{`.",
            ]
        )
        return "\n".join(lines)

    if isinstance(exc, json.JSONDecodeError):
        pos = exc.pos if hasattr(exc, "pos") else 0
        snippet = raw[max(0, pos - 80) : pos + 80] if raw else ""
        return (
            "L'output non è JSON parsabile.\n"
            f"Errore: {exc.msg} alla posizione {pos}.\n"
            f"Contesto attorno all'errore: …{snippet}…\n"
            f"Rigenera SOLO un oggetto JSON valido conforme allo schema "
            f"`{schema_name}`. Niente preambolo, niente fence."
        )

    return (
        f"L'output precedente ha generato un errore: {exc}. "
        f"Rigenera SOLO l'oggetto JSON conforme allo schema `{schema_name}`."
    )


def _parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        return json.loads(text)
    m = _JSON_FENCE_RE.search(text)
    if m:
        return json.loads(m.group(1).strip())
    raise json.JSONDecodeError("No JSON object found", text, 0)

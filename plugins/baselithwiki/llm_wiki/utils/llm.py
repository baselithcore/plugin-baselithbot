"""Dispatcher LLM unificato per Ollama / OpenAI-compatibile.

Pattern derivato da `graphrag/utils/llm.py`. La scelta di parlare OpenAI-compat
(tramite `openai.Client(base_url=...)`) garantisce che lo stesso codice lavori
contro: Ollama (/v1), LM Studio, llama.cpp-server, vLLM, llamafile, OpenAI.

Ollama ha inoltre un SDK nativo che usiamo quando `LLM_VENDOR=ollama` perché
espone in modo più pulito tool-calling e streaming granulare.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Generator
from typing import Any

from llm_wiki import config as _config
from llm_wiki.config import (
    LLM_CACHE_TTL,
    LLM_KEEP_ALIVE,
    LLM_TIMEOUT,
)
from llm_wiki.utils.cache import TTLCache

logger = logging.getLogger(__name__)

_LLM_CACHE: TTLCache[str, str] = TTLCache(maxsize=512, ttl=LLM_CACHE_TTL)
_client_cache: dict[str, Any] = {}


# --- client factories -------------------------------------------------------


def _current_ollama_url() -> str:
    import os as _os

    return _os.environ.get("OLLAMA_URL") or _config.OLLAMA_URL


def _current_openai_key() -> str:
    import os as _os

    return _os.environ.get("OPENAI_API_KEY") or _config.OPENAI_API_KEY or ""


def _current_openai_base() -> str:
    import os as _os

    return _os.environ.get("OPENAI_API_BASE") or _config.OPENAI_API_BASE


def _ollama_client() -> Any:
    url = _current_ollama_url()
    cached = _client_cache.get("ollama")
    if cached is not None and _client_cache.get("ollama_url") == url:
        return cached
    try:
        import ollama

        try:
            client = ollama.Client(host=url, timeout=LLM_TIMEOUT)
        except TypeError:
            # versioni vecchie non accettano timeout nel costruttore
            client = ollama.Client(host=url)
    except ImportError as exc:
        raise RuntimeError(
            "Pacchetto `ollama` non installato. `pip install ollama`."
        ) from exc
    _client_cache["ollama"] = client
    _client_cache["ollama_url"] = url
    return client


def _openai_client() -> Any:
    key = _current_openai_key()
    base = _current_openai_base()
    cached = _client_cache.get("openai")
    if (
        cached is not None
        and _client_cache.get("openai_key") == key
        and _client_cache.get("openai_base") == base
    ):
        return cached
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=key or "sk-placeholder",
            base_url=base,
            timeout=LLM_TIMEOUT,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Pacchetto `openai` non installato. `pip install openai`."
        ) from exc
    _client_cache["openai"] = client
    _client_cache["openai_key"] = key
    _client_cache["openai_base"] = base
    return client


def reset_clients() -> None:
    """Drop cached LLM clients so the next call rebuilds with fresh env.

    Used by scaffold after writing provider keys to ``.env`` and syncing
    them into ``os.environ`` — without this, in-process callers (prompt
    synthesizer, ingest workers running in the same process before the
    restart) keep talking to the old vendor.
    """
    _client_cache.clear()


# --- cache helpers ----------------------------------------------------------


def _cache_key(
    messages: list[dict[str, Any]],
    model: str,
    json_mode: bool,
    options: dict[str, Any] | None = None,
) -> str:
    payload = json.dumps(
        {"m": model, "j": json_mode, "msgs": messages, "o": options or {}},
        ensure_ascii=False,
        sort_keys=True,
    )
    return "llm:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _openai_sampling_kwargs(options: dict[str, Any] | None) -> dict[str, Any]:
    """Traduce le opzioni stile Ollama in kwargs accettati da OpenAI-compat.

    ``num_predict`` → ``max_tokens``. ``temperature``/``top_p``/``seed``
    passano invariati. Altre chiavi (top_k, repeat_penalty, mirostat, ecc.)
    sono Ollama-only e vengono droppate silenziosamente in modalità OpenAI.
    """
    if not options:
        return {}
    out: dict[str, Any] = {}
    if "temperature" in options:
        out["temperature"] = options["temperature"]
    if "top_p" in options:
        out["top_p"] = options["top_p"]
    if "seed" in options:
        out["seed"] = options["seed"]
    np = options.get("num_predict")
    if isinstance(np, int) and np > 0:
        out["max_tokens"] = np
    return out


# --- public API -------------------------------------------------------------


def _resolve_vendor(override: str | None) -> str:
    """Pick the active vendor for the next ``utils.llm`` call.

    Precedence: explicit ``vendor=`` arg → ``RAG_VENDOR`` (post-refresh
    config constant, which falls back to ``LLM_VENDOR`` when unset).
    Shell-export of ``LLM_VENDOR`` is honoured via ``config.refresh_paths``
    (the wizard / admin endpoints call it after mutating env).
    """
    if override:
        return override.lower()
    return (_config.RAG_VENDOR or _config.LLM_VENDOR or "ollama").lower()


def generate(
    prompt: str | None = None,
    *,
    messages: list[dict[str, Any]] | None = None,
    model: str | None = None,
    json_mode: bool = False,
    use_cache: bool = True,
    options: dict[str, Any] | None = None,
    vendor: str | None = None,
) -> str:
    """Genera una risposta one-shot dal provider attivo (RAG di default).

    ``vendor`` esplicito → override (es. ingest che chiama utils.llm).
    Default = ``RAG_VENDOR`` (chat/RAG vendor, fallback ``LLM_VENDOR``).
    ``options`` mappa per-call sampling (``temperature``, ``top_p``,
    ``num_predict``, ``seed``, ecc.). Tradotta in ``options=`` per Ollama
    e ``temperature=``/``top_p=``/``max_tokens=`` per OpenAI-compat.
    Default = None: ciascun provider usa i propri default.
    """
    if prompt is None and not messages:
        raise ValueError("Fornire `prompt` o `messages`.")

    import os as _os

    vendor_id = _resolve_vendor(vendor)
    msgs = messages or [{"role": "user", "content": prompt or ""}]
    if model:
        model_id = model
    elif vendor_id == "openai":
        model_id = _os.environ.get("OPENAI_MODEL") or _config.OPENAI_MODEL
    else:
        model_id = _os.environ.get("OLLAMA_MODEL") or _config.OLLAMA_MODEL

    # Cache key include options: sampling diversi possono dare output diversi.
    key = _cache_key(msgs, model_id, json_mode, options=options) if use_cache else None
    if key:
        cached = _LLM_CACHE.get(key)
        if cached is not None:
            return cached

    if vendor_id == "openai":
        client = _openai_client()
        kwargs: dict[str, Any] = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        kwargs.update(_openai_sampling_kwargs(options))
        resp = client.chat.completions.create(model=model_id, messages=msgs, **kwargs)
        content = resp.choices[0].message.content or ""
    else:
        client = _ollama_client()
        kwargs = {}
        if json_mode:
            kwargs["format"] = "json"
        if options:
            kwargs["options"] = dict(options)
        # Pass keep_alive on every call so Ollama doesn't unload the model
        # between consecutive ingest steps (cold-load = 30-60s). Older
        # ollama-python versions don't accept the kwarg → fall back silently.
        try:
            resp = client.chat(
                model=model_id, messages=msgs, keep_alive=LLM_KEEP_ALIVE, **kwargs
            )
        except TypeError:
            resp = client.chat(model=model_id, messages=msgs, **kwargs)
        if isinstance(resp, dict):
            content = resp.get("message", {}).get("content", "")
        else:
            content = getattr(getattr(resp, "message", None), "content", "") or ""

    content = content.strip()
    if key and content:
        _LLM_CACHE.set(key, content)
    return content


def stream(
    prompt: str | None = None,
    *,
    messages: list[dict[str, Any]] | None = None,
    model: str | None = None,
    options: dict[str, Any] | None = None,
    vendor: str | None = None,
) -> Generator[str, None, None]:
    """Streaming token-by-token dal provider attivo. ``options`` come in :func:`generate`."""
    if prompt is None and not messages:
        raise ValueError("Fornire `prompt` o `messages`.")

    import os as _os

    vendor_id = _resolve_vendor(vendor)
    msgs = messages or [{"role": "user", "content": prompt or ""}]
    if model:
        model_id = model
    elif vendor_id == "openai":
        model_id = _os.environ.get("OPENAI_MODEL") or _config.OPENAI_MODEL
    else:
        model_id = _os.environ.get("OLLAMA_MODEL") or _config.OLLAMA_MODEL

    if vendor_id == "openai":
        client = _openai_client()
        kwargs = _openai_sampling_kwargs(options)
        response = client.chat.completions.create(
            model=model_id, messages=msgs, stream=True, **kwargs
        )
        for chunk in response:
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                yield delta
    else:
        client = _ollama_client()
        ollama_kwargs: dict[str, Any] = {}
        if options:
            ollama_kwargs["options"] = dict(options)
        try:
            response = client.chat(
                model=model_id,
                messages=msgs,
                stream=True,
                keep_alive=LLM_KEEP_ALIVE,
                **ollama_kwargs,
            )
        except TypeError:
            response = client.chat(
                model=model_id, messages=msgs, stream=True, **ollama_kwargs
            )
        for chunk in response:
            if isinstance(chunk, dict):
                piece = chunk.get("message", {}).get("content", "")
            else:
                piece = getattr(getattr(chunk, "message", None), "content", "") or ""
            if piece:
                yield piece


def generate_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    model: str | None = None,
    vendor: str | None = None,
) -> Any:
    """Chiamata con tool-calling. Restituisce il messaggio assistant."""
    import os as _os

    vendor_id = _resolve_vendor(vendor)
    if model:
        model_id = model
    elif vendor_id == "openai":
        model_id = _os.environ.get("OPENAI_MODEL") or _config.OPENAI_MODEL
    else:
        model_id = _os.environ.get("OLLAMA_MODEL") or _config.OLLAMA_MODEL

    if vendor_id == "openai":
        client = _openai_client()
        resp = client.chat.completions.create(
            model=model_id, messages=messages, tools=tools, tool_choice="auto"
        )
        return resp.choices[0].message
    client = _ollama_client()
    try:
        resp = client.chat(
            model=model_id, messages=messages, tools=tools, keep_alive=LLM_KEEP_ALIVE
        )
    except TypeError:
        resp = client.chat(model=model_id, messages=messages, tools=tools)
    if isinstance(resp, dict):
        return resp.get("message", {})
    return getattr(resp, "message", {})


def warmup_llm(model: str | None = None) -> bool:
    """Pre-load the LLM into RAM so the first ingest call doesn't pay the
    30-60s cold-start. No-op for OpenAI (server-side, instant). For Ollama
    we issue a tiny prompt that triggers the model load; the `keep_alive`
    option keeps it resident afterwards.

    Returns True on success, False on any failure (logged, never raises).
    """
    if _config.LLM_VENDOR != "ollama":
        return True
    model_id = model or _config.OLLAMA_MODEL
    try:
        client = _ollama_client()
        try:
            client.chat(
                model=model_id,
                messages=[{"role": "user", "content": "ping"}],
                options={"temperature": 0.0, "num_predict": 1},
                keep_alive=LLM_KEEP_ALIVE,
            )
        except TypeError:
            client.chat(
                model=model_id,
                messages=[{"role": "user", "content": "ping"}],
                options={"temperature": 0.0, "num_predict": 1},
            )
        logger.info(
            "[warmup] LLM `%s` resident (keep_alive=%s)", model_id, LLM_KEEP_ALIVE
        )
        return True
    except Exception as exc:
        logger.warning("[warmup] LLM `%s` failed: %s", model_id, exc)
        return False


def embed_ollama(texts: list[str], model: str) -> list[list[float]]:
    """Genera embeddings via Ollama (usato se EMBEDDER_MODEL è servito da Ollama)."""
    client = _ollama_client()
    out: list[list[float]] = []
    for text in texts:
        resp = client.embeddings(model=model, prompt=text)
        if isinstance(resp, dict):
            emb = resp.get("embedding", [])
        else:
            emb = getattr(resp, "embedding", [])
        out.append(list(emb))
    return out

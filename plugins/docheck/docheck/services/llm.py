"""LLM client wrapper. Provider-agnostic OpenAI-compatible HTTP API.

Defaults to Ollama (http://127.0.0.1:11434/v1). Works with vLLM, llama.cpp
server, LM Studio, and any other OpenAI-compatible local runtime by changing
DOCHECK_LLM_BASE_URL / DOCHECK_LLM_PROVIDER.
"""

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from openai import AsyncOpenAI

from ..core.config import settings
from ..core.logging import log

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "local",
            timeout=httpx.Timeout(settings.llm_request_timeout_s),
        )
        log.info(
            "llm.client_init",
            provider=settings.llm_provider,
            base_url=settings.llm_base_url,
            primary_model=settings.llm_primary_model,
        )
    return _client


def _supports_native_json(provider: str) -> bool:
    # Ollama (>=0.1.34) and vLLM both expose `response_format=json_object`.
    return provider.lower() in {
        "ollama",
        "vllm",
        "openai",
        "openai-compatible",
        "lmstudio",
    }


async def chat_json(
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """Call LLM forcing JSON mode. Raises on parse failure."""
    client = get_client()
    chosen_model = model or settings.llm_primary_model
    kwargs: dict[str, Any] = {
        "model": chosen_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature
        if temperature is not None
        else settings.llm_temperature,
        "top_p": settings.llm_top_p,
        "max_tokens": max_tokens,
    }
    if _supports_native_json(settings.llm_provider):
        kwargs["response_format"] = {"type": "json_object"}

    started = time.perf_counter()
    try:
        res = await client.chat.completions.create(**kwargs)
    except Exception:
        log.exception(
            "llm.call_failed",
            model=chosen_model,
            mode="json",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        raise

    raw = res.choices[0].message.content or "{}"
    usage = getattr(res, "usage", None)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    log.debug(
        "llm.call",
        model=chosen_model,
        mode="json",
        duration_ms=duration_ms,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
        finish_reason=res.choices[0].finish_reason,
        response_chars=len(raw),
    )
    try:
        result: dict[str, Any] = json.loads(raw)
        return result
    except json.JSONDecodeError as exc:
        log.error(
            "llm.json_decode_failed",
            model=chosen_model,
            error=str(exc),
            error_pos=exc.pos,
            raw_len=len(raw),
            raw_head=raw[:400],
            raw_tail=raw[-200:] if len(raw) > 400 else None,
            finish_reason=res.choices[0].finish_reason,
        )
        raise


async def chat_json_resilient(
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 4096,
    repair_max_tokens: int | None = None,
) -> dict[str, Any]:
    """Resilient JSON call. On parse failure: 1 repair retry, then raise.

    Repair stage asks the model to fix its previous malformed output. Useful
    against truncation (`finish_reason=length`) and stray tokens.
    """
    try:
        return await chat_json(
            system=system,
            user=user,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except json.JSONDecodeError as exc:
        log.warning(
            "llm.repair_attempt",
            error=str(exc),
            error_pos=exc.pos,
            raw_head=(exc.doc or "")[:200],
        )
        repair_user = (
            "Fix the following malformed JSON. Output ONLY valid JSON, "
            "preserving original semantics. Close any unterminated strings.\n\n"
            f"BROKEN:\n{(exc.doc or '')[:6000]}"
        )
        return await chat_json(
            system="You are a strict JSON repair tool. Output valid JSON only.",
            user=repair_user,
            model=model,
            temperature=0.0,
            max_tokens=repair_max_tokens or max_tokens,
        )


async def chat_text_stream(
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """Stream plain text completion token-by-token via OpenAI-compatible SSE.

    Yields content deltas as they arrive. Caller is responsible for accumulating
    the full text and closing semantics (e.g. emitting a `done` event).
    """
    client = get_client()
    chosen_model = model or settings.llm_primary_model
    started = time.perf_counter()
    try:
        stream = await client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature
            if temperature is not None
            else settings.llm_temperature,
            top_p=settings.llm_top_p,
            max_tokens=max_tokens,
            stream=True,
        )
    except Exception:
        log.exception(
            "llm.stream_open_failed",
            model=chosen_model,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        raise

    total_chars = 0
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            total_chars += len(delta)
            yield delta
    log.debug(
        "llm.stream_done",
        model=chosen_model,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        response_chars=total_chars,
    )


async def chat_text(
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 4096,
) -> str:
    """Plain text completion. Used for free-form extraction prompts."""
    client = get_client()
    res = await client.chat.completions.create(
        model=model or settings.llm_primary_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature
        if temperature is not None
        else settings.llm_temperature,
        top_p=settings.llm_top_p,
        max_tokens=max_tokens,
    )
    return res.choices[0].message.content or ""

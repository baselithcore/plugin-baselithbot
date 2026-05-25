import logging
import os
import sys

import ollama
import openai

from agent_jira.cache import TTLCache
from agent_jira.cost_control import BudgetExceededError, cost_controller
from agent_jira.config import (
    OLLAMA_API_BASE,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
    OPENAI_ENABLED,
    OPENAI_MODEL,
)

logger = logging.getLogger(__name__)


def _resolve_client():
    """Restituisce un client LLM (Ollama o OpenAI) in base alla configurazione."""
    if OPENAI_ENABLED:
        if not OPENAI_API_KEY:
            print(
                "❌ ERRORE: OpenAI abilitato ma OPENAI_API_KEY mancante!",
                file=sys.stderr,
            )
            return None
        return openai.Client(api_key=OPENAI_API_KEY)

    # Fallback su Ollama
    base_url = OLLAMA_API_BASE or os.environ.get("OLLAMA_HOST")
    if base_url:
        try:
            return ollama.Client(host=base_url)
        except AttributeError:
            os.environ["OLLAMA_HOST"] = base_url
    return None


_LLM_CLIENT = _resolve_client()


def _estimate_tokens(text: str) -> int:
    """Stima approssimativa token (1 token ~ 4 chars)."""
    if not text:
        return 0
    return len(text) // 4


# In-memory Semantic Cache (max 1000 items, TTL 1 hour)
_LLM_CACHE = TTLCache(maxsize=1000, ttl=3600.0)


def generate_response(prompt: str, model: str = None, json: bool = False) -> str:
    """
    Genera una risposta dal modello LLM (Ollama o OpenAI).
    Utilizza una cache semantica (chiave=prompt+model) per evitare chiamate ripetute.
    """
    # 0. Check Semantic Cache
    cache_key = f"{model or 'default'}:{json}:{prompt}"
    cached = _LLM_CACHE.get(cache_key)
    if cached:
        logger.info("🧠 Semantic Cache Hit for prompt fragment: '%s...'", prompt[:30])
        # We still verify budget/rate limits logic?
        # Usually semantic cache bypasses cost, but we should probably track it as '0 cost' or skipped.
        return cached

    # Track input tokens (estimated)
    cost_controller.track_tokens(_estimate_tokens(prompt), model="input")

    try:
        content = ""
        usage_tokens = 0

        if OPENAI_ENABLED:
            model_to_use = model or OPENAI_MODEL
            if _LLM_CLIENT is None:
                return "❌ Errore: Client OpenAI non inizializzato (manca API Key?)"

            kwargs = {}
            if json:
                kwargs["response_format"] = {"type": "json_object"}

            response = _LLM_CLIENT.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            content = response.choices[0].message.content.strip()

            # Use exact usage if available
            if response.usage:
                usage_tokens = response.usage.total_tokens
            else:
                usage_tokens = _estimate_tokens(content)

        else:
            # Ollama Logic
            model_to_use = model or OLLAMA_MODEL
            kwargs = {}
            if json:
                kwargs["format"] = "json"
            kwargs["think"] = False

            if _LLM_CLIENT is not None:
                response = _LLM_CLIENT.chat(
                    model=model_to_use,
                    messages=[{"role": "user", "content": prompt}],
                    **kwargs,
                )
            else:
                response = ollama.chat(
                    model=model_to_use,
                    messages=[{"role": "user", "content": prompt}],
                    **kwargs,
                )

            # Ollama returns dict or object (depending on version)
            if isinstance(response, dict):
                content = response["message"]["content"].strip()
                # Try to get eval_count + prompt_eval_count
                eval_count = response.get("eval_count", 0)
                prompt_eval = response.get("prompt_eval_count", 0)
                if eval_count > 0 or prompt_eval > 0:
                    usage_tokens = eval_count + prompt_eval
                else:
                    usage_tokens = _estimate_tokens(content)
            elif hasattr(response, "message"):
                # New Ollama API returns objects with attributes
                content = (
                    response.message.content.strip()
                    if hasattr(response.message, "content")
                    else str(response.message)
                )
                # Try to get token counts from response attributes
                eval_count = getattr(response, "eval_count", 0) or 0
                prompt_eval = getattr(response, "prompt_eval_count", 0) or 0
                if eval_count > 0 or prompt_eval > 0:
                    usage_tokens = eval_count + prompt_eval
                else:
                    usage_tokens = _estimate_tokens(content)
            else:
                # Fallback: convert to string
                content = str(response)
                usage_tokens = _estimate_tokens(content)

        # Track total/output tokens (if exact usage found, we prefer that, otherwise estimate output)
        output_tokens = 0
        if OPENAI_ENABLED and "response" in locals() and response.usage:
            output_tokens = response.usage.completion_tokens
        elif (
            not OPENAI_ENABLED and "response" in locals() and isinstance(response, dict)
        ):
            output_tokens = response.get("eval_count", _estimate_tokens(content))
        else:
            output_tokens = _estimate_tokens(content)

        cost_controller.track_tokens(output_tokens, model=model_to_use)

        # Store in Semantic Cache
        _LLM_CACHE.set(cache_key, content)

        return content

    except BudgetExceededError:
        raise
    except Exception as e:
        provider = "OpenAI" if OPENAI_ENABLED else "Ollama"
        logger.error(f"Errore chiamando {provider}: {e}")
        raise


def generate_response_stream(prompt: str, model: str = None):
    """Genera una risposta streaming dal modello LLM (Ollama o OpenAI)."""
    # Track input
    cost_controller.track_tokens(_estimate_tokens(prompt), model="input_stream")

    try:
        accumulated_content = ""

        if OPENAI_ENABLED:
            model_to_use = model or OPENAI_MODEL
            if _LLM_CLIENT is None:
                yield "❌ Errore: Client OpenAI non inizializzato"
                return

            stream = _LLM_CLIENT.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                if content:
                    accumulated_content += content
                    yield content
        else:
            # Ollama Logic
            model_to_use = model or OLLAMA_MODEL
            if _LLM_CLIENT is not None:
                stream = _LLM_CLIENT.chat(
                    model=model_to_use,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    think=False,
                )
            else:
                stream = ollama.chat(
                    model=model_to_use,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    think=False,
                )

            for chunk in stream:
                # Handle both dict and object responses
                if isinstance(chunk, dict):
                    content = chunk.get("message", {}).get("content", "")
                elif hasattr(chunk, "message"):
                    content = (
                        chunk.message.content
                        if hasattr(chunk.message, "content")
                        else ""
                    )
                else:
                    content = ""

                if content:
                    accumulated_content += content
                    yield content

        # Track output total at the end of stream
        cost_controller.track_tokens(
            _estimate_tokens(accumulated_content), model="output_stream"
        )

    except BudgetExceededError:
        raise
    except Exception as e:
        provider = "OpenAI" if OPENAI_ENABLED else "Ollama"
        logger.error(f"Errore chiamando {provider}: {e}")
        raise

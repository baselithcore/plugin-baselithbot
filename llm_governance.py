"""Central LLM-governance overlay for the dbview Node child.

dbview's NL→Query engine runs inside the vendored Node child, which reads its
LLM routing from process env (``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` /
``OLLAMA_BASE_URL`` + per-role model vars — see
``dbview/apps/api/src/nl2sql/llm/factory.ts``). When the BaselithCore host has
an operator-pinned per-plugin LLM policy for ``dbview`` (set from the auth
console), this module translates that pin into child env **overrides** applied
at every spawn: the historical env passthrough stays intact and governed
values simply win over it. Unpinned → no overrides, behaviour identical to an
ungoverned deployment. Never raises — governance must not break child spawn.

Two independent scopes (``manifest.yaml`` ``llm_scopes``):

* ``nl2sql`` — the NL→Query translation pipeline (per-dialect-kind models);
* ``explain`` — the explain/summarize pipeline (``*_MODEL_EXPLAIN``).

Either scope with no pin of its own inherits the plugin default pin (resolved
centrally by ``resolve_governed_client_config``), then the child's own env —
so a single default pin governs both pipelines.

What governance overrides:

* **Credentials + endpoint** for each governed provider — whichever scope
  routes to a provider supplies that provider's central key/base
  (``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` / ``OLLAMA_BASE_URL``; the child
  normalises the Ollama base's ``/api`` suffix itself).
* **The default model** per pipeline: a pinned model replaces the child's
  per-role default-model env vars for that scope (a pin is governance, not a
  hint). A pin without a model governs provider/credentials only.

What it deliberately leaves alone: the **per-request** provider/model the
dbview UI sends (``req.provider`` / ``req.model``) and per-user BYOK stored
credentials — explicit caller choices are a product feature, matching the
framework precedent (see ``core.services.llm.governed``). Only ``openai``,
``anthropic`` and ``ollama`` pins are honoured — the child bundles SDKs for
exactly those three; a ``huggingface`` pin is ignored.

Two propagation paths, live-first:

* **Live (no restart)** — the proxy (:mod:`plugins.dbview.proxy_router`) also
  resolves the pin **per request** via :func:`governed_request_headers` and
  forwards it to the running child as trusted ``x-dbview-gov-*`` headers, which
  the Node engine prefers over its spawn env. A re-pin therefore takes effect
  within the policy-snapshot TTL with no respawn. The proxy strips any inbound
  copy of these headers, so a client can never spoof the pinned routing.
* **Spawn env (fallback)** — :func:`governed_child_env` resolves the pin at
  every child (re)spawn (see ``SupervisorConfig.env_provider``), covering
  requests that do not traverse the proxy and giving a crash-restart the
  current pin.
"""

from __future__ import annotations

import logging

from core.services.llm.governed import (
    GovernedClientConfig,
    resolve_governed_client_config,
)

logger = logging.getLogger(__name__)

_PLUGIN_NAME = "dbview"
# Providers the vendored Node child bundles an SDK for.
_SERVEABLE = frozenset({"openai", "anthropic", "ollama"})
# Declared LLM scopes (must match manifest.yaml ``llm_scopes`` ids).
NL2SQL_SCOPE = "nl2sql"
EXPLAIN_SCOPE = "explain"

# Child env vars holding the default model per NL→Query dialect kind
# (factory.ts DEFAULT_OLLAMA_MODEL_BY_KIND). A governed ollama model replaces
# all of them — the per-request explicit model from the UI still wins.
_OLLAMA_KIND_MODEL_VARS: tuple[str, ...] = (
    "OLLAMA_MODEL_SQL",
    "OLLAMA_MODEL_GRAPH",
    "OLLAMA_MODEL_DOCUMENT",
    "OLLAMA_MODEL_VECTOR",
    "OLLAMA_MODEL_KEYVALUE",
    "OLLAMA_MODEL_SEARCH",
    "OLLAMA_MODEL_SAAS",
)

# Default-model env var per provider, per scope (factory.ts).
_MODEL_VARS: dict[str, dict[str, tuple[str, ...]]] = {
    NL2SQL_SCOPE: {
        "ollama": _OLLAMA_KIND_MODEL_VARS,
        "openai": ("OPENAI_MODEL",),
        "anthropic": ("ANTHROPIC_MODEL",),
    },
    EXPLAIN_SCOPE: {
        "ollama": ("OLLAMA_MODEL_EXPLAIN",),
        "openai": ("OPENAI_MODEL_EXPLAIN",),
        "anthropic": ("ANTHROPIC_MODEL_EXPLAIN",),
    },
}


def _governed(scope: str) -> GovernedClientConfig | None:
    """Governed routing for dbview at *scope*, or ``None`` to keep child env.

    A declared scope with no pin of its own falls back to the plugin default
    pin (handled centrally in ``resolve_governed_client_config``).
    """
    gov = resolve_governed_client_config(_PLUGIN_NAME, scope)
    if gov is None or gov.provider not in _SERVEABLE:
        return None
    return gov


def _credential_env(gov: GovernedClientConfig) -> dict[str, str]:
    """Central credential/endpoint env for *gov*'s provider."""
    env: dict[str, str] = {}
    if gov.provider == "ollama":
        if gov.api_base:
            env["OLLAMA_BASE_URL"] = gov.api_base
        return env
    key = gov.key()
    if key:
        env["OPENAI_API_KEY" if gov.provider == "openai" else "ANTHROPIC_API_KEY"] = key
    return env


# Env var the child reads to know a scope's pin is *enforced* (must win over
# the per-request provider/model and per-user BYOK, and hide the UI controls).
# Keyed by scope: ``DBVIEW_LLM_ENFORCED_NL2SQL`` / ``DBVIEW_LLM_ENFORCED_EXPLAIN``.
_ENFORCED_ENV_VAR: dict[str, str] = {
    NL2SQL_SCOPE: "DBVIEW_LLM_ENFORCED_NL2SQL",
    EXPLAIN_SCOPE: "DBVIEW_LLM_ENFORCED_EXPLAIN",
}


# --- live per-request propagation (proxy → child headers) -------------------
#
# ``governed_child_env`` only reaches the child at *spawn*, so a re-pin needs a
# child respawn to take effect. The proxy (:mod:`plugins.dbview.proxy_router`)
# additionally resolves the pin **per request** and forwards it to the running
# child as trusted headers, which the Node engine prefers over its spawn env —
# so a re-pin propagates live (within the policy snapshot TTL) with no restart.
# The proxy strips any inbound copy of these so a client can never spoof them.
_H_NL2SQL_PROVIDER = "x-dbview-gov-nl2sql-provider"
_H_NL2SQL_MODEL = "x-dbview-gov-nl2sql-model"
_H_EXPLAIN_PROVIDER = "x-dbview-gov-explain-provider"
_H_EXPLAIN_MODEL = "x-dbview-gov-explain-model"
_H_OPENAI_KEY = "x-dbview-gov-openai-key"
_H_ANTHROPIC_KEY = "x-dbview-gov-anthropic-key"
_H_OLLAMA_BASE = "x-dbview-gov-ollama-base"

#: Every governance request header — the proxy strips all inbound copies.
GOV_REQUEST_HEADERS: frozenset[str] = frozenset(
    {
        _H_NL2SQL_PROVIDER,
        _H_NL2SQL_MODEL,
        _H_EXPLAIN_PROVIDER,
        _H_EXPLAIN_MODEL,
        _H_OPENAI_KEY,
        _H_ANTHROPIC_KEY,
        _H_OLLAMA_BASE,
    }
)

_SCOPE_HEADERS: tuple[tuple[str, str, str], ...] = (
    (NL2SQL_SCOPE, _H_NL2SQL_PROVIDER, _H_NL2SQL_MODEL),
    (EXPLAIN_SCOPE, _H_EXPLAIN_PROVIDER, _H_EXPLAIN_MODEL),
)


def governed_request_headers() -> dict[str, str]:
    """Per-request governance headers for the current dbview LLM pin (may be empty).

    Resolved **live** on every proxied request, so a re-pin propagates to the
    already-running child without a respawn. Emits, per governed scope, the
    enforced provider + model, plus the central credential/endpoint for that
    provider. Cheap and total: any resolution failure degrades to ``{}`` — the
    child then falls back to its spawn env, exactly as before.
    """
    try:
        headers: dict[str, str] = {}
        for scope, provider_h, model_h in _SCOPE_HEADERS:
            gov = _governed(scope)
            if gov is None:
                continue
            headers[provider_h] = gov.provider
            if gov.model:
                headers[model_h] = gov.model
            headers.update(_credential_headers(gov))
        return headers
    except Exception:  # noqa: BLE001 — governance must never break the proxy
        logger.warning(
            "[dbview] governed LLM request-header resolution failed — the child "
            "falls back to its spawn env",
            exc_info=True,
        )
        return {}


def _credential_headers(gov: GovernedClientConfig) -> dict[str, str]:
    """Central credential/endpoint header for *gov*'s provider."""
    if gov.provider == "ollama":
        return {_H_OLLAMA_BASE: gov.api_base} if gov.api_base else {}
    key = gov.key()
    if not key:
        return {}
    return {(_H_OPENAI_KEY if gov.provider == "openai" else _H_ANTHROPIC_KEY): key}


def governed_child_env() -> dict[str, str]:
    """Child env overrides for the operator's dbview LLM pin (may be empty).

    Called by the supervisor at every child spawn (after the passthrough env
    and the plugin's own ``extra_env``), so governed values always win.
    Cheap and total: any resolution failure degrades to ``{}`` — the child
    spawns with its own configuration, exactly as if unpinned.

    A pinned scope also emits ``DBVIEW_LLM_ENFORCED_<SCOPE>=<provider>`` so the
    Node engine enforces the pin over the per-request provider/model and any
    per-user BYOK credential, and the SPA hides the matching LLM controls.
    """
    try:
        env: dict[str, str] = {}
        for scope in (NL2SQL_SCOPE, EXPLAIN_SCOPE):
            gov = _governed(scope)
            if gov is None:
                continue
            env[_ENFORCED_ENV_VAR[scope]] = gov.provider
            env.update(_credential_env(gov))
            if gov.model:
                for var in _MODEL_VARS[scope][gov.provider]:
                    env[var] = gov.model
        if env:
            logger.info(
                "[dbview] applying governed LLM env overrides: %s",
                ", ".join(sorted(k for k in env if not k.endswith("_API_KEY"))),
            )
        return env
    except Exception:  # noqa: BLE001 — governance must never break child spawn
        logger.warning(
            "[dbview] governed LLM env resolution failed — spawning the child "
            "with its own configuration",
            exc_info=True,
        )
        return {}


__all__ = [
    "EXPLAIN_SCOPE",
    "GOV_REQUEST_HEADERS",
    "NL2SQL_SCOPE",
    "governed_child_env",
    "governed_request_headers",
]

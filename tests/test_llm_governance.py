"""Central LLM governance: dbview honours the per-plugin LLM pin.

Exercises :mod:`plugins.dbview.llm_governance` — the seam that translates the
operator's pin (auth console; scopes ``nl2sql``/``explain``) into env
overrides for the vendored Node child, while unpinned/unserviceable cases
yield **no** overrides (child keeps its own env, zero behaviour change).
"""

from __future__ import annotations

import pytest

from core.config.services import LLMConfig
from core.services.llm.policy import PluginLLMPolicy, set_plugin_llm_policy_resolver
from plugins.dbview import llm_governance
from plugins.dbview.llm_governance import (
    GOV_REQUEST_HEADERS,
    governed_child_env,
    governed_request_headers,
)

_OLLAMA_KIND_VARS = llm_governance._OLLAMA_KIND_MODEL_VARS

# Env that can leak host credentials into LLMConfig (fields with a
# validation_alias ignore same-named init kwargs, so scrub these first).
_LLM_ENV_VARS = (
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_API_BASE",
    "LLM_API_KEY",
    # Per-provider endpoint: it outranks ``LLM_API_BASE`` inside
    # ``core.services.llm.runtime.api_base_for``, so leaving it set pins every
    # Ollama route at the developer's own box. ``core/config/env.py`` pushes the
    # repo-root ``.env`` into ``os.environ`` at import, which is how it gets set
    # here at all — CI has no such file, which is why this only fails locally.
    "LLM_OLLAMA_API_BASE",
    # Last-resort fallback in the same resolver, and commonly exported
    # machine-wide by the Ollama CLI.
    "OLLAMA_HOST",
    "LLM_OPENAI_API_KEY",
    "LLM_ANTHROPIC_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "LLM_HUGGINGFACE_API_KEY",
    "HF_TOKEN",
)


@pytest.fixture(autouse=True)
def _hermetic_policy(monkeypatch):
    """Isolate the resolver and pin a deterministic central LLMConfig."""
    for var in _LLM_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    set_plugin_llm_policy_resolver(None)
    cfg = LLMConfig(
        provider="ollama",
        model="base-model",
        enable_cache=False,
        api_base="http://central-ollama:11434",
    )
    monkeypatch.setattr("core.services.llm.governed.get_llm_config", lambda: cfg)
    yield
    set_plugin_llm_policy_resolver(None)


def _pin(policies: dict[str | None, PluginLLMPolicy]) -> None:
    """Install a scope-aware resolver: ``{scope-or-None: policy}`` for dbview."""

    def resolver(name: str, scope: str | None = None) -> PluginLLMPolicy | None:
        if name != "dbview":
            return None
        return policies.get(scope)

    set_plugin_llm_policy_resolver(resolver)


def test_unpinned_yields_no_overrides():
    env = governed_child_env()
    assert env == {}
    # No pin ⇒ no enforcement signal ⇒ the child keeps per-request + BYOK.
    assert "DBVIEW_LLM_ENFORCED_NL2SQL" not in env
    assert "DBVIEW_LLM_ENFORCED_EXPLAIN" not in env


def test_default_ollama_pin_governs_both_scopes():
    _pin({None: PluginLLMPolicy(provider="ollama", model="llama3.1:8b")})
    env = governed_child_env()
    # Central endpoint + the pinned model as the default for every dialect
    # kind (nl2sql scope) and for the explain pipeline (inherited fallback).
    assert env["OLLAMA_BASE_URL"] == "http://central-ollama:11434"
    for var in _OLLAMA_KIND_VARS:
        assert env[var] == "llama3.1:8b"
    assert env["OLLAMA_MODEL_EXPLAIN"] == "llama3.1:8b"
    assert "OPENAI_API_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env
    # Both scopes are enforced on the pinned provider (child locks the UI +
    # overrides per-request/BYOK for each).
    assert env["DBVIEW_LLM_ENFORCED_NL2SQL"] == "ollama"
    assert env["DBVIEW_LLM_ENFORCED_EXPLAIN"] == "ollama"


def test_per_scope_pins_route_independently(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-central")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-central")
    cfg = LLMConfig(
        provider="ollama", model="base-model", enable_cache=False, api_base=None
    )
    monkeypatch.setattr("core.services.llm.governed.get_llm_config", lambda: cfg)
    _pin(
        {
            "nl2sql": PluginLLMPolicy(provider="openai", model="gpt-4o"),
            "explain": PluginLLMPolicy(provider="anthropic", model="claude-x"),
        }
    )
    env = governed_child_env()
    assert env["OPENAI_API_KEY"] == "sk-openai-central"
    assert env["OPENAI_MODEL"] == "gpt-4o"
    assert env["ANTHROPIC_API_KEY"] == "sk-anthropic-central"
    assert env["ANTHROPIC_MODEL_EXPLAIN"] == "claude-x"
    # The other scope's model vars stay untouched.
    assert "OPENAI_MODEL_EXPLAIN" not in env
    assert "ANTHROPIC_MODEL" not in env
    for var in _OLLAMA_KIND_VARS:
        assert var not in env
    # Each scope is enforced on its own provider — the UI locks translate to
    # openai and explain to anthropic independently.
    assert env["DBVIEW_LLM_ENFORCED_NL2SQL"] == "openai"
    assert env["DBVIEW_LLM_ENFORCED_EXPLAIN"] == "anthropic"


def test_unserviceable_pin_emits_no_enforcement_signal():
    # A provider the child can't serve is ignored — no override AND no
    # enforcement flag, so the UI keeps the per-user controls.
    _pin({None: PluginLLMPolicy(provider="huggingface", model="some-model")})
    env = governed_child_env()
    assert "DBVIEW_LLM_ENFORCED_NL2SQL" not in env
    assert "DBVIEW_LLM_ENFORCED_EXPLAIN" not in env


def test_same_provider_pin_without_model_inherits_central_default_model():
    # A same-provider pin with no model resolves to the central default model
    # (LLMConfig.model) — the funnel contract, mirrored by GovernedClientConfig.
    _pin({None: PluginLLMPolicy(provider="ollama", model=None)})
    env = governed_child_env()
    assert env["OLLAMA_BASE_URL"] == "http://central-ollama:11434"
    for var in (*_OLLAMA_KIND_VARS, "OLLAMA_MODEL_EXPLAIN"):
        assert env[var] == "base-model"


def test_unserviceable_provider_pin_is_ignored():
    # The Node child has no HuggingFace SDK → keep its own configuration.
    _pin({None: PluginLLMPolicy(provider="huggingface", model="some-model")})
    assert governed_child_env() == {}


def test_cross_provider_pin_without_model_is_dropped():
    # Central default provider is ollama; an openai pin without a model would
    # inherit a meaningless default model → dropped centrally, no overrides.
    _pin({None: PluginLLMPolicy(provider="openai", model=None)})
    assert governed_child_env() == {}


def test_resolver_failure_degrades_to_no_overrides():
    def exploding(name: str, scope: str | None = None) -> PluginLLMPolicy | None:
        raise RuntimeError("policy store down")

    set_plugin_llm_policy_resolver(exploding)
    assert governed_child_env() == {}


# --- live per-request headers (proxy → running child, no respawn) -----------


def test_request_headers_empty_when_unpinned():
    assert governed_request_headers() == {}


def test_request_headers_openai_pin_carries_provider_model_and_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-central")
    cfg = LLMConfig(
        provider="ollama", model="base-model", enable_cache=False, api_base=None
    )
    monkeypatch.setattr("core.services.llm.governed.get_llm_config", lambda: cfg)
    _pin({None: PluginLLMPolicy(provider="openai", model="gpt-4o-mini")})
    headers = governed_request_headers()
    # Both scopes inherit the default pin → both enforced live.
    assert headers["x-dbview-gov-nl2sql-provider"] == "openai"
    assert headers["x-dbview-gov-nl2sql-model"] == "gpt-4o-mini"
    assert headers["x-dbview-gov-explain-provider"] == "openai"
    assert headers["x-dbview-gov-explain-model"] == "gpt-4o-mini"
    assert headers["x-dbview-gov-openai-key"] == "sk-openai-central"


def test_request_headers_ollama_pin_carries_base_not_key():
    _pin({None: PluginLLMPolicy(provider="ollama", model="llama3.1:8b")})
    headers = governed_request_headers()
    assert headers["x-dbview-gov-nl2sql-provider"] == "ollama"
    assert headers["x-dbview-gov-ollama-base"] == "http://central-ollama:11434"
    assert "x-dbview-gov-openai-key" not in headers


def test_request_headers_per_scope_independent(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-central")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-central")
    cfg = LLMConfig(
        provider="ollama", model="base-model", enable_cache=False, api_base=None
    )
    monkeypatch.setattr("core.services.llm.governed.get_llm_config", lambda: cfg)
    _pin(
        {
            "nl2sql": PluginLLMPolicy(provider="openai", model="gpt-4o"),
            "explain": PluginLLMPolicy(provider="anthropic", model="claude-x"),
        }
    )
    headers = governed_request_headers()
    assert headers["x-dbview-gov-nl2sql-provider"] == "openai"
    assert headers["x-dbview-gov-nl2sql-model"] == "gpt-4o"
    assert headers["x-dbview-gov-explain-provider"] == "anthropic"
    assert headers["x-dbview-gov-explain-model"] == "claude-x"
    assert headers["x-dbview-gov-openai-key"] == "sk-openai-central"
    assert headers["x-dbview-gov-anthropic-key"] == "sk-anthropic-central"


def test_request_headers_are_all_in_the_proxy_strip_set():
    # Anti-spoof: every header the proxy mints must also be stripped inbound.
    assert GOV_REQUEST_HEADERS >= {
        "x-dbview-gov-nl2sql-provider",
        "x-dbview-gov-explain-provider",
        "x-dbview-gov-openai-key",
    }

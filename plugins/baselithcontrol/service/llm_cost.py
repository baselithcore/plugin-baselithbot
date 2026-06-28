"""Real per-plugin LLM usage/cost attribution for the dashboard.

The core runtime funnels every LLM token count through one module-level sink,
``core.services.llm.service._report_tokens_to_middleware(count, model)`` — input
tokens are reported with ``model="input"`` / ``"input_stream"`` and output tokens
with the real model id. We **wrap that sink at runtime** (no core source edit, so
the Sacred-Core boundary and the architecture gate stay intact) to also record
usage into a process-wide ledger, attributed to the plugin that is serving the
current request.

Attribution rides a context var (:data:`current_plugin`) set by the per-plugin
ASGI meter (:mod:`plugin_meter`) — the same path→plugin matcher used for request
telemetry — so it stays request-scoped and never trusts client input. LLM calls
made outside a plugin-attributed HTTP request (background tasks, core routes) are
grouped under ``"unbound"``. Cost is a **list-price estimate** from
``core.models.pricing`` (core does not expose provider-billed cost); the token
counts themselves are the runtime's own measured values.

Usage is additionally keyed by **tenant** so the dashboard can show each user
only their own spend. The tenant is identity-derived — read from
``core.context.get_tenant_or_default()`` (bound at the auth chokepoints from the
JWT ``tenant_id`` claim, default ``= user_id``), never a client header — at the
moment usage is recorded, i.e. inside the same request task that the auth guard
bound. Calls outside a tenant-bound context fall back to ``"default"``. The
read side (:func:`LlmCostLedger.snapshot`) filters to one tenant for an ordinary
user, or aggregates across **all** tenants for an admin (the platform-wide view).
"""

from __future__ import annotations

import threading
import time
from contextvars import ContextVar
from typing import Any

from core.observability.logging import get_logger

logger = get_logger(__name__)

# Set per-request by the ASGI meter; visible to LLM calls in the same task.
current_plugin: ContextVar[str | None] = ContextVar("blc_current_plugin", default=None)
# Holds the prompt-token count between the paired input/output usage reports.
_pending_input: ContextVar[int] = ContextVar("blc_pending_input", default=0)

UNBOUND = "unbound"  # LLM usage not attributable to a plugin HTTP request
_DEFAULT_TENANT = "default"  # tenant fallback for calls with no bound identity

_INSTALLED = False
_INSTALL_LOCK = threading.Lock()


class LlmCostLedger:
    """Process-wide, thread-safe ledger of LLM usage keyed by (tenant, plugin, model)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[tuple[str, str, str], dict[str, Any]] = {}
        # Usage accumulated since the last :meth:`drain_deltas`. The durable
        # store folds these into Postgres via an additive UPSERT (so workers
        # sum, never clobber); ``_rows`` keeps the absolute in-memory totals for
        # the no-DB fallback. Both are updated under the same lock in `record`.
        self._deltas: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._started = time.time()

    def record(
        self,
        tenant: str,
        plugin: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Accumulate one usage report (prompt>0 marks the start of a call)."""
        prompt_tokens = max(prompt_tokens, 0)
        completion_tokens = max(completion_tokens, 0)
        cost = 0.0
        try:
            from core.models.pricing import estimate_cost

            cost = estimate_cost(model, prompt_tokens, completion_tokens)
        except Exception:  # noqa: BLE001 — pricing is best-effort, never fatal
            cost = 0.0
        key = (tenant, plugin, model)
        with self._lock:
            row = self._rows.get(key)
            if row is None:
                row = {
                    "tenant": tenant,
                    "plugin": plugin,
                    "model": model,
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_usd": 0.0,
                    "last_active": 0.0,
                }
                self._rows[key] = row
            delta = self._deltas.get(key)
            if delta is None:
                delta = {
                    "tenant": tenant,
                    "plugin": plugin,
                    "model": model,
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_usd": 0.0,
                }
                self._deltas[key] = delta
            if prompt_tokens > 0:  # a fresh call (input side reported once)
                row["calls"] += 1
                delta["calls"] += 1
            row["prompt_tokens"] += prompt_tokens
            row["completion_tokens"] += completion_tokens
            row["cost_usd"] += cost
            row["last_active"] = time.time()
            delta["prompt_tokens"] += prompt_tokens
            delta["completion_tokens"] += completion_tokens
            delta["cost_usd"] += cost

    def drain_deltas(self) -> list[dict[str, Any]]:
        """Return and clear per-key usage accumulated since the last drain.

        The durable store (:mod:`.cost_store`) folds these into Postgres via an
        additive UPSERT, so each worker contributes its own slice without
        clobbering the others. The absolute in-memory totals (:meth:`snapshot`)
        are left intact as the no-database fallback.
        """
        with self._lock:
            drained = list(self._deltas.values())
            self._deltas = {}
            return drained

    def snapshot(self, tenant: str | None = None) -> tuple[float, list[dict[str, Any]]]:
        """Return ``(since_epoch, rows)`` aggregated by ``(plugin, model)``.

        ``tenant=None`` aggregates across **every** tenant (the admin/global
        view — total spend by all users); a tenant id restricts the aggregate to
        that tenant's own usage. The tenant dimension is collapsed out of the
        returned rows so the response shape is identical for both scopes.
        """
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        with self._lock:
            for (row_tenant, plugin, model), row in self._rows.items():
                if tenant is not None and row_tenant != tenant:
                    continue
                mkey = (plugin, model)
                agg = merged.get(mkey)
                if agg is None:
                    agg = {
                        "plugin": plugin,
                        "model": model,
                        "calls": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "cost_usd": 0.0,
                        "last_active": 0.0,
                    }
                    merged[mkey] = agg
                agg["calls"] += row["calls"]
                agg["prompt_tokens"] += row["prompt_tokens"]
                agg["completion_tokens"] += row["completion_tokens"]
                agg["cost_usd"] += row["cost_usd"]
                agg["last_active"] = max(agg["last_active"], row["last_active"])
            return self._started, list(merged.values())


_LEDGER: LlmCostLedger | None = None
_LEDGER_LOCK = threading.Lock()


def get_llm_ledger() -> LlmCostLedger:
    """Return the singleton usage ledger."""
    global _LEDGER
    if _LEDGER is None:
        with _LEDGER_LOCK:
            if _LEDGER is None:
                _LEDGER = LlmCostLedger()
    return _LEDGER


def _current_tenant() -> str:
    """Identity-derived tenant for the active call, ``"default"`` if unbound.

    Reads the tenant the auth chokepoints bound for this request task (from the
    JWT ``tenant_id`` claim) — never a client header — so usage is attributed to
    the logged-in user. Degrades to ``"default"`` for out-of-request callers
    (background tasks, scripts) and if core context is unavailable.
    """
    try:
        from core.context import get_tenant_or_default

        return get_tenant_or_default()
    except Exception:  # noqa: BLE001 — attribution is best-effort, never fatal
        return _DEFAULT_TENANT


def attribute_tokens(count: int, model: str) -> None:
    """Record one token report against the active tenant+plugin (input/output paired)."""
    if model.startswith("input"):  # core labels prompt reports "input"/"input_stream"
        _pending_input.set(int(count))
        return
    plugin = current_plugin.get() or UNBOUND
    tenant = _current_tenant()
    prompt = _pending_input.get(0)
    if prompt:
        _pending_input.set(0)
    get_llm_ledger().record(tenant, plugin, model, prompt, int(count))


def install_llm_cost_tracking() -> bool:
    """Wrap the core token sink so usage is also recorded into the ledger.

    Idempotent and best-effort: returns ``True`` once tracking is active (or was
    already), ``False`` if the LLM service module is unavailable.
    """
    global _INSTALLED
    if _INSTALLED:
        return True
    with _INSTALL_LOCK:
        if _INSTALLED:
            return True
        try:
            import core.services.llm.service as mod
        except Exception as exc:  # noqa: BLE001 — LLM layer optional
            logger.warning("LLM cost tracking unavailable: %s", exc)
            return False
        original = getattr(mod, "_report_tokens_to_middleware", None)
        if not callable(original):
            return False

        def wrapped(count: int, model: str = "unknown") -> None:
            try:
                original(count, model=model)
            finally:
                try:
                    attribute_tokens(count, model)
                except Exception:  # noqa: BLE001 — never break an LLM call
                    pass

        mod._report_tokens_to_middleware = wrapped
        get_llm_ledger()
        _INSTALLED = True
        logger.info("BaselithControl LLM cost tracking installed")
        return True


__all__ = [
    "current_plugin",
    "LlmCostLedger",
    "get_llm_ledger",
    "attribute_tokens",
    "install_llm_cost_tracking",
    "UNBOUND",
]

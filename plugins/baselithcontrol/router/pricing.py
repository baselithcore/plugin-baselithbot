"""Read-only LLM cost routes: real per-plugin usage + a pricing reference.

* ``/cost/usage`` — measured per-plugin LLM spend since process start, recorded
  by the runtime token-sink wrapper (:mod:`..service.llm_cost`). Token counts are
  the runtime's own values; cost is a list-price estimate.
* ``/pricing`` — the core pricing table (:mod:`core.models.pricing`), shown
  alongside as a rate reference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from core.auth.types import AuthUser
from core.context import get_tenant_or_default

from ..api_models import CostUsageView, PluginCostRow, PricingRow, PricingView
from ._guards import current_principal, is_admin_async, read_guard

if TYPE_CHECKING:
    from ..service.cost_store import CostStore

_PROVIDER_PREFIXES: tuple[tuple[str, str], ...] = (
    ("claude", "Anthropic"),
    ("gpt", "OpenAI"),
    ("o1", "OpenAI"),
    ("gemini", "Google"),
    ("ollama/", "Local"),
)


def _provider_of(model_id: str) -> str:
    """Best-effort provider label from a model id prefix."""
    for prefix, provider in _PROVIDER_PREFIXES:
        if model_id.startswith(prefix):
            return provider
    return "Other"


def _flush_pending(store: CostStore) -> bool:
    """Sync helper (run off the event loop): probe the DB and flush deltas.

    Returns whether durable persistence is available, so the route knows to read
    from Postgres (the cross-worker, restart-surviving source of truth) or to
    fall back to the in-memory ledger. Flushing this worker's pending deltas
    first makes its own recent spend visible on the very next read.
    """
    from ..service.llm_cost import get_llm_ledger

    if not store.available():
        return False
    store.flush(get_llm_ledger().drain_deltas())
    return True


def build_pricing_router() -> APIRouter:
    """Build the cost sub-router: real usage + pricing reference (auth reads)."""
    router = APIRouter(
        tags=["baselithcontrol:cost"], dependencies=[Depends(read_guard)]
    )

    @router.get("/cost/usage", response_model=CostUsageView)
    async def cost_usage(
        principal: AuthUser = Depends(current_principal),
    ) -> CostUsageView:
        """Measured per-plugin LLM spend since process start (list-price cost).

        Tenant-scoped: an ordinary user sees only their own usage; an admin sees
        the **platform-wide** total (every user's spend), so the System Console
        cost menu reports the whole deployment. Scope is identity-derived — the
        admin check and the caller's tenant both come from the validated
        session, never a client-supplied value.
        """
        from starlette.concurrency import run_in_threadpool

        from ..service.cost_store import get_cost_store
        from ..service.llm_cost import get_llm_ledger, install_llm_cost_tracking

        admin = await is_admin_async(principal)
        # Admin → global (all tenants). Otherwise the caller's own tenant, taken
        # from the JWT-derived claim (or the bound context), never a header.
        tenant = (
            None
            if admin
            else (getattr(principal, "tenant_id", None) or get_tenant_or_default())
        )
        scope = "global" if admin else "tenant"

        tracked = install_llm_cost_tracking()  # idempotent; ensures the wrapper

        # Durable totals (survive restarts, sum across workers) when a DB is
        # configured; otherwise the in-memory ledger (resets on restart). The
        # sync probe + this worker's pending-delta flush run off the event loop;
        # the read itself is async. Flushing first makes this worker's own
        # recent spend visible immediately (others land within a flush cycle).
        store = get_cost_store()
        persistent = await run_in_threadpool(_flush_pending, store)
        if persistent:
            since, raw = await store.read(tenant)
        else:
            since, raw = get_llm_ledger().snapshot(tenant)
        rows = [
            PluginCostRow(
                plugin=r["plugin"],
                model=r["model"],
                calls=r["calls"],
                prompt_tokens=r["prompt_tokens"],
                completion_tokens=r["completion_tokens"],
                total_tokens=r["prompt_tokens"] + r["completion_tokens"],
                cost_usd=round(r["cost_usd"], 6),
                last_active=r["last_active"] or None,
            )
            for r in raw
        ]
        rows.sort(key=lambda r: r.cost_usd, reverse=True)
        return CostUsageView(
            tracked=tracked,
            since=since,
            scope=scope,
            tenant_id=tenant,
            persistent=persistent,
            total_cost_usd=round(sum(r.cost_usd for r in rows), 6),
            total_tokens=sum(r.total_tokens for r in rows),
            rows=rows,
        )

    @router.get("/pricing", response_model=PricingView)
    async def pricing() -> PricingView:
        """The LLM list-price table + unknown-model fallback (USD / 1M tokens)."""
        from core.models.pricing import (
            DEFAULT_PRICING,
            PRICING_AS_OF,
            UNKNOWN_PRICE,
        )

        rows = [
            PricingRow(
                model_id=model_id,
                provider=_provider_of(model_id),
                input_usd_per_million=price.input_usd_per_million,
                output_usd_per_million=price.output_usd_per_million,
            )
            for model_id, price in DEFAULT_PRICING.items()
        ]
        rows.sort(key=lambda r: (r.provider, r.model_id))
        return PricingView(
            as_of=PRICING_AS_OF,
            unknown_input_usd_per_million=UNKNOWN_PRICE.input_usd_per_million,
            unknown_output_usd_per_million=UNKNOWN_PRICE.output_usd_per_million,
            rows=rows,
        )

    return router


__all__ = ["build_pricing_router"]

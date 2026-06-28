"""Read-only LLM cost routes: real per-plugin usage + a pricing reference.

* ``/cost/usage`` — measured per-plugin LLM spend since process start, recorded
  by the runtime token-sink wrapper (:mod:`..service.llm_cost`). Token counts are
  the runtime's own values; cost is a list-price estimate.
* ``/pricing`` — the core pricing table (:mod:`core.models.pricing`), shown
  alongside as a rate reference.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..api_models import CostUsageView, PluginCostRow, PricingRow, PricingView
from ._guards import read_guard

# Pricing snapshot date — kept in sync with core/models/pricing.py's comment.
_AS_OF = "2026-05-16"

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


def build_pricing_router() -> APIRouter:
    """Build the cost sub-router: real usage + pricing reference (auth reads)."""
    router = APIRouter(
        tags=["baselithcontrol:cost"], dependencies=[Depends(read_guard)]
    )

    @router.get("/cost/usage", response_model=CostUsageView)
    async def cost_usage() -> CostUsageView:
        """Measured per-plugin LLM spend since process start (list-price cost)."""
        from ..service.llm_cost import get_llm_ledger, install_llm_cost_tracking

        tracked = install_llm_cost_tracking()  # idempotent; ensures the wrapper
        since, raw = get_llm_ledger().snapshot()
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
            total_cost_usd=round(sum(r.cost_usd for r in rows), 6),
            total_tokens=sum(r.total_tokens for r in rows),
            rows=rows,
        )

    @router.get("/pricing", response_model=PricingView)
    async def pricing() -> PricingView:
        """The LLM list-price table + unknown-model fallback (USD / 1M tokens)."""
        from core.models.pricing import DEFAULT_PRICING, UNKNOWN_PRICE

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
            as_of=_AS_OF,
            unknown_input_usd_per_million=UNKNOWN_PRICE.input_usd_per_million,
            unknown_output_usd_per_million=UNKNOWN_PRICE.output_usd_per_million,
            rows=rows,
        )

    return router


__all__ = ["build_pricing_router"]

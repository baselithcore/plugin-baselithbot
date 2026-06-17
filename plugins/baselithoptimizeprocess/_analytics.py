"""Analytics mixin for :class:`BopService`: cost rollup + what-if simulation.

Split out of the service body (like :class:`GovernanceMixin`) to keep files well
under the size cap and group the read-only "predict / cost" concern behind one
seam. Touches only ``self._store`` and the tenant context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from .anomaly import (
    Anomaly,
    BreachForecast,
    detect_anomalies,
    forecast_breach,
)
from .api_models import RegisterProcessRequest
from .cost import CostReport, process_cost
from .models import ProcessGraph
from .reporting import build_csv, build_markdown

if TYPE_CHECKING:  # for the cast that reaches sibling-mixin/service methods
    from .service import BopService
from .simulation import (
    SimulationComparison,
    SimulationResult,
    compare,
)
from .simulation import simulate as simulate_graph
from .store import ProcessStore
from .tenancy import current_tenant


class AnalyticsMixin:
    """Cost and simulation behaviour mixed into the BOP service."""

    _store: ProcessStore

    async def cost_report(self, process_id: str) -> CostReport | None:
        """Roll up a process's node costs; None when the process is unknown."""
        process = await self._store.get_process(current_tenant(), process_id)
        if process is None:
            return None
        return process_cost(process)

    async def simulate(self, process_id: str) -> SimulationResult | None:
        """Predict the current process's cycle time and cost; None if unknown."""
        process = await self._store.get_process(current_tenant(), process_id)
        if process is None:
            return None
        return simulate_graph(process)

    async def simulate_variant(
        self, process_id: str, request: RegisterProcessRequest
    ) -> SimulationComparison | None:
        """What-if: compare a candidate redesign against the stored baseline."""
        baseline = await self._store.get_process(current_tenant(), process_id)
        if baseline is None:
            return None
        variant = ProcessGraph(
            id=baseline.id,
            name=request.name or baseline.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
            kpis=request.kpis,
            currency=request.currency,
            annual_case_volume=request.annual_case_volume,
        )
        return compare(baseline, variant)

    async def anomalies(self, process_id: str) -> list[Anomaly]:
        """Statistical KPI outliers across the process's recent samples."""
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return []
        out: list[Anomaly] = []
        for kpi in process.kpis:
            samples = await self._store.recent_samples(tenant, process.id, kpi.id)
            out.extend(detect_anomalies(kpi, samples))
        return out

    async def forecasts(self, process_id: str) -> list[BreachForecast]:
        """Breach forecasts for the process's KPIs (trend → target)."""
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return []
        return await self._forecasts_for(tenant, process)

    async def _forecasts_for(
        self, tenant: str, process: ProcessGraph
    ) -> list[BreachForecast]:
        """Compute breach forecasts for a (already-fetched) process."""
        out: list[BreachForecast] = []
        for kpi in process.kpis:
            samples = await self._store.recent_samples(tenant, process.id, kpi.id)
            forecast = forecast_breach(kpi, samples)
            if forecast is not None:
                out.append(forecast)
        return out

    async def report(self, process_id: str, fmt: str = "markdown") -> str | None:
        """Render an executive report (Markdown or CSV); None if unknown."""
        svc = cast("BopService", self)
        process = await self._store.get_process(current_tenant(), process_id)
        if process is None:
            return None
        snapshots = await svc.snapshots(process_id)
        bottlenecks = await svc.list_bottlenecks(process_id)
        cost = process_cost(process)
        sim = simulate_graph(process)
        proposals = await svc.list_proposals(process_id)
        renderer = build_csv if fmt == "csv" else build_markdown
        return renderer(process, snapshots, bottlenecks, cost, sim, proposals)


__all__ = ["AnalyticsMixin"]

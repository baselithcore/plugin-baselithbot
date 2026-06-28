"""Wire contract for the control-plane API.

These DTOs are the stable boundary between the dashboard frontend and the
aggregation/control backend. They are deliberately decoupled from the internal
registry shapes so the UI never depends on core internals.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

API_VERSION = "1"


class PluginState(str, Enum):
    """Coarse lifecycle state projected onto the wire."""

    discovered = "discovered"  # known statically, not yet activated
    active = "active"  # initialized and serving
    disabled = "disabled"  # explicitly unregistered
    failed = "failed"  # load/health failure
    unknown = "unknown"


class EmbedSurface(BaseModel):
    """An aggregatable UI surface discovered from a plugin's manifest/tabs."""

    tab_id: str
    label: str
    mount_url: str | None = None  # SPA mount, e.g. "/baselithbot"
    static_base: str | None = None  # "/plugins/<name>/static"
    embeddable: bool = True  # has an embeddable mount (index.html or explicit url)


class StatusKind(str, Enum):
    """Health vocabulary projected onto a plugin (decoupled from lifecycle).

    Maps cleanly onto agent semantics: ``healthy`` (running + ready),
    ``degraded`` (running but unhealthy), ``down`` (load/health failure),
    ``disabled`` (intentionally off), ``unknown`` (not yet probed).
    """

    healthy = "healthy"
    degraded = "degraded"
    down = "down"
    disabled = "disabled"
    unknown = "unknown"


class MetricView(BaseModel):
    """A single formatted metric surfaced on a plugin tile."""

    label: str
    value: float | str | None = None
    format: str = "number"  # number | percent | duration | bytes | text
    tone: str = "neutral"  # neutral | success | warning | danger | info


class PluginCardView(BaseModel):
    """One row of the inventory grid."""

    name: str
    version: str = "0.0.0"
    description: str = ""
    category: str = "uncategorized"
    group: str = ""  # display grouping (manifest control.group → category fallback)
    tier: str = "application"  # "system" (framework/infra) | "application" (custom)
    tenancy: str = (
        "shared"  # "shared" (deployment tenant) | "personal" (1 user = 1 tenant)
    )
    icon: str = ""  # optional lucide icon name from manifest control.icon
    instance: str | None = None  # multi-env/tenant routing label
    state: PluginState = PluginState.unknown
    healthy: bool | None = None
    initialized: bool = False
    config_enabled: bool | None = None  # persisted `enabled` in plugins.yaml
    provides_routes: bool = False
    router_prefix: str | None = None
    surfaces: list[EmbedSurface] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class InventoryView(BaseModel):
    """Full plugin catalog for the dashboard grid."""

    api_version: str = API_VERSION
    total: int = 0
    plugins: list[PluginCardView] = Field(default_factory=list)


class StatusView(BaseModel):
    """Aggregated health + system metrics snapshot."""

    api_version: str = API_VERSION
    healthy: bool = False
    plugins: dict[str, dict] = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)


class PluginStatus(BaseModel):
    """Normalized health envelope for one plugin (the status adapter output)."""

    plugin: str
    kind: StatusKind = StatusKind.unknown
    state: PluginState = PluginState.unknown
    latency_ms: float | None = None
    code: int | None = None
    last_seen: float | None = None  # epoch seconds of last healthy probe
    metrics: list[MetricView] = Field(default_factory=list)


class WidgetFieldSpec(BaseModel):
    """A declarative field mapping over a plugin's JSON status endpoint."""

    path: str  # dot-path into the JSON (e.g. "queue.depth", "items.0.id")
    label: str | None = None
    format: str = "number"  # number | percent | duration | bytes | text
    highlight: dict | None = None  # {"gte"|"lte"|"eq": x, "tone": "warning"}


class WidgetSpec(BaseModel):
    """Zero-code status widget declared in a plugin manifest (``control.widget``).

    The dashboard resolves this spec server-side; the browser fetches the
    same-origin ``endpoint`` directly (cookie-authed) and renders it with a
    single generic renderer — no per-plugin frontend code, no coupling.
    """

    plugin: str
    title: str
    endpoint: str  # relative, same-origin path (e.g. "/api/<plugin>/stats")
    display: str = "list"  # list | block
    fields: list[WidgetFieldSpec] = Field(default_factory=list)


class HeadStat(BaseModel):
    """A framework-wide aggregate shown in the head band above the grid."""

    key: str
    label: str
    value: float
    tone: str = "neutral"


class OverviewView(BaseModel):
    """Framework-wide control-plane summary."""

    api_version: str = API_VERSION
    total: int = 0
    healthy: int = 0
    degraded: int = 0
    down: int = 0
    embeddable: int = 0
    with_routes: int = 0
    stats: list[HeadStat] = Field(default_factory=list)


class SystemResources(BaseModel):
    """Framework-wide (whole-process + host) resource snapshot.

    Per-plugin CPU/RAM is deliberately absent: plugins share one process, so the
    OS cannot attribute it. Per-plugin signal lives in :class:`PluginRuntime`.
    All gauges are optional — ``None`` when ``psutil`` or a platform counter is
    unavailable, so the dashboard can hide what it can't measure.
    """

    api_version: str = API_VERSION
    available: bool = False
    uptime_seconds: float = 0.0
    cpu_percent: float | None = None  # this process, across all cores
    host_cpu_percent: float | None = None  # whole host
    cpu_count: int | None = None
    rss_bytes: int | None = None  # resident memory of the process
    rss_percent: float | None = None  # process RSS as % of host RAM
    mem_percent: float | None = None  # host memory pressure
    mem_total_bytes: int | None = None
    mem_available_bytes: int | None = None
    threads: int | None = None
    open_fds: int | None = None
    net_sent_bps: float | None = None  # bytes/s, rate-derived between polls
    net_recv_bps: float | None = None
    net_sent_bytes: int | None = None  # cumulative host counters
    net_recv_bytes: int | None = None


class PluginRuntime(BaseModel):
    """Per-plugin HTTP request telemetry (the honest per-plugin resource view)."""

    plugin: str
    requests: int = 0  # monotonic; the UI derives request rate from its deltas
    errors: int = 0
    in_flight: int = 0
    error_rate: float = 0.0
    avg_ms: float = 0.0  # EWMA-smoothed latency
    p95_ms: float = 0.0
    last_ms: float = 0.0


class ActionRequest(BaseModel):
    """Optional body for a gated action; the reason flows into the audit trail."""

    reason: str | None = None


class ConfigRequest(BaseModel):
    """Set a plugin's persisted ``enabled`` flag in plugins.yaml."""

    enabled: bool
    reason: str | None = None


class ActionResult(BaseModel):
    """Outcome of a gated lifecycle operation."""

    plugin: str
    operation: str
    ok: bool
    state: PluginState = PluginState.unknown
    message: str = ""


class AuditEntryView(BaseModel):
    """A single append-only audit record."""

    actor: str
    plugin: str
    operation: str
    ok: bool
    reason: str | None = None
    timestamp: float


class RequestVolumeSample(BaseModel):
    """One point of the retained aggregate request-rate series.

    ``requests_per_sec`` is the total HTTP throughput across all plugins at
    ``timestamp`` (epoch seconds), derived server-side from the monotonic meter
    so the trend survives page reloads and spans the full retained window.
    """

    timestamp: float
    requests_per_sec: float


class LifecycleEvent(BaseModel):
    """A retained plugin-lifecycle record for the activity timeline.

    Captures the well-known control-plane topics (``plugin.activated`` /
    ``deactivated`` / ``reloaded`` / ``failed`` and governed dashboard actions)
    with their timestamp, so the UI can show recent history even after a reload.
    """

    type: str
    timestamp: float
    plugin: str | None = None
    state: str | None = None
    ok: bool | None = None


class LogEntry(BaseModel):
    """One captured application log record for the live log viewer."""

    seq: int  # monotonic id, for stable de-dup/keying on the client
    timestamp: float
    level: str  # DEBUG | INFO | WARNING | ERROR | CRITICAL
    logger: str  # fully-qualified logger name (e.g. plugins.auth.routes)
    plugin: str  # attribution derived from the logger name (e.g. "auth", "core")
    message: str


class LogsView(BaseModel):
    """A filtered tail of the in-memory log ring, plus filter facets."""

    api_version: str = API_VERSION
    enabled: bool = True
    capacity: int = 0
    count: int = 0  # entries returned after filtering
    plugins: list[str] = Field(default_factory=list)  # distinct plugins seen
    entries: list[LogEntry] = Field(default_factory=list)


class PricingRow(BaseModel):
    """List-price for one model, USD per 1M tokens (reference, not live spend)."""

    model_id: str
    provider: str
    input_usd_per_million: float
    output_usd_per_million: float


class PricingView(BaseModel):
    """The LLM pricing reference table for the cost panel.

    A **pricing reference** (list price per 1M tokens) shown alongside the real
    measured per-plugin usage — handy for sanity-checking the rate applied.
    """

    api_version: str = API_VERSION
    currency: str = "USD"
    as_of: str = ""  # snapshot date of the pricing table
    unknown_input_usd_per_million: float = 0.0
    unknown_output_usd_per_million: float = 0.0
    rows: list[PricingRow] = Field(default_factory=list)


class PluginCostRow(BaseModel):
    """Measured LLM usage + list-price cost for one (plugin, model) pair."""

    plugin: str
    model: str
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    last_active: float | None = None


class CostUsageView(BaseModel):
    """Real per-plugin LLM spend since process start (list-price estimate).

    Token counts are the runtime's own measured values, attributed to the plugin
    that served the originating request; ``unbound`` groups usage from calls not
    tied to a plugin HTTP request. Cost is a list-price estimate (the core layer
    does not expose provider-billed cost). ``tracked`` is false if the wrapper
    could not be installed.
    """

    api_version: str = API_VERSION
    currency: str = "USD"
    tracked: bool = True
    since: float = 0.0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    rows: list[PluginCostRow] = Field(default_factory=list)


__all__ = [
    "API_VERSION",
    "PluginState",
    "StatusKind",
    "MetricView",
    "EmbedSurface",
    "PluginCardView",
    "InventoryView",
    "StatusView",
    "PluginStatus",
    "WidgetFieldSpec",
    "WidgetSpec",
    "HeadStat",
    "OverviewView",
    "SystemResources",
    "PluginRuntime",
    "ActionRequest",
    "ConfigRequest",
    "ActionResult",
    "AuditEntryView",
    "RequestVolumeSample",
    "LifecycleEvent",
    "LogEntry",
    "LogsView",
    "PricingRow",
    "PricingView",
    "PluginCostRow",
    "CostUsageView",
]

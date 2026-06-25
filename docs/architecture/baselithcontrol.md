# `baselithcontrol` — Centralized Control-Plane Dashboard

> **Status:** design specification (approved work proposal, 2026-06-15)
> **Type:** official plugin — `RouterPlugin` + sub-app-mounted React/Vite SPA
> **Goal:** a single command bridge that dynamically discovers every loaded
> plugin, monitors it in real time, aggregates its UI, and exposes governed
> lifecycle control — built on the framework's *existing* primitives, with zero
> per-plugin hardcoding.

This document is the binding contract for the build. It is split into a
**Backend** section (control API, state, modules) and a **Frontend** section
(shell layout, widgets, UI aggregation). Every primitive referenced below was
verified against the current tree; file/line anchors are given so the
implementation stays faithful.

---

## 0. Design principles (locked)

| Axis | Decision | Why |
| --- | --- | --- |
| UI aggregation | **Hybrid, manifest-driven** — sandboxed `<iframe>` embed of each plugin SPA (from `get_ui_tabs()` / frontend-manifest) **+** A2UI status widgets | No coupling; plugins stay the source of truth for their own UI; dashboard adds only the frame + cross-plugin realtime status |
| Realtime | **SSE** `/api/baselithcontrol/stream` fed by a **bridge** off `core.events.bus.EventBus` (`plugin.*` / `system.*`), Redis PubSub fan-out for multi-instance | Matches the canonical repo pattern ([baselithtwin/router_realtime.py](../../plugins/baselithtwin/router_realtime.py)); reuses the in-process bus instead of inventing transport |
| Control | **Full lifecycle** (enable / disable / reload) behind `auth.require_roles(ADMIN)` **+** `AutonomyPolicy` gating **+** append-only audit | Powerful but governed; destructive actions are HITL-gated, never silent |
| Frontend stack | **React 19 + Vite + Tailwind 4 + Zustand + motion/react** (baselithbrain template) **+ `react-i18next` en/it** | Newest stack in repo; i18n en+it is mandatory for new plugins per CLAUDE.md |
| Hard constraints | every source file **< 500 LOC**; `SecretStr` for credentials; **pure ASGI** middleware; `integrity_sha256` recomputed on `.py` edits | Framework invariants |

**Sacred Core rule:** `baselithcontrol` is a plugin. It imports *from* `core`
(registry, event bus, a2ui, auth) but adds **no** files under `core/` and
introduces **no** new `core -> plugins` import.

---

## 1. Primitives reused (do not reinvent)

| Capability | Source | Surface consumed |
| --- | --- | --- |
| Plugin enumeration | [core/plugins/registry.py](../../core/plugins/registry.py) | `get_all()`, `list_plugins()`, `health_check()`, `get_discovered_plugin()`, `get_frontend_manifest()`, `get_all_static_paths()` |
| Runtime handle | [core/api/lifespan.py:335](../../core/api/lifespan.py#L335) | `app.state.plugin_registry` |
| Lifecycle actions | [core/plugins/api.py](../../core/plugins/api.py) | existing `enable` / `disable` / `reload` + `/metrics/system/overview` — proxied, **not** duplicated |
| Event bus | [core/events/bus.py:446](../../core/events/bus.py#L446) | `get_event_bus()`, `subscribe(name, handler, priority)`, `await emit(name, data, source=…)` |
| SSE shape | [plugins/baselithtwin/router_realtime.py:81](../../plugins/baselithtwin/router_realtime.py#L81) | heartbeat 20 s, `: connected`, `X-Accel-Buffering: no` |
| Safe UI trees | [core/a2a/a2ui.py:182](../../core/a2a/a2ui.py#L182) | `validate_blueprint()`, sealed 12-component whitelist, depth ≤ 16 / nodes ≤ 256 |
| AuthZ | [plugins/auth/dependencies.py:220](../../plugins/auth/dependencies.py#L220) | `require_roles(AuthRole.ADMIN)`, `AuthRole.GUEST` (read-only) |
| Autonomy gating | [core/orchestration/autonomy.py:56](../../core/orchestration/autonomy.py#L56) | `AutonomyPolicy.requires_approval()`, `enforce_approval()`, `ApprovalRequiredError` |
| Sub-app mount | [plugins/baselithwiki/plugin.py](../../plugins/baselithwiki/plugin.py) | `setup_app_middleware()` → `app.mount()`, lifespan in bg task |

---

## 2. Directory layout (modular from commit #1)

```
plugins/baselithcontrol/
├── manifest.yaml                 # name=baselithcontrol; deps: auth; integrity_sha256
├── __init__.py                   # explicit exports
├── plugin.py                     # ControlPlanePlugin(RouterPlugin) + setup_app_middleware
├── config.py                     # Pydantic settings (SecretStr), root .env
├── i18n.py                       # negotiate_locale + translate (backend strings)
├── locales/  en.json  it.json    # backend user-facing catalog (en + it)
├── api_models.py                 # Pydantic DTOs (the wire contract)
├── router/
│   ├── __init__.py               # assemble sub-routers → one APIRouter
│   ├── inventory.py              # GET /inventory, /ui-registry
│   ├── status.py                 # GET /status, /status/{plugin}
│   ├── actions.py                # POST /actions/{plugin}/{op}  (gated)
│   └── stream.py                 # GET /stream  (SSE)
├── service/
│   ├── __init__.py
│   ├── aggregator.py             # registry+manifest+discovery → InventoryView/StatusView
│   ├── control.py                # gated lifecycle (RBAC + autonomy + audit)
│   └── bridge.py                 # EventBus → per-client asyncio.Queue → SSE
├── store/
│   └── protocol.py               # AuditSink Protocol (in-memory default; Postgres opt-in later)
└── ui/                           # React 19 + Vite + Tailwind 4 (built → ui/dist/)
    ├── package.json  vite.config.ts  tailwind.config.ts
    └── src/
        ├── main.tsx  App.tsx
        ├── i18n.ts               # react-i18next bootstrap
        ├── locales/{en,it}/common.json
        ├── lib/  motion.ts  api.ts  sse.ts
        ├── store/  useControlStore.ts   # Zustand
        ├── hooks/  useInventory.ts  useStatusStream.ts
        ├── components/
        │   ├── Shell/  index.tsx  Sidebar.tsx  Topbar.tsx
        │   ├── widgets/  PluginCard.tsx  HealthBadge.tsx  MetricSpark.tsx  A2UIRenderer.tsx
        │   └── embed/  PluginFrame.tsx   # sandboxed iframe
        └── pages/  Overview.tsx  PluginDetail.tsx
```

Every file stays **< 500 LOC** — split *before* the PR, never after.

---

## BACKEND

## 3. API contract (`/api/baselithcontrol`) — the conclusion criterion

The prefix is the framework default (`RouterPlugin.get_router_prefix()` →
`/api/baselithcontrol`). Read endpoints accept `Accept-Language` (en/it).

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/inventory` | `GUEST`+ | Merged catalog: active plugins + lazy-discovered, metadata, capabilities, embeddable flag |
| `GET` | `/ui-registry` | `GUEST`+ | Embeddable surfaces only (tabs, mount URL, static base) for the shell |
| `GET` | `/status` | `GUEST`+ | Aggregated health + system metrics overview |
| `GET` | `/status/{plugin}` | `GUEST`+ | Per-plugin drill-down (state, health, metrics, last events) |
| `GET` | `/stream` | `GUEST`+ | SSE: lifecycle/health/metric deltas (EventBus bridge) |
| `POST` | `/actions/{plugin}/enable` | `ADMIN` | Gated activate |
| `POST` | `/actions/{plugin}/disable` | `ADMIN` | Gated deactivate (HITL via autonomy) |
| `POST` | `/actions/{plugin}/reload` | `ADMIN` | Gated hot-reload |

### 3.1 Wire DTOs — `api_models.py`

```python
"""Wire contract for the control-plane API (stable, versioned via X-API-Version)."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class PluginState(str, Enum):
    """Mirror of core.plugins.lifecycle.PluginState for the wire."""
    discovered = "discovered"
    active = "active"
    disabled = "disabled"
    failed = "failed"
    unknown = "unknown"


class EmbedSurface(BaseModel):
    """An aggregatable UI surface discovered from a plugin's manifest."""
    tab_id: str
    label: str
    mount_url: str | None = None          # SPA mount, e.g. "/baselithbot"
    static_base: str | None = None        # "/plugins/<name>/static"
    embeddable: bool = True               # has index.html → iframe-able


class PluginCardView(BaseModel):
    """One row of the inventory grid."""
    name: str
    version: str
    description: str = ""
    category: str = "uncategorized"
    tenancy: str = "shared"        # "shared" | "personal" — read-only tenancy model badge
    state: PluginState = PluginState.unknown
    healthy: bool | None = None
    initialized: bool = False
    provides_routes: bool = False
    router_prefix: str | None = None
    surfaces: list[EmbedSurface] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class InventoryView(BaseModel):
    api_version: str = "1"
    total: int
    plugins: list[PluginCardView]


class StatusView(BaseModel):
    healthy: bool
    plugins: dict[str, dict] = Field(default_factory=dict)   # health_check() shape
    metrics: dict = Field(default_factory=dict)              # system/overview shape


class ActionRequest(BaseModel):
    """Optional body for a gated action (reason flows into the audit trail)."""
    reason: str | None = None


class ActionResult(BaseModel):
    plugin: str
    operation: str
    ok: bool
    state: PluginState
    message: str
```

### 3.2 Aggregator — `service/aggregator.py`

Pure read-side projection over the registry. No mutation, thread-safe (the
registry guards itself with an `RLock`).

```python
"""Project the live registry + static discovery into wire views."""
from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger

from ..api_models import (
    EmbedSurface, InventoryView, PluginCardView, PluginState, StatusView,
)

logger = get_logger(__name__)


class ControlAggregator:
    """Read-only façade over ``app.state.plugin_registry``."""

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def inventory(self) -> InventoryView:
        cards: list[PluginCardView] = []
        health = self._registry.health_check().get("plugins", {})

        for row in self._registry.list_plugins():          # active + lazy
            name = row["name"]
            disc = self._registry.get_discovered_plugin(name)
            hstate = health.get(name, {})
            cards.append(
                PluginCardView(
                    name=name,
                    version=row.get("version", "0.0.0"),
                    description=row.get("description", ""),
                    initialized=row.get("initialized", False),
                    state=self._state(row, hstate),
                    healthy=hstate.get("status") == "healthy" if hstate else None,
                    provides_routes=bool(getattr(disc, "provides_routes", False)),
                    router_prefix=getattr(disc, "router_prefix", None),
                    surfaces=self._surfaces(name, disc),
                )
            )
        return InventoryView(total=len(cards), plugins=cards)

    def ui_registry(self) -> list[EmbedSurface]:
        out: list[EmbedSurface] = []
        for card in self.inventory().plugins:
            out.extend(s for s in card.surfaces if s.embeddable)
        return out

    def status(self, system_metrics: dict) -> StatusView:
        hc = self._registry.health_check()
        return StatusView(
            healthy=hc.get("healthy", False),
            plugins=hc.get("plugins", {}),
            metrics=system_metrics,
        )

    # -- helpers -------------------------------------------------------------
    def _state(self, row: dict, hstate: dict) -> PluginState:
        if hstate.get("status") == "unhealthy":
            return PluginState.failed
        if row.get("initialized"):
            return PluginState.active
        return PluginState.discovered

    def _surfaces(self, name: str, disc: Any) -> list[EmbedSurface]:
        tabs = getattr(disc, "ui_tabs", None) or []
        static_path = self._registry.get_all_static_paths().get(name)
        static_base = f"/plugins/{name}/static" if static_path else None
        embeddable = bool(static_path and (static_path / "index.html").exists())
        surfaces = [
            EmbedSurface(
                tab_id=t.get("id", name),
                label=t.get("label", name),
                mount_url=t.get("url") or (f"/{name}" if embeddable else None),
                static_base=static_base,
                embeddable=embeddable or bool(t.get("url")),
            )
            for t in tabs
        ]
        if not surfaces and embeddable:                      # SPA without ui_tabs
            surfaces.append(
                EmbedSurface(tab_id=name, label=name, mount_url=f"/{name}",
                             static_base=static_base, embeddable=True)
            )
        return surfaces
```

### 3.3 EventBus → SSE bridge — `service/bridge.py`

`EventBus.subscribe()` takes a **handler callback** (not an async iterator), so
each SSE client gets its own bounded `asyncio.Queue`; the handler enqueues,
the generator drains. Mirrors baselithtwin's framing exactly.

```python
"""Bridge the in-process EventBus to per-client SSE queues."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from core.events.bus import get_event_bus
from core.observability.logging import get_logger

logger = get_logger(__name__)

_HEARTBEAT_SECONDS = 20.0
_WATCHED = ("plugin.*", "system.*")        # wildcard topics


async def control_sse() -> AsyncIterator[str]:
    """Yield SSE frames for control-plane lifecycle/health events."""
    bus = get_event_bus()
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=256)

    async def _on_event(event) -> None:                      # Handler signature
        try:
            queue.put_nowait(
                {"type": event.name, "source": getattr(event, "source", None),
                 "data": getattr(event, "data", {})}
            )
        except asyncio.QueueFull:
            logger.warning("control SSE queue full; dropping %s", event.name)

    unsubscribes = [bus.subscribe(topic, _on_event) for topic in _WATCHED]
    yield ": connected\n\n"                                  # open + onopen now
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), _HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield ": ping\n\n"                           # idle keepalive
                continue
            yield f"data: {json.dumps(payload)}\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        return
    finally:
        for off in unsubscribes:
            off()
```

### 3.4 Governed control — `service/control.py`

Lifecycle mutation is the only privileged path. Three gates, fail-closed:
**(1)** `require_roles(ADMIN)` at the route, **(2)** `AutonomyPolicy` approval
for destructive ops, **(3)** append-only audit. The actual state change reuses
the registry/loader the core already exposes — no duplicate logic.

```python
"""Gated lifecycle operations: RBAC + autonomy + audit, then delegate to core."""
from __future__ import annotations

from typing import Any, Protocol

from core.orchestration.autonomy import (
    AutonomyPolicy, enforce_approval, ApprovalRequiredError,
)
from core.observability.logging import get_logger

from ..api_models import ActionResult, PluginState

logger = get_logger(__name__)

# Disabling/reloading a running plugin is mutation of live infra → gated.
_CATEGORY = "system_admin"


class AuditSink(Protocol):
    async def record(self, *, actor: str, plugin: str, op: str,
                     ok: bool, reason: str | None) -> None: ...


class ControlService:
    def __init__(self, registry: Any, policy: AutonomyPolicy,
                 audit: AuditSink, human_intervention: Any | None = None) -> None:
        self._registry = registry
        self._policy = policy
        self._audit = audit
        self._human = human_intervention

    async def run(self, *, plugin: str, op: str, actor: str,
                  reason: str | None) -> ActionResult:
        if plugin not in self._registry:
            return ActionResult(plugin=plugin, operation=op, ok=False,
                                state=PluginState.unknown, message="not found")
        try:
            if op in ("disable", "reload"):                  # destructive → HITL
                await enforce_approval(
                    self._policy, _CATEGORY, f"{op}:{plugin}",
                    human_intervention=self._human,
                )
            ok, state = await self._dispatch(plugin, op)
        except ApprovalRequiredError as exc:
            await self._audit.record(actor=actor, plugin=plugin, op=op,
                                     ok=False, reason=str(exc))
            return ActionResult(plugin=plugin, operation=op, ok=False,
                                state=PluginState.active, message=str(exc))

        await self._audit.record(actor=actor, plugin=plugin, op=op,
                                 ok=ok, reason=reason)
        return ActionResult(plugin=plugin, operation=op, ok=ok, state=state,
                            message="ok" if ok else "operation failed")

    async def _dispatch(self, plugin: str, op: str) -> tuple[bool, PluginState]:
        if op == "reload":
            ok = await self._registry.reload_plugin(plugin)
            return ok, PluginState.active if ok else PluginState.failed
        if op == "disable":
            await self._registry.unregister(plugin)
            return True, PluginState.disabled
        if op == "enable":
            ok = await self._registry.ensure_plugin_active(plugin)
            return ok, PluginState.active if ok else PluginState.failed
        return False, PluginState.unknown
```

### 3.5 Routers (thin) — `router/actions.py`

Routers only adapt HTTP ↔ service. Auth dependency lives here.

```python
"""Gated lifecycle routes — admin only."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, Request

from core.auth.types import AuthRole, AuthUser
from plugins.auth.dependencies import require_roles

from ..api_models import ActionRequest, ActionResult


def build_actions_router(get_service) -> APIRouter:
    router = APIRouter(tags=["baselithcontrol:actions"])

    @router.post("/actions/{plugin}/{op}", response_model=ActionResult)
    async def act(
        plugin: str,
        op: Literal["enable", "disable", "reload"],
        request: Request,
        body: ActionRequest = Body(default=ActionRequest()),
        user: AuthUser = Depends(require_roles(AuthRole.ADMIN)),
    ) -> ActionResult:
        service = get_service(request.app)
        return await service.run(
            plugin=plugin, op=op, actor=user.user_id, reason=body.reason,
        )

    return router
```

`router/stream.py` wraps `control_sse()` in a `StreamingResponse` with
`media_type="text/event-stream"` and the same headers as baselithtwin.
`router/inventory.py` / `router/status.py` call the aggregator and depend on
`require_roles(AuthRole.GUEST, AuthRole.USER, AuthRole.ADMIN)` (read tiers).

### 3.6 Plugin entrypoint — `plugin.py`

`RouterPlugin` assembles the sub-routers; `setup_app_middleware()` mounts the
built SPA before the middleware stack freezes (baselithwiki pattern). The
registry handle is read from `app.state` at request time, never captured early.

```python
"""ControlPlanePlugin: aggregation API + mounted dashboard SPA."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.plugins.router_plugin import RouterPlugin
from core.observability.logging import get_logger

logger = get_logger(__name__)
MOUNT_PATH = "/baselithcontrol"


class ControlPlanePlugin(RouterPlugin):
    def create_router(self) -> Any:
        from fastapi import APIRouter
        from .router import build_control_router
        router = APIRouter()
        router.include_router(build_control_router())
        return router

    def get_ui_tabs(self) -> list[dict[str, str]]:
        return [{"id": "baselithcontrol", "label": "Control", "url": MOUNT_PATH}]

    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        dist = Path(__file__).parent / "ui" / "dist"
        if not dist.exists():
            logger.warning("baselithcontrol UI not built; SPA not mounted")
            return
        from fastapi.staticfiles import StaticFiles
        app.mount(MOUNT_PATH, StaticFiles(directory=str(dist), html=True),
                  name="baselithcontrol")
```

### 3.7 State management summary

- **No new persistent store on the hot path.** Inventory/status are *derived*
  live from the registry each request (cache with a short TTL in the Zustand
  store on the client, not server-side, to avoid staleness).
- **Audit** is the only write: `AuditSink` Protocol, in-memory ring buffer by
  default; a Postgres-backed sink is an opt-in follow-up (same pattern as BOP
  persistence) — the Protocol keeps it swappable without touching routers.
- **Tenancy:** events and audit inherit the request tenant via
  `core.context.get_current_tenant_id()` (already honored by the EventBus).

---

## FRONTEND

## 4. Shell, widgets, UI aggregation

Stack: React 19 + Vite + Tailwind 4 + Zustand + `motion/react`, built with
`VITE_BASE_PATH=/baselithcontrol/` so assets resolve under the mount. i18n via
`react-i18next` with `en` (default/fallback) + `it`, language switcher in the
top bar, locale persisted to `localStorage`.

### 4.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Topbar:  ⬡ baselithcontrol   health pill   🌐 EN/IT   ⚙︎admin │
├───────────┬──────────────────────────────────────────────────┤
│ Sidebar   │  Overview (default)                              │
│  Overview │  ┌── PluginCard grid (responsive auto-fit) ──┐   │
│  ▸ plugin │  │ [name][ver]  ●healthy  ▁▂▅ metric spark   │   │
│  ▸ plugin │  │ [enable][disable][reload]  (admin only)   │   │
│  …        │  └───────────────────────────────────────────┘   │
│           │  PluginDetail → tabs: [Status][Embedded UI]      │
│           │     Embedded UI = sandboxed <iframe src=mount>   │
└───────────┴──────────────────────────────────────────────────┘
```

The card grid is the unified status surface; the embedded-UI tab is where the
plugin's own SPA lives, untouched. Status widgets that a plugin chooses to emit
as A2UI blueprints render natively via `A2UIRenderer` (whitelist-safe).

### 4.2 Realtime hook — `hooks/useStatusStream.ts`

```typescript
import { useEffect } from "react";
import { useControlStore } from "../store/useControlStore";

// SSE is unnamed data: frames (EventSource.onmessage). Reconnect with backoff.
export function useStatusStream(): void {
  const apply = useControlStore((s) => s.applyEvent);

  useEffect(() => {
    const url = `${import.meta.env.VITE_BASE_PATH ?? "/"}api/baselithcontrol/stream`;
    let es: EventSource | null = null;
    let retry = 0;
    let timer: number | undefined;

    const connect = () => {
      es = new EventSource(url, { withCredentials: true });
      es.onopen = () => (retry = 0);
      es.onmessage = (e) => {
        try { apply(JSON.parse(e.data)); } catch { /* ignore malformed */ }
      };
      es.onerror = () => {
        es?.close();
        retry = Math.min(retry + 1, 6);
        timer = window.setTimeout(connect, 500 * 2 ** retry); // capped backoff
      };
    };

    connect();
    return () => { es?.close(); if (timer) clearTimeout(timer); };
  }, [apply]);
}
```

`store/useControlStore.ts` (Zustand) holds `plugins`, merges `applyEvent`
deltas by name, and exposes selectors so a card re-renders only when *its*
plugin changes (avoids whole-grid re-render). Inventory is fetched once via
TanStack Query / `lib/api.ts` and then kept fresh by the stream.

### 4.3 Sandboxed embed — `components/embed/PluginFrame.tsx`

```typescript
interface PluginFrameProps { src: string; title: string; }

// Each plugin SPA renders in an isolated origin-locked iframe. `sandbox`
// grants scripts + same-origin (needed for its own API calls) but blocks
// top-navigation and popups — the plugin can't hijack the control shell.
export function PluginFrame({ src, title }: PluginFrameProps) {
  return (
    <iframe
      src={src}
      title={title}
      className="h-full w-full rounded-2xl border border-white/10"
      sandbox="allow-scripts allow-same-origin allow-forms"
      referrerPolicy="no-referrer"
      loading="lazy"
    />
  );
}
```

### 4.4 A2UI renderer — `components/widgets/A2UIRenderer.tsx`

Renders only the 12 whitelisted component types from
[core/a2a/a2ui.py](../../core/a2a/a2ui.py). Unknown `type` → render nothing
(the backend already validated, but the client stays defensive). One small
`switch` per node; no `dangerouslySetInnerHTML`, ever. Keeps the dashboard able
to show plugin-emitted status widgets without trusting plugin markup.

### 4.5 i18n bootstrap — `ui/src/i18n.ts`

```typescript
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en/common.json";
import it from "./locales/it/common.json";

void i18n.use(initReactI18next).init({
  resources: { en: { common: en }, it: { common: it } },
  lng: localStorage.getItem("blc.lang") ?? "en",
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});
export default i18n;
```

`en/common.json` and `it/common.json` stay key-for-key in sync (CI rule: a key
added in one must exist in the other). All JSX copy comes from `t("…")` — no
literal strings.

---

## 5. Manifest & integrity

```yaml
# plugins/baselithcontrol/manifest.yaml
name: baselithcontrol
version: 0.1.0
description: Centralized control-plane dashboard — discover, monitor, and govern all plugins.
author: BaselithCore Team
license: Apache-2.0
category: operations
readiness: alpha
tags: [dashboard, control-plane, observability, orchestration]
min_core_version: 1.0.0
required_resources: []
optional_resources: [redis]            # PubSub fan-out only when multi-instance
plugin_dependencies:
  auth: ">=0.1.0"                      # RBAC for gated actions
python_dependencies: []               # core-only; no heavy new deps
environment_variables:
  - BASELITHCONTROL_ENABLED
  - BASELITHCONTROL_REQUIRE_ADMIN
integrity_sha256: "<recompute-on-every-.py-edit>"
```

Register in `plugins.yaml` (the loader filters by config — an unregistered
plugin never loads). Recompute `integrity_sha256` after any `.py` change (UI
edits don't affect the `.py` hash).

---

## 6. Verification gates (must pass for the PR)

```bash
python -m pytest tests/unit/plugins/baselithcontrol/ -v   # mock registry + bus
python scripts/check_official_plugin_typing.py            # strict mypy
python scripts/check_architecture_boundaries.py           # no new core->plugins
ruff check .
find plugins/baselithcontrol -name '*.py' -exec wc -l {} + | awk '$1 > 500'  # empty
find plugins/baselithcontrol/ui/src -regex '.*\.\(ts\|tsx\)' -exec wc -l {} + | awk '$1 > 500'
( cd plugins/baselithcontrol/ui && npm ci && npm run build )   # → ui/dist/
```

**Test matrix (mock registry + bus, no live infra):**

- aggregator projects active + lazy plugins; embeddable flag toggles on `index.html`
- SSE bridge emits `: connected`, forwards a `plugin.*` event, pings on idle, unsubscribes on disconnect
- control service: ADMIN required (403 for GUEST), autonomy denies `disable` → audited failure, `reload` success path audited
- i18n: en/it catalogs key-parity assertion

---

## 7. Build order (priority)

1. **API contract** — `api_models.py` + `router/` skeletons returning typed stubs (freezes the wire). *(conclusion criterion)*
2. **Aggregator + status** — read-side over the registry; Overview grid lights up.
3. **SSE bridge + stream route** — live deltas flowing.
4. **Governed control** — RBAC + autonomy + audit on actions.
5. **Frontend shell** — embed + A2UI renderer + i18n; then gates + integrity + this doc finalized.

Each step lands as small modules, green gates, integrity recomputed.

```

---

## 8. Elevation — best-in-class dashboard patterns (implemented)

Researched against self-hosted dashboards (Homepage, Glance, Dashy, Heimdall,
Organizr, Flame). The convergent architecture they all share — *a `type`-keyed
registry decoupling a normalized data contract from a generic renderer, fed by a
server-side resolver, with a zero-code declarative widget as the escape hatch* —
maps directly onto primitives baselithcontrol already had. Adopted, scoped to a
**plugin** control plane (not arbitrary external services):

### 8.1 Status adapter + 4-state a11y vocabulary
`service/probe.py` → `StatusProber` emits a normalized `PluginStatus`
envelope: `{kind, state, latency_ms, code, last_seen, metrics[]}`. `StatusKind`
collapses lifecycle+health into `healthy | degraded | down | disabled |
unknown`. The frontend `HealthBadge` renders a **distinct shape per state**
(●◆■▲○) so status reads without relying on color (Dashy
`statusCheckAccessibility`), with a hover tooltip showing latency + last-healthy
relative time. Route: `GET /status/{plugin}`.

### 8.2 Zero-code declarative widgets (the escape hatch)
A plugin opts into a rich status tile with **no frontend code** by adding a
`control.widget` block to its `manifest.yaml`. `service/widgets.py` resolves the
spec server-side; the browser fetches the **same-origin relative endpoint**
directly (already cookie-authed) and renders it with one generic
`DeclarativeWidget` (Homepage `customapi` / Glance `custom-api`). Because plugins
are in-process and same-origin, **only relative endpoints are accepted** — no
external fetch, no SSRF surface, no secret injection needed (the session carries
auth). Manifest contract:

```yaml
control:
  group: Operations          # display grouping (→ category fallback)
  icon: gauge                # optional lucide icon name
  instance: prod             # optional multi-env/tenant label
  widget:
    title: Twin queue
    endpoint: /api/baselithtwin/stats   # RELATIVE, same-origin only
    display: list            # list | block
    fields:
      - { path: queue.depth, label: Queue, format: number,
          highlight: { gte: 50, tone: warning } }
      - { path: replies.today, label: Replies, format: number }
```

`format` ∈ `number|percent|duration|bytes|text`; `highlight` ∈
`{gte|lte|eq, tone}` for threshold coloring. Route: `GET /widgets`.

### 8.3 Information architecture

- **Head band** (`GET /overview` → `OverviewView`): framework-wide counts
  (total / healthy / degraded / down) with tones, above the grid
  (Homepage info-widgets / Glance head-widgets).
- **Grouping + search**: the Overview groups cards by `control.group`
  (category fallback) and offers a type-anywhere filter over name/description/
  tags. Manifest-driven, derive-then-override (Flame/Organizr discovery model).

### 8.4 Endpoint surface (final)

`GET /inventory · /ui-registry · /status · /overview · /status/{plugin} ·
/widgets · /stream` (read) and `POST /actions/{plugin}/{op}` + `GET /audit`
(admin). Nine routes total.

### 8.5 Deliberately skipped (dated / out-of-scope for a plugin control plane)

ICMP ping (needs a host binary; an app-level healthcheck is strictly better for
in-process plugins) · weather/clock/RSS vanity widgets · an in-browser YAML
layout editor (config is manifests + registry, not hand-edited) · using an
iframe reverse-proxy portal as primary nav (`X-Frame-Options`/CSP increasingly
blocks it — sandboxed-iframe embed is used only where a plugin SPA genuinely
needs it).

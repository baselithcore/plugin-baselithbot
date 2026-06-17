"""BaselithControl — the centralized control-plane dashboard plugin.

A single command bridge that dynamically discovers every loaded plugin,
monitors it in real time over SSE, aggregates its UI (sandboxed embed + A2UI
status widgets), and exposes governed lifecycle control (enable/disable/reload)
behind RBAC, an optional autonomy gate, and an append-only audit trail.

The package is split into cohesive sub-modules so no file approaches the 500 LOC
cap and so aggregation, realtime, control, and persistence concerns stay
isolated:

* :mod:`config`      — typed settings (env-overridable, self-contained defaults).
* :mod:`api_models`  — the stable wire contract (Pydantic DTOs).
* :mod:`service`     — aggregation, SSE bridge, gated control, audit.
* :mod:`router`      — the async FastAPI surface (REST + SSE).
* :mod:`plugin`      — the :class:`RouterPlugin` entry point + SPA mount.

``core/`` is never modified (Sacred Core); only framework primitives are
imported, and no plugin is referenced by name.
"""

from __future__ import annotations

from .plugin import BaselithControlPlugin

__all__ = ["BaselithControlPlugin"]

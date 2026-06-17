"""BaselithTwin — an engineered WhatsApp Digital Twin plugin.

Ingests a user's WhatsApp stream (via an OpenWA gateway), learns their
communicative style, persists salient facts into a hierarchical long-term
memory, and drafts/sends replies that faithfully simulate the user's identity
under a governed, human-in-the-loop autonomy policy.

The package is split into cohesive sub-modules so no file approaches the 500 LOC
cap and so transport, domain, persistence, and cognition concerns stay isolated:

* :mod:`gateway`  — the :class:`WhatsAppGateway` Protocol and its backends.
* :mod:`store`    — the persistence contract (in-memory default, Postgres opt-in).
* :mod:`style`    — communicative-style extraction (``StyleProfile``).
* :mod:`twin`     — the draft-generation engine and prompt assembly.
* :mod:`policy`   — the whitelist-driven autonomy decision.
* :mod:`service`  — the async orchestrator wiring it all together.
* :mod:`router`   — the FastAPI surface (REST + SSE + webhook) for the frontend.

``core/`` is never imported into at module top-level except for framework
primitives; heavy cognitive services (LLM, embeddings, core memory) are bound
lazily with graceful degradation so the plugin boots with zero external infra.
"""

from __future__ import annotations

from .plugin import BaselithTwinPlugin

__all__ = ["BaselithTwinPlugin"]

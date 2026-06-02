"""RedAgent orchestrator package.

Drives the scan lifecycle:

  ScanRequest
    -> GuardrailPipeline (SSRF, scope, intensity)
    -> [HITL approval if active/intrusive]
    -> for scanner in selected: SandboxRunner -> Scanner.run -> Findings
    -> Persistence (Postgres) + VulnerabilityGraph (FalkorDB)
    -> Audit + observability events

Pipeline is deterministic for the MVP; LLM-driven planning over the
attack-surface graph is a fase 2 extension hook (see the planner).

Split across submodules to respect the 500-line file cap:

* ``_agent`` — the :class:`RedAgent` orchestrator class.
* ``_scan_loop`` — the scan-execution loop and HITL-approval wait.
* ``_planner_factory`` — default-planner selection.

``from plugins.red_agent.agent import RedAgent`` continues to work.
"""

from __future__ import annotations

from plugins.red_agent.agent._agent import RedAgent
from plugins.red_agent.agent._planner_factory import _build_default_planner

__all__ = ["RedAgent", "_build_default_planner"]

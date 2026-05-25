"""Adversary emulation module.

Runs ATT&CK-mapped techniques against authorized endpoints to test
defensive coverage. Two execution backends are supported:

* :mod:`atomic_loader` — loads `Atomic Red Team
  <https://github.com/redcanaryco/atomic-red-team>`_ YAML test
  definitions and surfaces them as a structured
  :class:`EmulationPlan`. The plan is dispatched through the
  endpoint daemon's existing local executor (sandbox-exec / landlock
  on the host) so emulation traffic stays within the authorized
  scope and is auditable end-to-end.
* :mod:`caldera_client` — submits operations to a MITRE Caldera
  server and polls until the operation completes. Used when the
  customer prefers a server-driven C2 plan over Red-Agent-issued
  Atomic dispatches.

Either backend converts its results into :class:`Finding` records via
:mod:`result_to_findings`, so the rest of the orchestrator
(enrichers, persistence, UI) treats emulation outcomes the same way
it treats scan findings — flowing through the same triage, audit,
and ATT&CK mapping pipelines.
"""

from plugins.red_agent.adversary.plan import (
    AtomicTest,
    EmulationPlan,
    EmulationStep,
    PlanLoadError,
)
from plugins.red_agent.adversary.result import EmulationOutcome, EmulationResult

__all__ = [
    "AtomicTest",
    "EmulationOutcome",
    "EmulationPlan",
    "EmulationResult",
    "EmulationStep",
    "PlanLoadError",
]

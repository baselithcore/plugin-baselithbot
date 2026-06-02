"""LLM-driven attack planner.

Drop-in replacement for :class:`ChainingPlanner` selected when
``RedAgentConfig.llm_planner_enabled`` is on and the engagement
autonomy reaches at least ``execute_active``.

The planner asks an LLM for the next ``PlannerStep`` given the goal,
state, and findings observed so far. The orchestrator + critic still
execute and vet every step — the LLM never sees credentials, scanner
raw bytes, or sandbox state, and never invokes scanners directly.

Safety contract enforced inside ``plan()``:

* **autonomy cap** — proposed intensity capped to
  ``state.autonomy_max_intensity`` before the step is even returned.
  The critic's :class:`RoECritic` is the second wall, but rejecting
  here lets us emit ``planner_hypothesis`` rejections cleanly.
* **token budget** — sum of input+output tokens across calls is
  bounded by ``llm_planner_max_tokens_per_scan``. Overflow halts the
  chain (``planner_llm_fallback`` audit event).
* **redaction** — finding ``evidence`` and ``raw`` blobs are passed
  through :func:`redact_secrets` before serialization.
* **provider fallback** — any client error / parse failure / schema
  violation flips a sticky fallback flag and delegates the rest of
  the scan to ``fallback_planner`` (typically :class:`ChainingPlanner`).

The implementation is split into focused submodules:

* ``_redaction`` — secret patterns + :func:`redact_secrets`.
* ``_client`` — the :class:`LLMPlannerClient` protocol and the
  :class:`CoreLLMServiceClient` adapter.
* ``_prompt`` — planner settings, prompt construction, response parsing.
* ``_planner`` — :class:`LLMReasoningPlanner` and :func:`build_llm_planner`.
"""

from __future__ import annotations

from plugins.red_agent.llm_planner._client import (
    CoreLLMServiceClient,
    LLMPlannerClient,
)
from plugins.red_agent.llm_planner._planner import (
    LLMReasoningPlanner,
    build_llm_planner,
)
from plugins.red_agent.llm_planner._prompt import _LLMPlannerSettings
from plugins.red_agent.llm_planner._redaction import redact_secrets

__all__ = [
    "CoreLLMServiceClient",
    "LLMPlannerClient",
    "LLMReasoningPlanner",
    "_LLMPlannerSettings",
    "build_llm_planner",
    "redact_secrets",
]

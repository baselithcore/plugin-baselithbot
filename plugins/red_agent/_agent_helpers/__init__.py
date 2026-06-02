"""Pure helpers extracted from ``agent.py`` to keep that module under the
500-line file cap. None of these depend on ``RedAgent`` instance state —
everything they need is passed in explicitly.

Split into focused submodules:

* ``_scanners`` — request filtering, scanner dispatch, payload bounding,
  validated-impact filtering.
* ``_enrichment`` — the full post-scanner enrichment pipeline and the
  individual enricher passes (threat intel, ML FP, LLM triage, dedup).

The post-pipeline helpers (``run_vex_suppression`` et al.) are re-exported
here so callers that historically imported them from ``_agent_helpers``
keep working.
"""

from __future__ import annotations

from plugins.red_agent._agent_helpers._enrichment import (
    run_llm_triage,
    run_ml_fp_classifier,
    run_post_scanner_pipeline,
    run_semantic_dedupe,
    run_threat_intel_enrichers,
)
from plugins.red_agent._agent_helpers._scanners import (
    apply_validated_impact,
    execute_scanner,
    filter_request_scanners,
    scanner_error_finding,
    truncate_payload,
)
from plugins.red_agent._post_pipeline import (
    run_compliance_mapping,
    run_exploit_validation,
    run_reachability,
    run_risk_scoring,
    run_vex_suppression,
)

__all__ = [
    "apply_validated_impact",
    "execute_scanner",
    "filter_request_scanners",
    "run_compliance_mapping",
    "run_exploit_validation",
    "run_llm_triage",
    "run_ml_fp_classifier",
    "run_post_scanner_pipeline",
    "run_reachability",
    "run_risk_scoring",
    "run_semantic_dedupe",
    "run_threat_intel_enrichers",
    "run_vex_suppression",
    "scanner_error_finding",
    "truncate_payload",
]

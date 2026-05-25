"""VPR-style risk scoring enricher.

Tenable's Vulnerability Priority Rating (VPR) and Qualys's QDS combine
CVSS with real-world exploitation context (EPSS / KEV), exposure, and
asset criticality to produce a single 0-10 score that triages
remediation queue ordering far better than CVSS alone.

This enricher implements an MVP variant. The score is purely
multiplicative and stays interpretable:

    risk_score = clamp(0, 10, base
                              * kev_multiplier
                              * epss_multiplier
                              * exposure_multiplier
                              * reachability_multiplier
                              * asset_multiplier)

Each multiplier defaults to ``1.0`` when its input is missing, so the
score degrades gracefully back to CVSS for findings without enriched
context. The band is a coarse label suitable for UI bucketing.

Inputs read from ``Finding.evidence``:

* ``kev_listed: bool`` (set by :class:`EpssKevEnricher`)
* ``epss_score: float`` (0..1, set by :class:`EpssKevEnricher`)
* ``reachable: bool`` (set by :class:`ReachabilityEnricher`)
* ``confirmed: bool`` (scanner-marked exploitation, e.g. sqlmap)

Inputs read from ``Target.metadata`` via the orchestrator:

* ``asset_criticality: "low" | "medium" | "high" | "crown_jewel"``
* ``exposure: "internet" | "internal" | "isolated"``
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding, Severity

logger = get_logger(__name__)


_SEVERITY_BASE: dict[Severity, float] = {
    Severity.INFO: 1.0,
    Severity.LOW: 3.0,
    Severity.MEDIUM: 5.0,
    Severity.HIGH: 7.5,
    Severity.CRITICAL: 9.5,
}

_ASSET_MULT: dict[str, float] = {
    "low": 0.7,
    "medium": 1.0,
    "high": 1.3,
    "crown_jewel": 1.5,
}

_EXPOSURE_MULT: dict[str, float] = {
    "internet": 1.2,
    "internal": 0.9,
    "isolated": 0.7,
}


class RiskScoringEnricher:
    """Compute a unified 0..10 risk score per finding."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        kev_multiplier: float = 1.5,
        max_epss_multiplier: float = 1.5,
        confirmed_multiplier: float = 1.3,
    ) -> None:
        self.enabled = enabled
        self.kev_multiplier = kev_multiplier
        self.max_epss_multiplier = max_epss_multiplier
        self.confirmed_multiplier = confirmed_multiplier

    def enrich(
        self,
        findings: list[Finding],
        *,
        asset_metadata: dict[str, Any] | None = None,
    ) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        meta = asset_metadata or {}
        # Both default to neutral (1.0). Multipliers only kick in when
        # the operator has tagged the asset; otherwise the score stays
        # interpretable as plain CVSS × KEV/EPSS/reachability.
        raw_crit = meta.get("asset_criticality")
        raw_exp = meta.get("exposure")
        asset_criticality = str(raw_crit).lower() if isinstance(raw_crit, str) else ""
        exposure = str(raw_exp).lower() if isinstance(raw_exp, str) else ""
        asset_mult = _ASSET_MULT.get(asset_criticality, 1.0)
        exposure_mult = _EXPOSURE_MULT.get(exposure, 1.0)
        for f in findings:
            score = self._score_finding(
                f, asset_mult=asset_mult, exposure_mult=exposure_mult
            )
            f.risk_score = score
            if isinstance(f.evidence, dict):
                f.evidence["risk_score"] = score
                f.evidence["risk_band"] = _band(score)
                f.evidence["risk_inputs"] = {
                    "asset_criticality": asset_criticality or None,
                    "exposure": exposure or None,
                }
        return findings

    def _score_finding(
        self, f: Finding, *, asset_mult: float, exposure_mult: float
    ) -> float:
        base = _base_score(f)
        kev_mult = (
            self.kev_multiplier
            if isinstance(f.evidence, dict) and f.evidence.get("kev_listed")
            else 1.0
        )
        epss_mult = self._epss_multiplier(f)
        reachable_mult = _reachability_multiplier(f)
        confirmed_mult = (
            self.confirmed_multiplier
            if isinstance(f.evidence, dict) and f.evidence.get("confirmed")
            else 1.0
        )
        raw = (
            base
            * kev_mult
            * epss_mult
            * reachable_mult
            * confirmed_mult
            * asset_mult
            * exposure_mult
        )
        return round(max(0.0, min(10.0, raw)), 2)

    def _epss_multiplier(self, f: Finding) -> float:
        if not isinstance(f.evidence, dict):
            return 1.0
        epss = f.evidence.get("epss_score")
        if epss is None:
            return 1.0
        try:
            value = float(epss)
        except (TypeError, ValueError):
            return 1.0
        value = max(0.0, min(1.0, value))
        return 1.0 + (self.max_epss_multiplier - 1.0) * value


def _base_score(f: Finding) -> float:
    if f.cvss_score is not None and f.cvss_score >= 0:
        return float(f.cvss_score)
    return _SEVERITY_BASE.get(f.severity, 5.0)


def _reachability_multiplier(f: Finding) -> float:
    if not isinstance(f.evidence, dict):
        return 1.0
    if "reachable" not in f.evidence:
        return 1.0
    reachable = f.evidence.get("reachable")
    if reachable is True:
        return 1.2
    if reachable is False:
        return 0.5
    return 1.0


def _band(score: float) -> str:
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score >= 2.0:
        return "low"
    return "info"

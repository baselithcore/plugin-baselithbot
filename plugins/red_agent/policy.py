"""Runtime policy editing for the Red Agent plugin.

Defines which RedAgentConfig fields are operator-editable at runtime
(via the UI) and the validation/apply logic. Secrets, host/port and
sandbox/graph backend selection remain env-only.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from plugins.red_agent.config import RedAgentConfig

# Whitelist of fields that may be edited at runtime via the API.
# Secrets, network endpoints, and process-bound settings are excluded.
EDITABLE_FIELDS: frozenset[str] = frozenset(
    {
        "scope_allowlist",
        "bug_bounty_mode",
        "bug_bounty_program_id",
        "allow_internal_targets",
        "require_hitl_for_active",
        "max_concurrent_scans",
        "audit_retention_days",
        "enabled_scanners",
        "scanner_timeouts",
        "multi_step_chains",
        "chain_max_iterations",
        "validated_impact_only",
        "validated_impact_min_cvss",
        "epss_kev_enricher_enabled",
        "epss_kev_bump_severity_on_kev",
        "epss_kev_high_epss_threshold",
        "attack_mapper_enabled",
        "osv_enricher_enabled",
        "greynoise_enricher_enabled",
        "reachability_enabled",
        "reachability_drop_unreachable",
        "reachability_drop_max_severity",
        "vex_enabled",
        "vex_suppress_not_affected",
        "vex_suppress_fixed",
        "risk_scoring_enabled",
        "compliance_mapper_enabled",
        "differential_enabled",
        "differential_ttl_seconds",
        "auto_remediation_enabled",
        "webhook_enabled",
        "webhook_min_severity",
        "webhook_in_enabled",
        "webhook_in_require_signature",
        "webhook_replay_protection",
    }
)


def _registered_scanner_names() -> frozenset[str]:
    """Allowed-scanner whitelist sourced from the live REGISTRY.

    Single source of truth: every adapter registered in
    ``plugins.red_agent.scanners.REGISTRY`` is automatically eligible for
    runtime enable/disable + timeout edits via the UI. Avoids drift
    between adapter list and the UI's "allowed scanners" facet.
    """
    from plugins.red_agent.scanners import REGISTRY

    return frozenset(REGISTRY.keys())


ALLOWED_SCANNERS: frozenset[str] = _registered_scanner_names()


class PolicyUpdate(BaseModel):
    """PATCH-style payload — every field optional."""

    scope_allowlist: list[str] | None = None
    bug_bounty_mode: bool | None = None
    bug_bounty_program_id: str | None = None
    allow_internal_targets: bool | None = None
    require_hitl_for_active: bool | None = None
    max_concurrent_scans: int | None = Field(default=None, ge=1, le=64)
    audit_retention_days: int | None = Field(default=None, ge=1, le=3650)
    enabled_scanners: list[str] | None = None
    scanner_timeouts: dict[str, int] | None = None
    multi_step_chains: bool | None = None
    chain_max_iterations: int | None = Field(default=None, ge=1, le=20)
    validated_impact_only: bool | None = None
    validated_impact_min_cvss: float | None = Field(default=None, ge=0.0, le=10.0)
    epss_kev_enricher_enabled: bool | None = None
    epss_kev_bump_severity_on_kev: bool | None = None
    epss_kev_high_epss_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    attack_mapper_enabled: bool | None = None
    osv_enricher_enabled: bool | None = None
    greynoise_enricher_enabled: bool | None = None
    reachability_enabled: bool | None = None
    reachability_drop_unreachable: bool | None = None
    reachability_drop_max_severity: Literal["info", "low", "medium", "high"] | None = (
        None
    )
    vex_enabled: bool | None = None
    vex_suppress_not_affected: bool | None = None
    vex_suppress_fixed: bool | None = None
    risk_scoring_enabled: bool | None = None
    compliance_mapper_enabled: bool | None = None
    differential_enabled: bool | None = None
    differential_ttl_seconds: int | None = Field(default=None, ge=60, le=86400)
    auto_remediation_enabled: bool | None = None
    webhook_enabled: bool | None = None
    webhook_min_severity: (
        Literal["info", "low", "medium", "high", "critical"] | None
    ) = None
    webhook_in_enabled: bool | None = None
    webhook_in_require_signature: bool | None = None
    webhook_replay_protection: bool | None = None

    @field_validator("scope_allowlist")
    @classmethod
    def _strip_allowlist(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned = [e.strip() for e in v if e and e.strip()]
        # Dedupe preserving order.
        seen: set[str] = set()
        out: list[str] = []
        for e in cleaned:
            if e not in seen:
                seen.add(e)
                out.append(e)
        return out

    @field_validator("enabled_scanners")
    @classmethod
    def _check_scanners(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        allowed = _registered_scanner_names()
        bad = [s for s in v if s not in allowed]
        if bad:
            raise ValueError(f"unknown scanners: {bad}")
        return list(dict.fromkeys(v))

    @field_validator("scanner_timeouts")
    @classmethod
    def _check_timeouts(cls, v: dict[str, int] | None) -> dict[str, int] | None:
        if v is None:
            return None
        allowed = _registered_scanner_names()
        for k, secs in v.items():
            if k not in allowed:
                raise ValueError(f"unknown scanner: {k}")
            if not (1 <= secs <= 86400):
                raise ValueError(f"timeout out of range for {k}")
        return v


def overrides_from_update(update: PolicyUpdate) -> dict[str, Any]:
    """Drop None fields so we only persist what the operator changed."""
    return {k: v for k, v in update.model_dump().items() if v is not None}


def apply_overrides(config: RedAgentConfig, overrides: dict[str, Any]) -> None:
    """Mutate the live RedAgentConfig in place with persisted overrides.

    Unknown / non-editable keys are silently ignored to keep forward
    compatibility when a deployment downgrades the plugin.
    """
    for key, value in overrides.items():
        if key not in EDITABLE_FIELDS:
            continue
        try:
            setattr(config, key, value)
        except Exception:  # noqa: BLE001 — pydantic validation
            continue


def snapshot(config: RedAgentConfig) -> dict[str, Any]:
    """Return the effective policy view consumed by the UI."""
    return {
        "scope_allowlist": list(config.scope_allowlist),
        "bug_bounty_mode": config.bug_bounty_mode,
        "bug_bounty_program_id": config.bug_bounty_program_id,
        "allow_internal_targets": config.allow_internal_targets,
        "require_hitl_for_active": config.require_hitl_for_active,
        "max_concurrent_scans": config.max_concurrent_scans,
        "enabled_scanners": list(config.enabled_scanners),
        "scanner_timeouts": dict(config.scanner_timeouts),
        "audit_retention_days": config.audit_retention_days,
        "sandbox_provider": config.sandbox_provider,
        "graph_backend": config.graph_backend,
        "multi_step_chains": config.multi_step_chains,
        "chain_max_iterations": config.chain_max_iterations,
        "validated_impact_only": config.validated_impact_only,
        "validated_impact_min_cvss": config.validated_impact_min_cvss,
        "epss_kev_enricher_enabled": config.epss_kev_enricher_enabled,
        "epss_kev_bump_severity_on_kev": config.epss_kev_bump_severity_on_kev,
        "epss_kev_high_epss_threshold": config.epss_kev_high_epss_threshold,
        "attack_mapper_enabled": config.attack_mapper_enabled,
        "osv_enricher_enabled": config.osv_enricher_enabled,
        "greynoise_enricher_enabled": config.greynoise_enricher_enabled,
        "reachability_enabled": config.reachability_enabled,
        "reachability_drop_unreachable": config.reachability_drop_unreachable,
        "reachability_drop_max_severity": config.reachability_drop_max_severity,
        "vex_enabled": config.vex_enabled,
        "vex_suppress_not_affected": config.vex_suppress_not_affected,
        "vex_suppress_fixed": config.vex_suppress_fixed,
        "risk_scoring_enabled": config.risk_scoring_enabled,
        "compliance_mapper_enabled": config.compliance_mapper_enabled,
        "differential_enabled": config.differential_enabled,
        "differential_ttl_seconds": config.differential_ttl_seconds,
        "auto_remediation_enabled": config.auto_remediation_enabled,
        "webhook_enabled": config.webhook_enabled,
        "webhook_url_configured": bool(config.webhook_url),
        "webhook_min_severity": config.webhook_min_severity,
        "webhook_in_enabled": config.webhook_in_enabled,
        "webhook_in_require_signature": config.webhook_in_require_signature,
        "webhook_replay_protection": config.webhook_replay_protection,
        "editable_fields": sorted(EDITABLE_FIELDS),
        "allowed_scanners": sorted(_registered_scanner_names()),
    }

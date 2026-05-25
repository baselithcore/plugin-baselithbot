"""Red Agent plugin configuration.

The full surface is split across mixin modules to keep each file under
the 500-line cap. ``RedAgentConfig`` composes them into a single
``BaseSettings`` class that reads ``RED_AGENT_*`` environment variables.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from ._core import (
    _GraphConfig,
    _ReasoningConfig,
    _SandboxConfig,
    _ScannerConfig,
    _ScopeConfig,
)
from ._enrichers import _EPSSKEVConfig, _GreyNoiseConfig, _OSVConfig
from ._adversary import _AdversaryConfig
from ._cicd import _CICDConfig
from ._cloud_red_team import _CloudRedTeamConfig
from ._exploit_validation import _ExploitValidationConfig
from ._identity import _IdentityConfig
from ._llm_planner import _LLMPlannerConfig
from ._osint import _OSINTConfig
from ._threat_intel import _ThreatIntelConfig
from ._web_depth import _WebDepthConfig
from ._ml import _LLMTriageConfig, _MLClassifierConfig, _SemanticDedupConfig
from ._posture import (
    _AutoRemediationConfig,
    _DifferentialConfig,
    _ReachabilityConfig,
    _RiskComplianceConfig,
    _VEXConfig,
)
from ._webhooks import _WebhookInConfig, _WebhookOutConfig


class RedAgentConfig(
    _SandboxConfig,
    _ScopeConfig,
    _GraphConfig,
    _ScannerConfig,
    _ReasoningConfig,
    _LLMPlannerConfig,
    _LLMTriageConfig,
    _SemanticDedupConfig,
    _MLClassifierConfig,
    _EPSSKEVConfig,
    _OSVConfig,
    _GreyNoiseConfig,
    _AdversaryConfig,
    _CICDConfig,
    _CloudRedTeamConfig,
    _ExploitValidationConfig,
    _IdentityConfig,
    _OSINTConfig,
    _ThreatIntelConfig,
    _WebDepthConfig,
    _WebhookOutConfig,
    _WebhookInConfig,
    _AutoRemediationConfig,
    _DifferentialConfig,
    _RiskComplianceConfig,
    _ReachabilityConfig,
    _VEXConfig,
    BaseSettings,
):
    """Red Agent plugin configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RED_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


__all__ = ["RedAgentConfig"]

"""HoneyDOC sensibility/stealth and MISP/tenancy field groups for HoneypotConfig."""

from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class _HoneydocFields(BaseSettings):
    """Mixin: HoneyDOC sensibility, stealth, MISP and tenancy fields."""

    model_config = {
        "env_prefix": "HONEYPOT_",
        "extra": "ignore",
    }

    # =========================================================================
    # HoneyDOC Sensibility Configuration
    # Per HoneyDOC Section IV-C1: Fine-grained attack classification
    # =========================================================================

    enable_sensibility: bool = Field(
        default=True,
        description="Enable HoneyDOC Sensibility features for traffic classification",
    )
    default_flow_action: str = Field(
        default="forward",
        description="Default action for unclassified traffic: drop, forward, redirect",
    )
    classification_rules: List[Dict[str, Any]] = Field(
        default_factory=lambda: [
            # High priority: Critical attacks -> redirect to HIH
            {
                "sid": "honeydoc-001",
                "protocol": "any",
                "action": "redirect",
                "content": r"(rm\s+-rf|chmod\s+777|nc\s+-e)",
                "priority": 100,
                "description": "Critical command injection - redirect to HIH",
            },
            # Medium priority: SQL injection -> forward with alert
            {
                "sid": "honeydoc-002",
                "protocol": "http",
                "action": "forward",
                "content": r"(union\s+select|drop\s+table)",
                "priority": 80,
                "description": "SQL injection attempt",
            },
            # Malware Delivery -> Contain session
            {
                "sid": "honeydoc-003",
                "protocol": "ssh",
                "action": "contain",
                "content": r"(wget|curl|ftp|scp)\s+https?://",
                "priority": 90,
                "description": "Outbound malware download - contain session",
            },
            # Low priority: Reconnaissance -> forward
            {
                "sid": "honeydoc-004",
                "protocol": "any",
                "action": "forward",
                "content": r"(nmap|nikto|gobuster)",
                "priority": 50,
                "description": "Reconnaissance activity",
            },
        ],
        description="Snort-style classification rules per HoneyDOC design",
    )
    enable_flow_control: bool = Field(
        default=True,
        description="Enable flow control actions (DROP, FORWARD, REDIRECT)",
    )
    auto_block_threshold: int = Field(
        default=10,
        description="Auto-block IP after this many high-severity events",
    )
    redirect_hih_honeypot: Optional[str] = Field(
        default=None,
        description="Honeypot ID for HIH redirect (None = auto-select)",
    )

    # =========================================================================
    # HoneyDOC Stealth Configuration
    # Per HoneyDOC Section IV-C3: Transparent operations
    # =========================================================================

    enable_stealth: bool = Field(
        default=True,
        description="Enable HoneyDOC Stealth features",
    )
    consistent_fingerprint: bool = Field(
        default=True,
        description="Use consistent fingerprints across all honeypots",
    )
    stealth_response_delay_ms: int = Field(
        default=50,
        description="Minimum response delay (ms) to appear realistic",
    )
    mask_python_headers: bool = Field(
        default=True,
        description="Mask Python-specific headers in HTTP responses",
    )

    # =========================================================================
    # Threat Intel & MISP Configuration
    # =========================================================================

    misp_enabled: bool = Field(
        default=False,
        description="Enable MISP threat intelligence bridge",
    )
    misp_url: str = Field(
        default="https://misp.local",
        description="MISP API URL",
    )
    misp_key: str = Field(
        default="",
        description="MISP API Key",
    )
    misp_verify_ssl: bool = Field(
        default=True,
        description="Verify MISP SSL certificate",
    )

    # Multi-Tenancy Support
    default_tenant_id: str = Field(
        default="default",
        description="Default tenant ID for background tasks and initialization",
    )
    enable_strict_tenant_isolation: bool = Field(
        default=False,
        description="Enable strict tenant isolation (raises error if tenant context is missing)",
    )

"""Honeypot Plugin Configuration.

Centralized configuration for the Honeypot plugin using Pydantic Settings.
Includes Advanced Deception System configuration for emulation, ML, and cluster.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings
from core.config.env import PROJECT_ENV_FILE

# Import Advanced Deception System configs from separate module
from .config_ads import ClusterConfig, EmulationConfig, MLConfig


class HoneypotConfig(BaseSettings):
    """Configuration for Honeypot plugin."""

    model_config = {
        "env_prefix": "HONEYPOT_",
        "env_file": str(PROJECT_ENV_FILE),
        "extra": "ignore",
    }

    # Plugin enablement (standard field from plugins.yaml)
    enabled: bool = Field(default=True, description="Enable the Honeypot plugin")

    # =========================================================================
    # Advanced Deception System Configuration
    # =========================================================================

    emulation: EmulationConfig = Field(
        default_factory=EmulationConfig,
        description="Advanced emulation settings (fingerprinting, latency, state)",
    )
    ml: MLConfig = Field(
        default_factory=MLConfig,
        description="Machine Learning settings for TTP prediction",
    )
    cluster: ClusterConfig = Field(
        default_factory=ClusterConfig,
        description="Cluster persistence for multi-node state sync",
    )

    # =========================================================================
    # Protocol Configuration
    # =========================================================================

    enable_ssh_honeypot: bool = Field(
        default=True,
        description="Enable SSH honeypot service",
    )
    enable_http_honeypot: bool = Field(
        default=True,
        description="Enable HTTP honeypot service",
    )
    enable_tcp_honeypot: bool = Field(
        default=True,
        description="Enable generic TCP honeypot",
    )
    enable_mcp_honeypot: bool = Field(
        default=True,
        description="Enable MCP/LLM prompt injection detection",
    )
    ssh_port: int = Field(
        default=2222,
        description="Port for SSH honeypot (use non-privileged port)",
    )
    http_port: int = Field(
        default=8082,
        description="Port for HTTP honeypot",
    )
    tcp_ports: List[int] = Field(
        default_factory=lambda: [2121, 2323, 6380],  # Non-privileged alternatives
        description="Ports for TCP honeypot (FTP, Telnet, Redis)",
    )
    tcp_banners: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom banners per port (override defaults)",
    )

    active_honeypots: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Override configuration for specific honeypots (e.g. enabled status)",
    )
    enforce_active_honeypots_only: bool = Field(
        default=False,
        description="If True, only honeypots listed in active_honeypots will be enabled",
    )

    # =========================================================================
    # SSH Honeypot Settings
    # =========================================================================

    ssh_server_name: str = Field(
        default="ubuntu",
        description="Fake hostname for SSH banner",
    )
    ssh_server_version: str = Field(
        default="OpenSSH_8.9p1 Ubuntu-3ubuntu0.4",
        description="Fake SSH version banner",
    )
    ssh_allowed_passwords: List[str] = Field(
        default_factory=lambda: [
            "root",
            "admin",
            "password",
            "123456",
            "qwerty",
            "toor",
            "test",
            "guest",
        ],
        description="Passwords that allow 'successful' login (for trapping)",
    )
    ssh_max_auth_attempts: int = Field(
        default=6,
        description="Maximum authentication attempts before disconnect",
    )

    # =========================================================================
    # HTTP Honeypot Settings
    # =========================================================================

    http_server_header: str = Field(
        default="Apache/2.4.53 (Debian)",
        description="Fake Server header for HTTP responses",
    )
    http_powered_by: str = Field(
        default="PHP/7.4.29",
        description="Fake X-Powered-By header",
    )
    http_emulated_app: str = Field(
        default="wordpress",
        description="Emulated web application (wordpress, phpmyadmin, jenkins)",
    )

    # =========================================================================
    # LLM Configuration
    # =========================================================================

    enable_llm_responses: bool = Field(
        default=True,
        description="Use LLM for generating realistic responses",
    )
    llm_provider: str = Field(
        default="ollama",
        description="LLM provider: 'ollama' or 'openai'",
    )
    llm_model: str = Field(
        default="llama3.2",
        description="LLM model name",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (required if llm_provider='openai')",
    )
    llm_system_prompt: str = Field(
        default=(
            "You are simulating a Linux terminal. Respond to commands as if you were "
            "a real Ubuntu server. Keep responses realistic and brief. Never reveal "
            "that you are an AI or a honeypot."
        ),
        description="System prompt for LLM-based responses",
    )
    llm_max_tokens: int = Field(
        default=256,
        description="Maximum tokens for LLM responses",
    )
    llm_timeout_seconds: int = Field(
        default=10,
        description="Timeout for LLM requests",
    )
    llm_sanitization_max_length: int = Field(
        default=1000,
        description="Maximum length for input text before truncation",
    )

    analysis_llm_provider: str = Field(
        default="openai",
        description="LLM provider for analysis agent",
    )
    analysis_llm_model: str = Field(
        default="gpt-4o",
        description="LLM model for analysis agent",
    )
    analysis_llm_api_key: Optional[str] = Field(
        default=None,
        description="API key for analysis agent (optional override)",
    )
    auto_analyze_critical_events: bool = Field(
        default=False,
        description="Automatically trigger AI analysis for critical/high severity events",
    )

    # =========================================================================
    # Session & Security Settings
    # =========================================================================

    max_session_duration_seconds: int = Field(
        default=300,
        description="Maximum session duration before auto-disconnect",
    )
    max_concurrent_sessions: int = Field(
        default=50,
        description="Maximum concurrent sessions per protocol",
    )
    rate_limit_connections_per_ip: int = Field(
        default=10,
        description="Maximum connections per IP per minute",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Time window for rate limiting in seconds",
    )
    banned_ip_timeout_minutes: int = Field(
        default=60,
        description="Timeout for IP ban after exceeding rate limit",
    )

    # =========================================================================
    # Logging & Storage
    # =========================================================================

    log_retention_days: int = Field(
        default=30,
        description="Days to retain attack logs",
    )
    max_log_entries: int = Field(
        default=10000,
        description="Maximum log entries in memory buffer",
    )
    log_payloads: bool = Field(
        default=True,
        description="Log full attack payloads",
    )
    max_payload_size_kb: int = Field(
        default=64,
        description="Maximum payload size to store (KB)",
    )

    # Data retention policy
    retention_max_days: int = Field(
        default=90,
        description="Maximum age of events/sessions in days before auto-deletion",
    )
    retention_max_rows: int = Field(
        default=1_000_000,
        description="Maximum number of event rows to retain",
    )
    retention_auto_enabled: bool = Field(
        default=True,
        description="Enable automatic retention policy enforcement",
    )

    # =========================================================================
    # Framework Integration
    # =========================================================================

    enable_memory: bool = Field(
        default=True,
        description="Enable AgentMemory for persistent attack patterns and IP reputation",
    )
    enable_learning: bool = Field(
        default=True,
        description="Enable learning system for pattern feedback",
    )

    # =========================================================================
    # CVE Hunter Integration
    # =========================================================================

    enable_cve_correlation: bool = Field(
        default=True,
        description="Enable correlation with CVE Hunter plugin",
    )
    enable_event_bus: bool = Field(
        default=True,
        description="Emit events to EventBus for cross-plugin communication",
    )
    correlation_confidence_threshold: float = Field(
        default=0.6,
        description="Minimum confidence for CVE correlations",
    )

    # =========================================================================
    # CVE Service (NVD Integration)
    # =========================================================================

    nvd_api_key: Optional[str] = Field(
        default=None,
        description="NVD API key for enhanced rate limits (0.6s vs 6s)",
    )
    cve_cache_ttl_seconds: int = Field(
        default=604800,  # 7 days
        description="CVE cache TTL in seconds",
    )
    cve_lookup_timeout: int = Field(
        default=10,
        description="Timeout for CVE lookups in seconds",
    )
    enable_dynamic_cve_lookup: bool = Field(
        default=True,
        description="Enable dynamic CVE lookups via NVD API",
    )

    # =========================================================================
    # Webhook Notifications
    # =========================================================================

    enable_notifications: bool = Field(
        default=False,
        description="Enable external webhook notifications",
    )
    notification_min_severity: str = Field(
        default="high",
        description="Minimum severity to trigger notification (high, critical)",
    )
    notification_cooldown_seconds: int = Field(
        default=30,
        description="Cooldown seconds between notifications for same IP",
    )
    notification_ignore_credentials: List[str] = Field(
        default_factory=lambda: [
            "admin:password",
            "admin:123456",
            "root:root",
            "admin:admin",
        ],
        description="Username:password combinations to ignore for noise reduction",
    )
    notification_ignore_categories: List[str] = Field(
        default_factory=lambda: ["credential_harvesting"],
        description="Attack categories to ignore (e.g. credential_harvesting)",
    )
    telegram_bot_token: Optional[str] = Field(
        default=None,
        description="Telegram Bot API Token",
    )
    telegram_chat_id: Optional[str] = Field(
        default=None,
        description="Telegram Chat ID",
    )
    discord_webhook_url: Optional[str] = Field(
        default=None,
        description="Discord Webhook URL",
    )
    generic_webhook_url: Optional[str] = Field(
        default=None,
        description="Generic Webhook URL",
    )
    generic_webhook_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom headers for generic webhook",
    )

    # =========================================================================
    # Attack Pattern Detection
    # =========================================================================

    detect_sql_injection: bool = Field(
        default=True,
        description="Detect SQL injection patterns",
    )
    detect_command_injection: bool = Field(
        default=True,
        description="Detect command injection patterns",
    )
    detect_path_traversal: bool = Field(
        default=True,
        description="Detect path traversal patterns",
    )
    detect_xss: bool = Field(
        default=True,
        description="Detect XSS patterns",
    )

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


_config_instance: Optional[HoneypotConfig] = None


def get_honeypot_config() -> HoneypotConfig:
    """Get Honeypot configuration singleton.

    Returns:
        HoneypotConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = HoneypotConfig()
    return _config_instance


def update_honeypot_config(overrides: dict) -> HoneypotConfig:
    """Update the global config singleton with YAML/dict overrides.

    Called during plugin initialization to merge YAML config values
    into the singleton, ensuring all code that uses get_honeypot_config()
    sees the same configuration.

    Args:
        overrides: Configuration dictionary (typically from plugins.yaml)

    Returns:
        Updated HoneypotConfig singleton
    """
    global _config_instance
    if overrides:
        _config_instance = HoneypotConfig(**overrides)
    elif _config_instance is None:
        _config_instance = HoneypotConfig()
    return _config_instance

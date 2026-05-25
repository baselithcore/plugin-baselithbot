"""CVE Hunter Configuration.

Centralized configuration for the CVE Hunter plugin using Pydantic Settings.
"""

from typing import Any, Dict, List, Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from core.config.env import PROJECT_ENV_FILE


class CVEHunterConfig(BaseSettings):
    """Configuration for CVE Hunter plugin."""

    model_config = {
        "env_prefix": "CVE_HUNTER_",
        "env_file": str(PROJECT_ENV_FILE),
        "extra": "ignore",
    }

    # Plugin enablement
    enabled: bool = Field(default=True, description="Enable the CVE Hunter plugin")

    # Scanning configuration
    scan_interval_minutes: int = Field(
        default=30,
        description="Interval between automatic scans in minutes",
    )
    max_concurrent_scans: int = Field(
        default=3,
        description="Maximum number of concurrent scan agents",
    )
    scan_timeout_seconds: int = Field(
        default=300,
        description="Timeout for individual scan operations",
    )

    # Data sources
    nvd_api_key: Optional[SecretStr] = Field(
        default=None,
        description="NVD API key for higher rate limits",
    )
    nvd_base_url: str = Field(
        default="https://services.nvd.nist.gov/rest/json/cves/2.0",
        description="NVD API base URL",
    )
    cve_org_url: str = Field(
        default="https://cveawg.mitre.org/api/cve",
        description="CVE.org API URL",
    )
    github_advisories_url: str = Field(
        default="https://api.github.com/advisories",
        description="GitHub Security Advisories API URL",
    )
    cisa_kev_url: str = Field(
        default="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        description="CISA Known Exploited Vulnerabilities catalog URL",
    )
    osv_api_url: str = Field(
        default="https://api.osv.dev/v1/query",
        description="OSV (Open Source Vulnerabilities) API URL",
    )
    exploitdb_url: str = Field(
        default="https://www.exploit-db.com/search",
        description="ExploitDB search URL",
    )

    # Rate limiting
    requests_per_minute: int = Field(
        default=30,
        description="Maximum requests per minute to external APIs",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache TTL for CVE data in seconds",
    )

    # Severity thresholds
    critical_cvss_threshold: float = Field(
        default=9.0,
        description="CVSS threshold for CRITICAL severity",
    )
    high_cvss_threshold: float = Field(
        default=7.0,
        description="CVSS threshold for HIGH severity",
    )
    medium_cvss_threshold: float = Field(
        default=4.0,
        description="CVSS threshold for MEDIUM severity",
    )

    # Alert configuration
    alert_on_critical: bool = Field(
        default=True,
        description="Generate alerts for CRITICAL CVEs",
    )
    alert_on_high: bool = Field(
        default=True,
        description="Generate alerts for HIGH CVEs",
    )

    # Discovery agent settings
    enable_discovery: bool = Field(
        default=True,
        description="Enable zero-day discovery agent",
    )
    discovery_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence for discovery alerts",
    )

    # SAST (Static Application Security Testing) settings
    enable_sast: bool = Field(
        default=False,
        description="Enable local SAST scanning for code repositories",
    )
    sast_paths: List[str] = Field(
        default_factory=list,
        description="List of local paths to scan for SAST",
    )
    sast_exclude_globs: List[str] = Field(
        default_factory=lambda: [
            "**/.git/**",
            "**/node_modules/**",
            "**/dist/**",
            "**/build/**",
            "**/.venv/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/.pytest_cache/**",
        ],
        description="Glob patterns to exclude from SAST scans",
    )
    sast_max_file_size_kb: int = Field(
        default=512,
        description="Skip files larger than this size (KB) during SAST scans",
    )
    sast_max_files: int = Field(
        default=5000,
        description="Maximum number of files to scan in a single SAST run",
    )

    # DAST (Dynamic Application Security Testing) settings
    enable_dast: bool = Field(
        default=False,
        description="Enable DAST scanning against configured targets",
    )
    dast_targets: List[str] = Field(
        default_factory=list,
        description="List of base URLs for DAST scanning",
    )
    dast_request_timeout_seconds: int = Field(
        default=10,
        description="Timeout for DAST HTTP requests",
    )
    dast_max_pages: int = Field(
        default=50,
        description="Maximum pages to crawl per target during DAST scans",
    )

    # Semgrep integration (SAST enhancement)
    enable_semgrep: bool = Field(
        default=False,
        description="Enable Semgrep for deeper SAST scanning",
    )
    semgrep_rules: List[str] = Field(
        default_factory=list,
        description="Semgrep rule identifiers or config URLs",
    )
    semgrep_config_path: Optional[str] = Field(
        default=None,
        description="Local Semgrep config file path",
    )
    semgrep_timeout_seconds: int = Field(
        default=120,
        description="Timeout for Semgrep execution",
    )

    # ZAP integration (DAST enhancement)
    enable_zap: bool = Field(
        default=False,
        description="Enable OWASP ZAP for deeper DAST scanning",
    )
    zap_command: str = Field(
        default="zap-baseline.py",
        description="ZAP CLI command in PATH (zap-baseline.py or zap-full-scan.py)",
    )
    zap_args: List[str] = Field(
        default_factory=list,
        description="Additional ZAP CLI arguments",
    )
    zap_timeout_seconds: int = Field(
        default=600,
        description="Timeout for ZAP execution",
    )

    # CodeQL integration (SAST enhancement)
    enable_codeql: bool = Field(
        default=False,
        description="Enable CodeQL for deeper SAST scanning",
    )
    codeql_cli_path: str = Field(
        default="codeql",
        description="CodeQL CLI command in PATH",
    )
    codeql_database_path: Optional[str] = Field(
        default=None,
        description="Path to CodeQL database to analyze",
    )
    codeql_query_suite: str = Field(
        default="security-and-quality",
        description="CodeQL query suite to run",
    )
    codeql_autocreate: bool = Field(
        default=False,
        description="Auto-create CodeQL database if missing",
    )
    codeql_source_root: Optional[str] = Field(
        default=None,
        description="Source root for auto-creating CodeQL database",
    )
    codeql_languages: List[str] = Field(
        default_factory=list,
        description="Languages for CodeQL database create (e.g., python,javascript)",
    )
    codeql_timeout_seconds: int = Field(
        default=900,
        description="Timeout for CodeQL execution",
    )

    # Sources to scan
    enabled_sources: List[str] = Field(
        default_factory=lambda: ["nvd", "github", "cisa_kev", "osv"],
        description="List of enabled CVE sources",
    )

    # =========================================================================
    # Multi-Tenancy Configuration
    # =========================================================================

    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant ID for multi-tenancy isolation. If None, uses default tenant.",
    )
    isolation_mode: str = Field(
        default="shared",
        description="Isolation mode: 'shared', 'dedicated', or 'hybrid'",
    )
    namespace: Optional[str] = Field(
        default=None,
        description="Namespace for resource isolation (e.g., database schema prefix)",
    )

    # =========================================================================
    # Core Framework Integration (Phase 1)
    # =========================================================================

    # Memory integration
    enable_memory: bool = Field(
        default=True,
        description="Enable AgentMemory for CVE knowledge persistence",
    )
    memory_ttl_days: int = Field(
        default=30,
        description="Days to retain CVE memories before compression",
    )
    memory_working_limit: int = Field(
        default=100,
        description="Maximum items in working memory",
    )

    # Event system integration
    enable_events: bool = Field(
        default=True,
        description="Enable EventBus for cross-agent communication",
    )

    # Learning integration
    enable_learning: bool = Field(
        default=True,
        description="Enable ExperienceReplay for continuous learning",
    )
    experience_buffer_size: int = Field(
        default=1000,
        description="Maximum experiences to store in replay buffer",
    )
    learning_priority_alpha: float = Field(
        default=0.6,
        description="Priority exponent for experience sampling (0=uniform, 1=full priority)",
    )

    # Self-correction integration
    enable_self_correction: bool = Field(
        default=True,
        description="Enable SelfCorrector for analysis validation",
    )
    max_correction_iterations: int = Field(
        default=2,
        description="Maximum self-correction iterations per analysis",
    )


_config_instance: Optional[CVEHunterConfig] = None


def get_cve_hunter_config() -> CVEHunterConfig:
    """Get CVE Hunter configuration singleton.

    Returns:
        CVEHunterConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = CVEHunterConfig()
    return _config_instance


def update_cve_hunter_config(overrides: Optional[Dict[str, Any]]) -> CVEHunterConfig:
    """Merge YAML/dict overrides into the config singleton.

    Env-var values are loaded first by `BaseSettings`; explicit overrides
    take precedence on top of those, mirroring the pattern used by other
    plugins (e.g. honeypot). When `overrides` is empty/None the existing
    singleton is returned unchanged.

    Args:
        overrides: Configuration dictionary, typically from `plugins.yaml`.

    Returns:
        Updated CVEHunterConfig singleton.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = CVEHunterConfig()
    if overrides:
        merged = {**_config_instance.model_dump(), **overrides}
        _config_instance = CVEHunterConfig(**merged)
    return _config_instance


def get_nvd_api_key(config: Optional[CVEHunterConfig] = None) -> Optional[str]:
    """Return the NVD API key as a plain string, or None when unset.

    Wraps `SecretStr.get_secret_value()` so call sites do not need to
    handle the `SecretStr` wrapping or its `None` fallback explicitly.
    """
    cfg = config or get_cve_hunter_config()
    secret = cfg.nvd_api_key
    if secret is None:
        return None
    return (
        secret.get_secret_value()
        if hasattr(secret, "get_secret_value")
        else str(secret)
    )

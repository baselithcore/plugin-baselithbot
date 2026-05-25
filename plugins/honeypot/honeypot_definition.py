"""Honeypot Definition Schema.

Pydantic models for YAML-based honeypot configuration.
Each honeypot is defined in a separate YAML file that conforms to this schema.
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import HoneypotProtocol


class ResponseMode(str, Enum):
    """Response generation mode for honeypot interactions."""

    STATIC = "static"  # Use predefined templates
    LLM = "llm"  # Use LLM for dynamic responses
    TEMPLATE = "template"  # Template-based with variable substitution


class DetectionPattern(BaseModel):
    """Custom detection pattern for attack identification."""

    name: str = Field(..., description="Pattern identifier")
    regex: str = Field(..., description="Regular expression pattern")
    severity: str = Field(
        default="medium", description="Severity: info, low, medium, high, critical"
    )
    category: Optional[str] = Field(
        default=None, description="Attack category for classification"
    )

    model_config = ConfigDict(extra="ignore")


class DetectionConfig(BaseModel):
    """Detection settings for a honeypot."""

    sql_injection: bool = Field(default=True, description="Detect SQL injection")
    command_injection: bool = Field(
        default=True, description="Detect command injection"
    )
    path_traversal: bool = Field(default=True, description="Detect path traversal")
    xss: bool = Field(default=True, description="Detect XSS attacks")
    custom_patterns: List[DetectionPattern] = Field(
        default_factory=list, description="Custom detection patterns"
    )

    model_config = ConfigDict(extra="ignore")


class HTTPRoute(BaseModel):
    """HTTP route configuration for specific paths."""

    path: str = Field(..., description="URL path pattern (supports wildcards)")
    method: List[str] = Field(
        default_factory=lambda: ["GET"], description="Allowed HTTP methods"
    )
    response_template: Optional[str] = Field(
        default="default", description="Response template name"
    )
    response_content: Optional[str] = Field(
        default=None, description="Static response content (overrides template)"
    )
    status_code: int = Field(default=200, description="HTTP status code")
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Custom response headers"
    )

    model_config = ConfigDict(extra="ignore")


class HTTPHoneypotConfig(BaseModel):
    """HTTP-specific honeypot configuration."""

    emulated_app: str = Field(
        default="wordpress",
        description="Application to emulate: wordpress, phpmyadmin, jenkins, generic",
    )
    server_header: str = Field(
        default="Apache/2.4.53 (Debian)", description="Server response header"
    )
    powered_by: Optional[str] = Field(
        default="PHP/7.4.29", description="X-Powered-By header value"
    )
    routes: List[HTTPRoute] = Field(
        default_factory=list, description="Custom route configurations"
    )
    default_response: str = Field(
        default="index", description="Default response template or content"
    )
    default_status_code: int = Field(
        default=200, description="Default HTTP status code"
    )
    capture_credentials: bool = Field(
        default=True, description="Capture login credentials from forms"
    )

    model_config = ConfigDict(extra="ignore")


class SSHHoneypotConfig(BaseModel):
    """SSH-specific honeypot configuration."""

    server_name: str = Field(default="ubuntu", description="Fake hostname for banner")
    version: str = Field(
        default="OpenSSH_8.9p1 Ubuntu-3ubuntu0.4", description="SSH version banner"
    )
    allowed_passwords: List[str] = Field(
        default_factory=lambda: ["root", "admin", "password", "123456", "toor"],
        description="Passwords that allow successful login (for trapping)",
    )
    max_auth_attempts: int = Field(
        default=6, description="Maximum authentication attempts before disconnect"
    )
    shell_persona: str = Field(
        default="ubuntu_server",
        description="Shell response persona: ubuntu_server, centos, debian, alpine",
    )
    motd: Optional[str] = Field(default=None, description="Custom message of the day")
    filesystem_emulation: bool = Field(
        default=True, description="Enable filesystem emulation for ls, cat, etc."
    )


class TCPResponseRule(BaseModel):
    """Rule for matching TCP input and generating a response."""

    pattern: str = Field(..., description="Regex pattern to match input")
    response: str = Field(..., description="Response to send if pattern matches")


class TCPHoneypotConfig(BaseModel):
    """TCP-specific honeypot configuration."""

    banner: str = Field(
        default="Welcome to service\r\n", description="Initial connection banner"
    )
    protocol_name: str = Field(
        default="generic",
        description="Protocol being emulated: ftp, telnet, redis, etc.",
    )
    prompt: str = Field(default="> ", description="Command prompt string")
    responses: List[TCPResponseRule] = Field(
        default_factory=list,
        description="List of regex response rules",
    )
    close_on_invalid: bool = Field(
        default=False, description="Close connection on invalid command"
    )


class MCPHoneypotConfig(BaseModel):
    """MCP/LLM Guard specific configuration."""

    system_prompt: Optional[str] = Field(
        default=None,
        description="Override system prompt for this specific guard",
    )
    sensitivity: str = Field(
        default="medium",
        description="Sensitivity level: low, medium, high, paranoid",
    )
    ignored_patterns: List[str] = Field(
        default_factory=list,
        description="List of pattern names to ignore (allow-list)",
    )
    custom_rules: List[DetectionPattern] = Field(
        default_factory=list, description="Additional custom injection patterns"
    )
    enforce_json: bool = Field(
        default=False,
        description="Enforce valid JSON output from the LLM",
    )


class CloudAuthConfig(BaseModel):
    """Authentication configuration for cloud honeypot."""

    accept_any_signature: bool = Field(
        default=True,
        description="Accept any AWS signature for session tracking",
    )
    capture_credentials: bool = Field(
        default=True,
        description="Capture credentials from requests",
    )
    max_auth_failures: int = Field(
        default=5,
        description="Maximum authentication failures before blocking",
    )
    weak_keys_for_baiting: List[str] = Field(
        default_factory=list,
        description="Weak access keys to use as bait",
    )

    model_config = ConfigDict(extra="ignore")


class CloudResponseConfig(BaseModel):
    """Response configuration for cloud honeypot."""

    include_request_ids: bool = Field(
        default=True,
        description="Include AWS-style request IDs in responses",
    )
    simulate_latency_ms: int = Field(
        default=50,
        description="Simulated network latency in milliseconds",
    )
    error_message_verbosity: str = Field(
        default="detailed",
        description="Error message verbosity: minimal, standard, detailed",
    )

    model_config = ConfigDict(extra="ignore")


class CloudHoneypotConfig(BaseModel):
    """Cloud Management API specific configuration."""

    provider: str = Field(
        default="aws",
        description="Cloud provider to emulate: aws, azure, gcp",
    )
    region: str = Field(
        default="us-east-1",
        description="Simulated cloud region",
    )
    enabled_services: List[str] = Field(
        default_factory=lambda: ["iam", "s3", "sts"],
        description="Cloud services to simulate",
    )
    auth_config: Optional[CloudAuthConfig] = Field(
        default=None,
        description="Authentication configuration",
    )
    imds_enabled: bool = Field(
        default=True,
        description="Enable Instance Metadata Service (IMDS) simulation",
    )
    imds_version: str = Field(
        default="v1",
        description="IMDS version: v1 (vulnerable) or v2 (secure)",
    )
    response_config: Optional[CloudResponseConfig] = Field(
        default=None,
        description="Response generation configuration",
    )

    model_config = ConfigDict(extra="ignore")


class ModbusHoneypotConfig(BaseModel):
    """Modbus TCP honeypot configuration for ICS/SCADA emulation."""

    unit_id: int = Field(
        default=1,
        description="Modbus unit/slave ID",
    )
    supported_function_codes: List[int] = Field(
        default_factory=lambda: [1, 2, 3, 4, 5, 6, 15, 16],
        description="Supported Modbus function codes",
    )
    holding_registers: Dict[int, int] = Field(
        default_factory=lambda: {
            0: 0,
            1: 100,
            2: 250,
            3: 0,
            4: 1,
            100: 2400,
            101: 500,
            102: 60,
        },
        description="Register address to value map (simulated PLC state)",
    )
    coils: Dict[int, bool] = Field(
        default_factory=lambda: {0: True, 1: False, 2: True, 3: True},
        description="Coil address to state map",
    )
    device_identification: str = Field(
        default="Siemens S7-1200 / Modbus TCP Gateway",
        description="Device identification string for Modbus device ID",
    )

    model_config = ConfigDict(extra="ignore")


class MQTTHoneypotConfig(BaseModel):
    """MQTT broker honeypot configuration for IoT emulation."""

    allow_anonymous: bool = Field(
        default=True,
        description="Allow connections without credentials",
    )
    valid_credentials: List[Dict[str, str]] = Field(
        default_factory=lambda: [
            {"username": "admin", "password": "admin"},
            {"username": "device", "password": "device123"},
        ],
        description="Credentials that allow successful authentication",
    )
    monitored_topics: List[str] = Field(
        default_factory=lambda: [
            "factory/#",
            "plc/#",
            "sensor/#",
            "actuator/#",
            "$SYS/#",
            "cmd/#",
            "firmware/#",
        ],
        description="MQTT topic patterns to monitor for ICS activity",
    )
    max_qos: int = Field(
        default=2,
        description="Maximum QoS level supported (0, 1, or 2)",
        ge=0,
        le=2,
    )
    broker_name: str = Field(
        default="Eclipse Mosquitto/2.0.18",
        description="Broker identification string",
    )

    model_config = ConfigDict(extra="ignore")


class S7CommHoneypotConfig(BaseModel):
    """S7comm/COTP PLC honeypot configuration for Siemens PLC emulation."""

    rack: int = Field(
        default=0,
        description="PLC rack number",
    )
    slot: int = Field(
        default=2,
        description="PLC slot number",
    )
    cpu_type: str = Field(
        default="CPU 315-2 PN/DP",
        description="Siemens CPU type identifier",
    )
    order_code: str = Field(
        default="6ES7 315-2EH14-0AB0",
        description="Siemens order code for SZL identification",
    )
    serial_number: str = Field(
        default="S C-HONYPOT0001",
        description="PLC serial number",
    )
    db_blocks: Dict[int, Dict[str, int]] = Field(
        default_factory=lambda: {
            1: {"size": 256, "fill": 0},
            2: {"size": 128, "fill": 0},
        },
        description="DB block number to configuration map (size in bytes, fill value)",
    )
    module_info: str = Field(
        default="S7-300",
        description="Module identification string for SZL list",
    )

    model_config = ConfigDict(extra="ignore")


class HoneyDocConfig(BaseModel):
    """HoneyDOC-specific configuration for a honeypot."""

    personality: str = Field(
        default="generic",
        description="Personality profile for consistency (e.g. 'ubuntu-server-22')",
    )
    stealth_delay_ms: Optional[int] = Field(
        default=None, description="Override global stealth response delay (ms)"
    )
    flow_action_override: Optional[str] = Field(
        default=None,
        description="Override default flow action (allow, block, redirect)",
    )
    custom_fingerprint: Optional[Dict[str, str]] = Field(
        default=None, description="Specific fingerprint overrides for this honeypot"
    )


class HoneypotDefinition(BaseModel):
    """Complete honeypot definition loaded from YAML.

    This is the main schema for YAML-based honeypot configuration files.
    Each file in the honeypots/ directory should conform to this schema.
    """

    # Core identification
    id: str = Field(..., description="Unique identifier (e.g., 'wordpress-login')")
    name: str = Field(..., description="Human-readable display name")
    description: str = Field(default="", description="Detailed description")

    # Protocol and network
    protocol: HoneypotProtocol = Field(..., description="Protocol: ssh, http, tcp")
    port: int = Field(..., description="Port to listen on", ge=0, le=65535)
    bind_address: str = Field(
        default="0.0.0.0",  # nosec B104
        description="Address to bind to",
    )

    # Handler configuration
    handler_type: str = Field(
        default="auto",
        description="Handler type: http, ssh, tcp, mcp, cloud, custom, auto (inferred from protocol)",
    )
    custom_handler_class: Optional[str] = Field(
        default=None,
        description="Python class path for custom handler (e.g. 'my_module.MyHandler'). Required if handler_type is 'custom'.",
    )

    # Protocol-specific configurations (mutually exclusive based on protocol)
    http_config: Optional[HTTPHoneypotConfig] = Field(
        default=None, description="HTTP-specific configuration"
    )
    ssh_config: Optional[SSHHoneypotConfig] = Field(
        default=None, description="SSH-specific configuration"
    )
    tcp_config: Optional[TCPHoneypotConfig] = Field(
        default=None, description="TCP-specific configuration"
    )
    mcp_config: Optional[MCPHoneypotConfig] = Field(
        default=None, description="MCP/LLM Guard specific configuration"
    )
    cloud_config: Optional[CloudHoneypotConfig] = Field(
        default=None, description="Cloud Management API specific configuration"
    )
    modbus_config: Optional[ModbusHoneypotConfig] = Field(
        default=None, description="Modbus TCP ICS/SCADA configuration"
    )
    mqtt_config: Optional[MQTTHoneypotConfig] = Field(
        default=None, description="MQTT broker IoT configuration"
    )
    s7comm_config: Optional[S7CommHoneypotConfig] = Field(
        default=None, description="S7comm Siemens PLC configuration"
    )

    # Detection configuration
    detection: DetectionConfig = Field(
        default_factory=DetectionConfig, description="Attack detection settings"
    )

    # Response generation
    response_mode: ResponseMode = Field(
        default=ResponseMode.STATIC, description="Response generation mode"
    )
    llm_system_prompt: Optional[str] = Field(
        default=None,
        description="Custom system prompt for LLM responses (if response_mode=llm)",
    )
    payload_templates: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom response templates by name",
    )

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    enabled: bool = Field(default=True, description="Whether this honeypot is active")
    priority: int = Field(
        default=0,
        description="Priority for resource allocation (higher = more resources)",
    )

    # HoneyDOC Configuration
    honeydoc: Optional[HoneyDocConfig] = Field(
        default=None, description="HoneyDOC specific configuration"
    )

    @field_validator("handler_type")
    @classmethod
    def validate_handler_type(cls, v: str, info) -> str:
        """Auto-infer handler type from protocol if set to auto."""
        if v == "auto":
            # Will be resolved during loading based on protocol
            return v
        valid_types = {
            "http",
            "ssh",
            "tcp",
            "mcp",
            "custom",
            "cloud",
            "auto",
            "modbus",
            "mqtt",
            "s7comm",
        }
        if v not in valid_types:
            raise ValueError(f"handler_type must be one of {valid_types}")
        return v

    def get_protocol_config(
        self,
    ) -> Optional[
        HTTPHoneypotConfig
        | SSHHoneypotConfig
        | TCPHoneypotConfig
        | MCPHoneypotConfig
        | CloudHoneypotConfig
        | ModbusHoneypotConfig
        | MQTTHoneypotConfig
        | S7CommHoneypotConfig
    ]:
        """Get the protocol-specific configuration."""
        # Cloud handler takes precedence if specified
        if self.handler_type == "cloud" and self.cloud_config:
            return self.cloud_config

        if self.protocol == HoneypotProtocol.HTTP:
            # Check if cloud handler with HTTP protocol
            if self.handler_type == "cloud":
                return self.cloud_config or CloudHoneypotConfig()
            return self.http_config or HTTPHoneypotConfig()
        elif self.protocol == HoneypotProtocol.SSH:
            return self.ssh_config or SSHHoneypotConfig()
        elif self.protocol == HoneypotProtocol.TCP:
            return self.tcp_config or TCPHoneypotConfig()
        elif self.protocol == HoneypotProtocol.MCP:
            return self.mcp_config or MCPHoneypotConfig()
        elif self.protocol == HoneypotProtocol.MODBUS:
            return self.modbus_config or ModbusHoneypotConfig()
        elif self.protocol == HoneypotProtocol.MQTT:
            return self.mqtt_config or MQTTHoneypotConfig()
        elif self.protocol == HoneypotProtocol.S7COMM:
            return self.s7comm_config or S7CommHoneypotConfig()
        return None

    def resolve_handler_type(self) -> str:
        """Resolve handler type, inferring from protocol if auto."""
        if self.handler_type != "auto":
            return self.handler_type
        # Auto-infer from protocol
        return self.protocol.value

    model_config = ConfigDict(extra="ignore")


class HoneypotDefinitionFile(BaseModel):
    """Wrapper for loading YAML file with source metadata."""

    definition: HoneypotDefinition
    source_file: Path = Field(..., description="Source YAML file path")

    model_config = ConfigDict(arbitrary_types_allowed=True)

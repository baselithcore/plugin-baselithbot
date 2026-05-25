"""Emulation Module Data Models.

Defines core data structures for the Advanced Deception System emulation layer.
All models use Pydantic v2 for validation and serialization.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class OperationType(str, Enum):
    """Types of operations for latency modeling."""

    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    FILESYSTEM_LIST = "filesystem_list"
    NETWORK_LOOKUP = "network_lookup"
    PROCESS_SPAWN = "process_spawn"
    PROCESS_LIST = "process_list"
    CRYPTO_OP = "crypto_op"
    SYSTEM_INFO = "system_info"
    AUTH_CHECK = "auth_check"
    GENERIC = "generic"


class TTP(str, Enum):
    """MITRE ATT&CK-aligned Tactics, Techniques, and Procedures."""

    # Reconnaissance
    ACTIVE_SCANNING = "T1595"
    GATHER_VICTIM_HOST_INFO = "T1592"

    # Initial Access
    EXPLOIT_PUBLIC_APP = "T1190"
    VALID_ACCOUNTS = "T1078"

    # Execution
    COMMAND_SCRIPTING = "T1059"
    SCHEDULED_TASK = "T1053"

    # Persistence
    CREATE_ACCOUNT = "T1136"
    SSH_AUTHORIZED_KEYS = "T1098.004"

    # Privilege Escalation
    SUDO_ABUSE = "T1548.003"
    SETUID_SETGID = "T1548.001"

    # Defense Evasion
    DISABLE_SECURITY = "T1562"
    INDICATOR_REMOVAL = "T1070"
    OBFUSCATED_FILES = "T1027"

    # Credential Access
    CREDENTIAL_DUMPING = "T1003"
    BRUTE_FORCE = "T1110"
    UNSECURED_CREDENTIALS = "T1552"

    # Discovery
    ACCOUNT_DISCOVERY = "T1087"
    FILE_DISCOVERY = "T1083"
    NETWORK_DISCOVERY = "T1046"
    SYSTEM_INFO_DISCOVERY = "T1082"
    PROCESS_DISCOVERY = "T1057"

    # Lateral Movement
    SSH_LATERAL = "T1021.004"
    REMOTE_SERVICES = "T1021"

    # Collection
    DATA_FROM_LOCAL = "T1005"
    DATA_STAGED = "T1074"

    # Exfiltration
    EXFIL_OVER_C2 = "T1041"
    EXFIL_OVER_ALT = "T1048"

    # Impact
    DATA_DESTRUCTION = "T1485"
    RESOURCE_HIJACKING = "T1496"  # Cryptomining


class TTPPrediction(BaseModel):
    """A predicted TTP with confidence score."""

    ttp: TTP
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class FSMutation(BaseModel):
    """Represents a filesystem mutation for state tracking."""

    mutation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mutation_type: Literal[
        "create_file",
        "create_dir",
        "modify_file",
        "delete_file",
        "delete_dir",
        "chmod",
        "chown",
    ]
    path: str
    content: Optional[str] = None
    permissions: Optional[str] = None
    owner: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_dump_compact(self) -> Dict[str, Any]:
        """Compact serialization for cluster sync."""
        return {
            "id": self.mutation_id,
            "t": self.mutation_type,
            "p": self.path,
            "c": self.content[:100] if self.content else None,  # Truncate content
            "ts": self.timestamp.isoformat(),
        }


class EnvMutation(BaseModel):
    """Represents an environment variable mutation."""

    mutation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    var_name: str
    var_value: Optional[str] = None
    action: Literal["set", "unset"] = "set"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CommandRecord(BaseModel):
    """Record of a command execution for history tracking."""

    command: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    output_preview: Optional[str] = None
    exit_code: int = 0
    operation_type: OperationType = OperationType.GENERIC
    detected_ttp: Optional[TTP] = None


class CredentialAttempt(BaseModel):
    """Record of a credential attempt."""

    username: str
    password: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = False
    auth_type: Literal["password", "key", "other"] = "password"


class TimingStats(BaseModel):
    """Statistics about session timing behavior."""

    session_start: datetime
    total_commands: int = 0
    mean_inter_command_delay_ms: float = 0.0
    min_inter_command_delay_ms: float = float("inf")
    max_inter_command_delay_ms: float = 0.0
    typing_speed_estimate_cpm: Optional[float] = None  # Characters per minute

    def update(self, new_delay_ms: float) -> None:
        """Update timing stats with new command delay."""
        n = self.total_commands
        if n == 0:
            self.mean_inter_command_delay_ms = new_delay_ms
        else:
            # Running average
            self.mean_inter_command_delay_ms = (
                self.mean_inter_command_delay_ms * n + new_delay_ms
            ) / (n + 1)
        self.min_inter_command_delay_ms = min(
            self.min_inter_command_delay_ms, new_delay_ms
        )
        self.max_inter_command_delay_ms = max(
            self.max_inter_command_delay_ms, new_delay_ms
        )
        self.total_commands += 1


class SessionState(BaseModel):
    """Complete state for an emulated session.

    Tracks all aspects of session context for coherent emulation
    and cluster synchronization.
    """

    session_id: str
    username: str = "root"
    hostname: str = "ubuntu-server"

    # Filesystem state
    cwd: str = "/root"
    home_dir: str = "/root"

    # Environment
    env_vars: Dict[str, str] = Field(
        default_factory=lambda: {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": "/root",
            "USER": "root",
            "SHELL": "/bin/bash",
            "TERM": "xterm-256color",
            "LANG": "en_US.UTF-8",
        }
    )

    # Command history
    command_history: List[CommandRecord] = Field(default_factory=list)

    # Mutations applied during session
    fs_mutations: List[FSMutation] = Field(default_factory=list)
    env_mutations: List[EnvMutation] = Field(default_factory=list)

    # Authentication attempts
    auth_attempts: List[CredentialAttempt] = Field(default_factory=list)

    # Timing profile
    timing: TimingStats = Field(
        default_factory=lambda: TimingStats(session_start=datetime.now(timezone.utc))
    )

    # Detected patterns
    detected_ttps: List[TTPPrediction] = Field(default_factory=list)

    # Session metadata
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    node_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_command(self, record: CommandRecord) -> None:
        """Add command to history and update timing."""
        if self.command_history:
            last_cmd = self.command_history[-1]
            delay_ms = (record.timestamp - last_cmd.timestamp).total_seconds() * 1000
            self.timing.update(delay_ms)

        self.command_history.append(record)
        self.last_activity = record.timestamp

    def apply_fs_mutation(self, mutation: FSMutation) -> None:
        """Apply and record a filesystem mutation."""
        self.fs_mutations.append(mutation)
        self.last_activity = mutation.timestamp

    def apply_env_mutation(self, mutation: EnvMutation) -> None:
        """Apply and record an environment mutation."""
        if mutation.action == "set" and mutation.var_value is not None:
            self.env_vars[mutation.var_name] = mutation.var_value
        elif mutation.action == "unset":
            self.env_vars.pop(mutation.var_name, None)
        self.env_mutations.append(mutation)

    def get_prompt(self) -> str:
        """Generate shell prompt for current state."""
        # Detect OS type based on env vars
        is_windows = self.env_vars.get("OS") == "Windows_NT"

        if is_windows:
            # Windows prompt: C:\Users\Administrator>
            # Map internal VFS paths to Windows display paths
            display_path = self.cwd.replace("/", "\\")
            if display_path.startswith("\\home"):
                display_path = display_path.replace("\\home", "\\Users", 1)

            if not display_path.startswith("C:"):
                display_path = "C:" + display_path

            return f"{display_path}> "
        else:
            # Linux prompt: user@host:path$
            user = self.env_vars.get("USER", self.username)
            short_cwd = (
                self.cwd.replace(self.home_dir, "~")
                if self.cwd.startswith(self.home_dir)
                else self.cwd
            )
            prompt_char = "#" if user == "root" else "$"
            return f"{user}@{self.hostname}:{short_cwd}{prompt_char} "


class FingerprintProfile(BaseModel):
    """OS fingerprint profile for coherent emulation.

    Contains all parameters needed to convincingly emulate
    a specific operating system across protocols.
    """

    # Profile identification
    profile_id: str
    os_type: Literal[
        "linux_ubuntu",
        "linux_centos",
        "linux_debian",
        "windows_server",
        "windows_desktop",
        "freebsd",
    ]
    os_version: str
    kernel_version: Optional[str] = None
    architecture: Literal["x86_64", "amd64", "arm64", "i686"] = "x86_64"

    # TCP/IP stack fingerprint (p0f compatible)
    tcp_ttl: int = 64
    tcp_window_size: int = 65535
    tcp_options: List[str] = Field(
        default_factory=lambda: ["mss", "sackOK", "timestamp", "nop", "wscale"]
    )
    tcp_df_flag: bool = True  # Don't Fragment
    tcp_window_scale: int = 7

    # SSH fingerprint
    ssh_banner: str = "OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"
    ssh_kex_algorithms: List[str] = Field(
        default_factory=lambda: [
            "curve25519-sha256",
            "curve25519-sha256@libssh.org",
            "ecdh-sha2-nistp256",
            "ecdh-sha2-nistp384",
            "ecdh-sha2-nistp521",
            "diffie-hellman-group-exchange-sha256",
        ]
    )
    ssh_ciphers: List[str] = Field(
        default_factory=lambda: [
            "chacha20-poly1305@openssh.com",
            "aes128-ctr",
            "aes192-ctr",
            "aes256-ctr",
            "aes128-gcm@openssh.com",
            "aes256-gcm@openssh.com",
        ]
    )

    # HTTP fingerprint
    http_server_header: str = "Apache/2.4.54 (Ubuntu)"
    http_header_order: List[str] = Field(
        default_factory=lambda: [
            "Date",
            "Server",
            "X-Powered-By",
            "Content-Type",
            "Content-Length",
        ]
    )
    http_header_casing: Literal["title", "lower", "original"] = "title"

    # Response content patterns
    uname_output: str = (
        "Linux ubuntu-server 5.15.0-88-generic #98-Ubuntu SMP x86_64 GNU/Linux"
    )
    motd_banner: str = (
        "Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-88-generic x86_64)"
    )

    # Latency model parameters (Gaussian distribution)
    latency_mean_ms: float = 50.0
    latency_std_ms: float = 15.0
    latency_min_ms: float = 5.0
    latency_max_ms: float = 500.0

    # Per-operation latency multipliers
    latency_multipliers: Dict[str, float] = Field(
        default_factory=lambda: {
            "filesystem_read": 0.2,
            "filesystem_write": 0.5,
            "filesystem_list": 0.3,
            "network_lookup": 1.5,
            "process_spawn": 2.0,
            "process_list": 0.4,
            "crypto_op": 3.0,
            "system_info": 0.3,
            "auth_check": 0.5,
            "generic": 1.0,
        }
    )

    @classmethod
    def load(cls, profile_name: str) -> "FingerprintProfile":
        """Load a fingerprint profile by name.

        Args:
            profile_name: Profile identifier (e.g., "linux_ubuntu")

        Returns:
            Loaded FingerprintProfile

        Raises:
            FileNotFoundError: If profile doesn't exist
        """
        import yaml

        profiles_dir = Path(__file__).parent / "profiles"
        profile_path = profiles_dir / f"{profile_name}.yaml"

        if not profile_path.exists():
            raise FileNotFoundError(f"Fingerprint profile not found: {profile_name}")

        with open(profile_path) as f:
            data = yaml.safe_load(f)

        return cls(**data)

    @classmethod
    def get_default(cls) -> "FingerprintProfile":
        """Get default Ubuntu profile."""
        return cls(
            profile_id="linux_ubuntu_default",
            os_type="linux_ubuntu",
            os_version="22.04.3 LTS",
            kernel_version="5.15.0-88-generic",
        )


class EmulatedResponse(BaseModel):
    """Response from the emulation engine."""

    output: str
    exit_code: int = 0
    operation_type: OperationType = OperationType.GENERIC
    latency_applied_ms: float = 0.0
    mutations: List[FSMutation] = Field(default_factory=list)
    detected_ttp: Optional[TTP] = None
    bait_triggered: bool = False
    alert_generated: bool = False


class BaitContent(BaseModel):
    """Dynamically generated bait content for adaptive response."""

    path: str
    content: str
    trigger_on_access: bool = True
    alert_priority: Literal["low", "medium", "high", "critical"] = "medium"
    external_webhook: bool = False
    canary_token: Optional[str] = None
    ttl_minutes: Optional[int] = None

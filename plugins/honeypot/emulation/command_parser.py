"""Command Parsing for TTP Detection.

Parses raw shell commands to extract semantic information,
detect operation types, and identify MITRE ATT&CK TTPs.
"""

from core.observability.logging import get_logger
import re
from typing import List, Optional

from .models import OperationType, TTP

logger = get_logger(__name__)


class ParsedCommand:
    """Parsed command with semantic analysis.

    Extracts operation type, detects TTPs, and identifies
    side effects (file/env modifications) from raw commands.
    """

    def __init__(self, raw_command: str):
        """Parse a command string.

        Args:
            raw_command: Raw command string
        """
        self.raw = raw_command.strip()
        self.command, self.args = self._parse_command_and_args()

        # Semantic analysis
        self.operation_type = self._detect_operation_type()
        self.detected_ttp: Optional[TTP] = self._detect_ttp()

        # Side effects
        self.creates_file = False
        self.deletes_file = False
        self.modifies_env = False
        self.target_path: Optional[str] = None
        self.var_name: Optional[str] = None
        self.var_value: Optional[str] = None

        self._analyze_side_effects()

    def _parse_command_and_args(self) -> tuple[str, List[str]]:
        """Parse command name and arguments.

        Returns:
            Tuple of (command, args)
        """
        parts = self.raw.split()
        if not parts:
            return "", []

        cmd = parts[0].lower()

        # Handle sudo prefix
        if cmd == "sudo" and len(parts) > 1:
            cmd = parts[1].lower()
            args = parts[2:]
        else:
            args = parts[1:]

        return cmd, args

    def _detect_operation_type(self) -> OperationType:
        """Detect operation type from command.

        Returns:
            OperationType enum value
        """
        # File operations
        if self.command in {"cat", "head", "tail", "less", "more"}:
            return OperationType.FILESYSTEM_READ
        elif self.command in {"ls", "dir", "find", "locate"}:
            return OperationType.FILESYSTEM_LIST
        elif self.command in {"touch", "echo", "tee", "dd"}:
            return OperationType.FILESYSTEM_WRITE
        elif self.command in {"mkdir", "mktemp"}:
            return OperationType.FILESYSTEM_WRITE
        elif self.command in {"rm", "rmdir", "unlink"}:
            return OperationType.FILESYSTEM_WRITE  # Matches original logic
        elif self.command in {"cp", "mv", "rsync"}:
            return OperationType.FILESYSTEM_WRITE
        elif self.command in {"chmod", "chown", "chgrp"}:
            return OperationType.FILESYSTEM_WRITE

        # Network operations
        elif self.command in {
            "curl",
            "wget",
            "nc",
            "ncat",
            "ssh",
            "scp",
            "sftp",
            "ftp",
        }:
            return OperationType.NETWORK_LOOKUP
        elif self.command in {"ping", "traceroute", "dig", "nslookup"}:
            return OperationType.NETWORK_LOOKUP
        elif self.command in {"netstat", "ss", "ip", "ifconfig", "route"}:
            return OperationType.SYSTEM_INFO

        # Process operations
        elif self.command in {"ps", "top", "htop", "pgrep"}:
            return OperationType.PROCESS_LIST
        elif self.command in {"kill", "pkill", "killall"}:
            return OperationType.PROCESS_KILL
        elif self.command in {"nice", "renice", "ionice"}:
            return OperationType.PROCESS_MANAGEMENT

        # System info
        elif self.command in {
            "uname",
            "hostname",
            "uptime",
            "whoami",
            "id",
            "w",
            "who",
        }:
            return OperationType.SYSTEM_INFO
        elif self.command in {"env", "printenv", "set", "export"}:
            return OperationType.SYSTEM_INFO

        # Crypto/encoding
        elif self.command in {"openssl", "gpg", "base64", "md5sum", "sha256sum"}:
            return OperationType.CRYPTO_OP

        # Archiving
        elif self.command in {"tar", "zip", "unzip", "gzip", "gunzip", "bzip2"}:
            return OperationType.ARCHIVE_OP

        # Default
        else:
            return OperationType.GENERIC

    def _detect_ttp(self) -> Optional[TTP]:
        """Detect MITRE ATT&CK TTP from command.

        Returns:
            TTP enum value or None
        """
        cmd_lower = self.raw.lower()

        # High-priority credential access
        if "/etc/shadow" in cmd_lower or "hashdump" in cmd_lower:
            return TTP.CREDENTIAL_DUMPING

        # SSH key access
        if "authorized_keys" in cmd_lower or ".ssh/id_" in cmd_lower:
            return TTP.SSH_AUTHORIZED_KEYS

        # AWS/cloud credentials
        if ".aws/credentials" in cmd_lower or "aws configure" in cmd_lower:
            return TTP.UNSECURED_CREDENTIALS

        # Kubernetes config
        if ".kube/config" in cmd_lower:
            return TTP.UNSECURED_CREDENTIALS

        # Account discovery
        if self.command in {"whoami", "id", "w", "who", "finger"}:
            return TTP.ACCOUNT_DISCOVERY

        # /etc/passwd enumeration
        if "/etc/passwd" in cmd_lower and self.command in {
            "cat",
            "head",
            "tail",
            "less",
        }:
            return TTP.CREDENTIAL_DUMPING

        # System info discovery
        if "/etc/os-release" in cmd_lower or "/proc/version" in cmd_lower:
            return TTP.SYSTEM_INFO_DISCOVERY

        # Network discovery
        if self.command in {"netstat", "ss", "ip", "ifconfig", "arp"}:
            return TTP.NETWORK_DISCOVERY

        # File/directory discovery
        if self.command == "find" and any(a.startswith("/") for a in self.args):
            return TTP.FILE_DISCOVERY

        # Privilege escalation
        if self.raw.startswith("sudo -l") or "sudo -i" in cmd_lower:
            return TTP.SUDO_ABUSE

        # Command/scripting interpreter
        if re.search(r"(python|perl|ruby|php|bash|sh)\s+-c", cmd_lower):
            return TTP.COMMAND_SCRIPTING

        # Data staging
        if self.command in {"tar", "zip", "7z"} and "-" in cmd_lower:
            return TTP.DATA_STAGED

        # Exfiltration
        if re.search(r"curl.*-[TX]", cmd_lower) or re.search(
            r"wget.*--post", cmd_lower
        ):
            return TTP.EXFIL_OVER_C2

        # History tampering
        if "history -c" in cmd_lower or ".bash_history" in cmd_lower:
            return TTP.INDICATOR_REMOVAL

        # Log clearing
        if self.command == "rm" and any("log" in a for a in self.args):
            return TTP.INDICATOR_REMOVAL

        return None

    def _analyze_side_effects(self) -> None:
        """Analyze command side effects (file/env mutations)."""
        # File creation
        if self.command in {"touch", "echo", "tee", "dd", "mktemp"}:
            self.creates_file = True
            if self.args:
                # Extract target path
                for arg in self.args:
                    if not arg.startswith("-") and "/" in arg:
                        self.target_path = arg
                        break
                # Handle redirection
                if ">" in self.raw:
                    parts = self.raw.split(">")
                    if len(parts) > 1:
                        self.target_path = parts[-1].strip().split()[0]

        # Directory creation
        elif self.command in {"mkdir"}:
            self.creates_file = True
            if self.args:
                self.target_path = next(
                    (a for a in self.args if not a.startswith("-")), None
                )

        # File deletion
        elif self.command in {"rm", "unlink"}:
            self.deletes_file = True
            if self.args:
                self.target_path = next(
                    (a for a in self.args if not a.startswith("-")), None
                )

        # Environment modification
        elif self.command == "export":
            self.modifies_env = True
            if self.args and "=" in self.args[0]:
                var_assignment = self.args[0]
                if "=" in var_assignment:
                    self.var_name, self.var_value = var_assignment.split("=", 1)

        # Direct assignment (VAR=value)
        elif "=" in self.command and not self.command.startswith("-"):
            self.modifies_env = True
            self.var_name, self.var_value = self.command.split("=", 1)

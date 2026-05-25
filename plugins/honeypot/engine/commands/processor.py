"""Main command processor orchestrating all command modules."""

import shlex
import random
from datetime import datetime, timedelta
from typing import Dict, Any

from ..virtual_filesystem import VirtualFilesystem
from .filesystem import FilesystemCommands
from .text_processing import TextProcessingCommands
from .system_info import SystemInfoCommands
from .network import NetworkCommands
from .scripting import ScriptingCommands
from .system_management import SystemManagementCommands
from .monitoring import MonitoringCommands
from .security import SecurityCommands

# Shell builtins that are typically silent initialization commands
SHELL_BUILTINS = {
    "export",
    "alias",
    "unalias",
    "set",
    "unset",
    "source",
    "declare",
    "typeset",
    "local",
    "readonly",
    "eval",
    "exec",
    "builtin",
    "command",
    "type",
    "hash",
    "bind",
    "complete",
    "compgen",
    "shopt",
    "enable",
    "true",
    "false",
    ".",
}


class CommandProcessor(
    FilesystemCommands,
    TextProcessingCommands,
    SystemInfoCommands,
    NetworkCommands,
    ScriptingCommands,
    SystemManagementCommands,
    MonitoringCommands,
    SecurityCommands,
):
    """Process shell commands with virtual filesystem.

    Combines all command modules through multiple inheritance.
    """

    def __init__(self, vfs: VirtualFilesystem, fingerprint: Dict[str, Any]):
        """Initialize command processor.

        Args:
            vfs: Virtual filesystem instance
            fingerprint: Honeypot fingerprint data
        """
        # Initialize all parent classes
        super().__init__(vfs, fingerprint)

        # Session state for realistic behavior
        self._session_start = datetime.now()
        self._boot_time = datetime.now() - timedelta(
            days=random.randint(12, 89),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        self._uid = random.choice([1000, 1001, 1002])
        self._pid_base = random.randint(1200, 8500)
        self._load_avg = (
            round(random.uniform(0.02, 0.18), 2),
            round(random.uniform(0.03, 0.14), 2),
            round(random.uniform(0.01, 0.09), 2),
        )

        # Bind self to scripting commands for bash -c
        if hasattr(self, "_cmd_bash"):
            # Store reference to processor for scripting commands
            self._processor = self  # type: ignore

    def process_command(self, command: str) -> str:
        """Process a shell command and return output.

        Args:
            command: Raw command string

        Returns:
            Command output
        """
        command = command.strip()
        if not command:
            return ""

        # Handle shell builtins and special commands
        if command.startswith(":"):
            return ""  # colon is a no-op

        # Parse command (handle pipes, redirections, etc.)
        if ">" in command or ">>" in command:
            return self._handle_redirection(command)

        if "|" in command:
            return self._handle_pipe(command)

        # Handle simple command
        return self._execute_single_command(command)

    def _execute_single_command(self, command: str) -> str:
        """Execute a single command.

        Args:
            command: Command to execute

        Returns:
            Command output
        """
        try:
            parts = shlex.split(command)
        except ValueError:
            # Quote parsing error
            return "-bash: syntax error near unexpected token"

        if not parts:
            return ""

        cmd_name = parts[0].lower()
        args = parts[1:]

        # Check if it's a builtin
        if cmd_name in SHELL_BUILTINS:
            return ""

        # Route to appropriate handler
        handlers = {
            "pwd": self._cmd_pwd,
            "cd": self._cmd_cd,
            "ls": self._cmd_ls,
            "cat": self._cmd_cat,
            "touch": self._cmd_touch,
            "mkdir": self._cmd_mkdir,
            "rm": self._cmd_rm,
            "rmdir": self._cmd_rmdir,
            "echo": self._cmd_echo,
            "whoami": self._cmd_whoami,
            "id": self._cmd_id,
            "hostname": self._cmd_hostname,
            "uname": self._cmd_uname,
            "date": self._cmd_date,
            "uptime": self._cmd_uptime,
            "ps": self._cmd_ps,
            "find": self._cmd_find,
            "chmod": self._cmd_chmod,
            "chown": self._cmd_chown,
            "cp": self._cmd_cp,
            "mv": self._cmd_mv,
            "head": self._cmd_head,
            "tail": self._cmd_tail,
            "grep": self._cmd_grep,
            "wc": self._cmd_wc,
            "wget": self._cmd_wget,
            "curl": self._cmd_curl,
            "python": self._cmd_python,
            "python3": self._cmd_python,
            "perl": self._cmd_perl,
            "bash": self._cmd_bash,
            "sh": self._cmd_bash,
            # System management commands
            "systemctl": self._cmd_systemctl,
            "service": self._cmd_service,
            "journalctl": self._cmd_journalctl,
            "apt": self._cmd_apt,
            "apt-get": self._cmd_apt,
            "dpkg": self._cmd_dpkg,
            # Monitoring commands
            "netstat": self._cmd_netstat,
            "ss": self._cmd_ss,
            "lsof": self._cmd_lsof,
            "iostat": self._cmd_iostat,
            "vmstat": self._cmd_vmstat,
            "free": self._cmd_free,
            "df": self._cmd_df,
            "du": self._cmd_du,
            "top": self._cmd_top,
            "htop": self._cmd_htop,
            "iotop": self._cmd_iotop,
            "dmesg": self._cmd_dmesg,
            "strace": self._cmd_strace,
            "tcpdump": self._cmd_tcpdump,
            "iftop": self._cmd_iftop,
            "sar": self._cmd_sar,
            "nmap": self._cmd_nmap,
            "lscpu": self._cmd_lscpu,
            "lsblk": self._cmd_lsblk,
            "lspci": self._cmd_lspci,
            "lsusb": self._cmd_lsusb,
            # Security commands
            "sudo": self._cmd_sudo,
            "su": self._cmd_su,
            "visudo": self._cmd_visudo,
            "passwd": self._cmd_passwd,
            "chage": self._cmd_chage,
            "usermod": self._cmd_usermod,
            "useradd": self._cmd_useradd,
            "userdel": self._cmd_userdel,
            "groupadd": self._cmd_groupadd,
            "adduser": self._cmd_adduser,
        }

        handler = handlers.get(cmd_name)
        if handler:
            try:
                return handler(args)
            except Exception as e:
                return f"-bash: {cmd_name}: error: {str(e)}"

        # Command not found
        return f"-bash: {cmd_name}: command not found"

    def _handle_redirection(self, command: str) -> str:
        """Handle output redirection (>, >>).

        Args:
            command: Command with redirection

        Returns:
            Command output (usually empty for redirections)
        """
        # Parse redirection
        if ">>" in command:
            parts = command.split(">>", 1)
            append = True
        elif ">" in command:
            parts = command.split(">", 1)
            append = False
        else:
            return self._execute_single_command(command)

        if len(parts) != 2:
            return "-bash: syntax error near unexpected token"

        cmd_part = parts[0].strip()
        file_part = parts[1].strip()

        # Execute command to get output
        output = self._execute_single_command(cmd_part)

        # Write to file
        success, error = self.vfs.write_file(
            file_part, output + "\n" if output else "", append=append
        )

        if not success:
            return error

        return ""  # Redirection produces no output

    def _handle_pipe(self, command: str) -> str:
        """Handle pipes (|).

        Args:
            command: Command with pipes

        Returns:
            Final output
        """
        # Simple pipe implementation
        commands = command.split("|")
        output = ""

        for i, cmd in enumerate(commands):
            cmd = cmd.strip()
            if i == 0:
                # First command
                output = self._execute_single_command(cmd)
            else:
                # Subsequent commands - simulate piping
                # For simplicity, just pass the previous output to grep/head/tail
                parts = shlex.split(cmd) if cmd else []
                if parts and parts[0] in ("grep", "head", "tail", "wc"):
                    # Simulate piping by processing the output
                    output = self._process_pipe_command(parts[0], parts[1:], output)
                else:
                    output = self._execute_single_command(cmd)

        return output

    def _process_pipe_command(self, cmd: str, args: list, input_data: str) -> str:
        """Process a command in a pipe with input data.

        Args:
            cmd: Command name
            args: Command arguments
            input_data: Input from previous command

        Returns:
            Processed output
        """
        if cmd == "grep" and args:
            # Simple grep simulation
            pattern = args[0]
            lines = [line for line in input_data.split("\n") if pattern in line]
            return "\n".join(lines)

        elif cmd == "head":
            n = 10
            if args and args[0].startswith("-"):
                try:
                    n = int(args[0][1:])
                except ValueError:
                    pass
            lines = input_data.split("\n")[:n]
            return "\n".join(lines)

        elif cmd == "tail":
            n = 10
            if args and args[0].startswith("-"):
                try:
                    n = int(args[0][1:])
                except ValueError:
                    pass
            lines = input_data.split("\n")[-n:]
            return "\n".join(lines)

        elif cmd == "wc":
            lines = input_data.split("\n")
            words = input_data.split()
            chars = len(input_data)
            return f"{len(lines)} {len(words)} {chars}"

        return input_data


# Legacy compatibility function
def generate_command_response(
    command: str, fingerprint: Dict[str, Any], vfs: VirtualFilesystem | None = None
) -> str:
    """Generate fake command response using virtual filesystem.

    Args:
        command: Command to respond to
        fingerprint: Honeypot fingerprint data
        vfs: Virtual filesystem instance (optional, creates new if not provided)

    Returns:
        Fake output
    """
    if vfs is None:
        # Create temporary VFS for backward compatibility
        username = "admin"
        hostname = fingerprint.get("hostname", "ubuntu-server")
        vfs = VirtualFilesystem(username=username, hostname=hostname)

    processor = CommandProcessor(vfs, fingerprint)
    return processor.process_command(command)

"""SSH Honeypot Handler.

Asyncio-based SSH honeypot server using asyncssh.
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Dict, Optional

from ..config import HoneypotConfig
from ..models import AttackCategory, AttackEvent, HoneypotProtocol, HoneypotSession
from .base import BaseHandler
from .ssh_commands import CommandProcessor, SHELL_BUILTINS
from .virtual_filesystem import VirtualFilesystem

# Advanced Deception System imports (optional)
try:
    from ..emulation import StatefulEmulator
    from ..emulation.models import FingerprintProfile

    ADS_AVAILABLE = True
except ImportError:
    ADS_AVAILABLE = False
    StatefulEmulator = None
    FingerprintProfile = None

logger = get_logger(__name__)

# Try to import asyncssh, but handle if not installed
try:
    import asyncssh
    from .ssh_protocol import SSHServerProtocol

    ASYNCSSH_AVAILABLE = True
except ImportError:
    ASYNCSSH_AVAILABLE = False
    SSHServerProtocol = object  # type: ignore
    logger.warning("asyncssh not installed. SSH honeypot will be disabled.")


class SSHHandler(BaseHandler):
    """SSH honeypot handler using asyncssh."""

    def __init__(self, config: HoneypotConfig, definition=None):
        """Initialize SSH handler."""
        super().__init__(config, definition)
        self._server = None
        self._sessions: Dict[str, HoneypotSession] = {}
        self._filesystems: Dict[
            str, VirtualFilesystem
        ] = {}  # Per-session filesystems (legacy)
        self._emulators: Dict[str, StatefulEmulator] = {}  # Per-session emulators (ADS)
        self._llm_service = None

        # Check if ADS emulation is enabled
        self._ads_enabled = (
            ADS_AVAILABLE and hasattr(config, "emulation") and config.emulation.enabled
        )

        if self._ads_enabled:
            # Load fingerprint profile for ADS
            profile_name = config.emulation.default_os_profile
            try:
                self._fingerprint_profile = FingerprintProfile.load(profile_name)
                logger.info(f"ADS enabled with profile: {profile_name}")
            except Exception as e:
                logger.error(
                    f"Failed to load ADS profile '{profile_name}': {e}. Falling back to legacy mode.",
                    exc_info=True,
                )
                self._ads_enabled = False
                self._fingerprint_profile = None
        else:
            self._fingerprint_profile = None
            if not ADS_AVAILABLE:
                logger.debug("ADS not available (emulation module not imported)")
            else:
                logger.debug("ADS disabled in configuration")

        # Initialize ML components if enabled
        self._ml_enabled = (
            self._ads_enabled and hasattr(config, "ml") and config.ml.enabled
        )

        if self._ml_enabled:
            try:
                from ..ml import TTPPredictor, AdaptiveResponseGenerator
                from pathlib import Path

                # Get model path relative to plugin directory
                plugin_dir = Path(__file__).parent.parent
                model_path = plugin_dir / config.ml.model_path

                self._ttp_predictor = TTPPredictor(model_path=model_path)
                self._adaptive_generator = AdaptiveResponseGenerator()
                logger.info(f"ML prediction enabled with model: {model_path.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize ML components: {e}. ML disabled.")
                self._ml_enabled = False
                self._ttp_predictor = None
                self._adaptive_generator = None
        else:
            self._ttp_predictor = None
            self._adaptive_generator = None
            logger.debug("ML prediction disabled")

    async def start(self, port: Optional[int] = None) -> None:
        """Start SSH honeypot server.

        Args:
            port: Port to listen on (overrides config)
        """
        if self._running:
            return

        if not ASYNCSSH_AVAILABLE:
            logger.error("Cannot start SSH honeypot: asyncssh not installed")
            return

        listen_port = port or self.config.ssh_port

        try:
            # Generate or load host key
            host_key = await self._get_or_create_host_key()

            self._server = await asyncssh.create_server(
                lambda: SSHServerProtocol(self),
                "",
                listen_port,
                server_host_keys=[host_key],
                process_factory=self._handle_process,
                line_editor=True,
            )

            self._running = True
            logger.info(f"SSH honeypot started on port {listen_port}")
        except OSError as e:
            logger.error(f"Failed to start SSH honeypot: {e}")
            raise

    async def stop(self) -> None:
        """Stop SSH honeypot server."""
        if not self._running:
            return

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        self._running = False
        logger.info("SSH honeypot stopped")

    async def _get_or_create_host_key(self):
        """Get or create SSH host key."""
        import os
        from pathlib import Path

        key_path = Path(__file__).parent.parent / "data" / "ssh_host_key"
        key_path.parent.mkdir(parents=True, exist_ok=True)

        if key_path.exists():
            return asyncssh.read_private_key(key_path)

        # Generate new key
        key = asyncssh.generate_private_key("ssh-rsa", key_size=2048)
        key_path.write_bytes(key.export_private_key())
        os.chmod(key_path, 0o600)
        return key

    def validate_password(self, username: str, password: str) -> bool:
        """Validate SSH password (always accept configured weak passwords).

        Args:
            username: Attempted username
            password: Attempted password

        Returns:
            True if password should be "accepted" (for honeypot purposes)
        """
        return password in self.config.ssh_allowed_passwords

    async def handle_auth_attempt(
        self,
        session_id: str,
        source_ip: str,
        source_port: int,
        username: str,
        password: str,
        success: bool,
    ) -> None:
        """Handle authentication attempt.

        Args:
            session_id: Session ID
            source_ip: Attacker IP
            source_port: Attacker port
            username: Attempted username
            password: Attempted password
            success: Whether auth was "successful"
        """
        # HoneyDOC Stealth: Apply realistic delay
        await self.apply_stealth_delay()

        # HoneyDOC Flow Control: Check if traffic allowed
        if not self.check_flow_allowed(source_ip, session_id):
            return

        # Check for brute force pattern
        patterns = []
        category = AttackCategory.CREDENTIAL_HARVESTING

        # Detect common attack patterns in username/password
        combined = f"{username}:{password}"
        detected, _ = self.detect_patterns(combined)
        patterns.extend(detected)

        event = AttackEvent(
            event_id=self._generate_event_id(),
            session_id=session_id,
            honeypot_id=self.config.cluster.node_id or "default",
            protocol=HoneypotProtocol.SSH,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            source_port=source_port,
            event_type="auth",
            raw_data=f"user={username} pass={password} success={success}",
            username=username,
            password=password,
            detected_patterns=patterns,
            category=category,
            severity=self.calculate_severity(category, patterns),
        )

        await self.emit_event(event)

    def _get_or_create_filesystem(
        self, session_id: str, username: str = "admin"
    ) -> VirtualFilesystem:
        """Get or create virtual filesystem for session (legacy mode).

        Args:
            session_id: Session ID
            username: Username for the session

        Returns:
            VirtualFilesystem instance
        """
        if session_id not in self._filesystems:
            fingerprint = self.get_fingerprint()
            hostname = fingerprint.get("hostname", self.config.ssh_server_name)
            self._filesystems[session_id] = VirtualFilesystem(
                username=username, hostname=hostname
            )

        return self._filesystems[session_id]

    def _get_or_create_emulator(
        self, session_id: str, username: str = "admin"
    ) -> Optional[StatefulEmulator]:
        """Get or create StatefulEmulator for session (ADS mode).

        Args:
            session_id: Session ID
            username: Username for the session

        Returns:
            StatefulEmulator instance or None if ADS disabled
        """
        if not self._ads_enabled:
            return None

        if session_id not in self._emulators:
            # Use ML components if available
            ttp_predictor = self._ttp_predictor if self._ml_enabled else None
            adaptive_generator = self._adaptive_generator if self._ml_enabled else None

            self._emulators[session_id] = StatefulEmulator(
                session_id=session_id,
                fingerprint_profile=self._fingerprint_profile,
                enable_latency=self.config.emulation.enable_latency_simulation,
                ttp_predictor=ttp_predictor,
                adaptive_generator=adaptive_generator,
            )

            logger.debug(
                f"Created ADS emulator for session {session_id} (ML: {self._ml_enabled})"
            )

        return self._emulators[session_id]

    async def handle_command(
        self,
        session_id: str,
        source_ip: str,
        source_port: int,
        command: str,
        username: str = "admin",
    ) -> str:
        """Handle SSH command execution.

        Args:
            session_id: Session ID
            source_ip: Attacker IP
            source_port: Attacker port
            command: Command to execute
            username: Username of the attacker

        Returns:
            Fake command output
        """
        # HoneyDOC Stealth: Apply realistic delay
        await self.apply_stealth_delay()

        # HoneyDOC Flow Control: Check if traffic allowed
        if not self.check_flow_allowed(source_ip, session_id):
            return ""

        cmd_parts = command.strip().split()
        cmd_name = cmd_parts[0].lower() if cmd_parts else ""

        # Skip event emission for shell initialization commands
        if cmd_name in SHELL_BUILTINS or cmd_name.startswith(":"):
            return self._generate_command_response(session_id, command, username)

        # Detect patterns
        patterns, category = self.detect_patterns(command)
        severity = self.calculate_severity(category, patterns)

        # Create event
        event = AttackEvent(
            event_id=self._generate_event_id(),
            session_id=session_id,
            honeypot_id=self.config.cluster.node_id or "default",
            protocol=HoneypotProtocol.SSH,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            source_port=source_port,
            event_type="command",
            raw_data=command,
            command=command,
            detected_patterns=patterns,
            category=category,
            severity=severity,
        )

        await self.emit_event(event)

        # Generate response
        return await self._generate_command_response(session_id, command, username)

    async def _generate_command_response(
        self, session_id: str, command: str, username: str = "admin"
    ) -> str:
        """Generate fake command response using ADS or legacy processor.

        Args:
            session_id: Session ID
            command: Command to respond to
            username: Username of the attacker

        Returns:
            Fake output
        """
        # Use ADS StatefulEmulator if enabled
        emulator = self._get_or_create_emulator(session_id, username)
        if emulator:
            try:
                response = await emulator.process_command(command)
                return response.output or ""
            except Exception as e:
                logger.error(
                    f"ADS emulation failed for command '{command}': {e}. Falling back to legacy."
                )
                # Fallback to legacy on error

        # Legacy mode: use CommandProcessor
        vfs = self._get_or_create_filesystem(session_id, username)
        fingerprint = self.get_fingerprint()
        processor = CommandProcessor(vfs, fingerprint)
        return processor.process_command(command)

    def get_session(self, session_id: str) -> Optional[HoneypotSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def get_sessions(self) -> list[HoneypotSession]:
        """Get all sessions."""
        return list(self._sessions.values())

    async def _handle_process(self, process) -> None:
        """Handle SSH process (command execution or interactive shell).

        Args:
            process: asyncssh SSHServerProcess object
        """
        session_id = self._generate_session_id()

        try:
            # Get connection info
            conn = process.channel.get_connection()
            peername = conn.get_extra_info("peername")
            source_ip = peername[0] if peername else "unknown"
            source_port = peername[1] if peername else 0

            # Get username from connection (if available)
            username = conn.get_extra_info("username", "admin")

            command = process.command

            if command:
                # Single command execution
                output = await self.handle_command(
                    session_id=session_id,
                    source_ip=source_ip,
                    source_port=source_port,
                    command=command,
                    username=username,
                )
                process.stdout.write(output + "\n")
                process.exit(0)
            else:
                # Interactive shell
                # Get VFS or Emulator to use dynamic prompt
                emulator = self._get_or_create_emulator(session_id, username)

                if emulator:
                    # ADS mode: use emulator's prompt
                    def prompt_func():
                        try:
                            return emulator.get_prompt()
                        except Exception as e:
                            logger.error(f"Error generating prompt: {e}")
                            return "$ "

                    welcome_msg = f"\nWelcome to {emulator.session.hostname}\n\n"
                else:
                    # Legacy mode: use VFS prompt
                    vfs = self._get_or_create_filesystem(session_id, username)

                    def prompt_func():
                        return vfs.get_prompt()

                    welcome_msg = f"\nWelcome to {self.config.ssh_server_name}\n\n"

                process.stdout.write(welcome_msg)
                process.stdout.write(prompt_func())

                try:
                    async for line in process.stdin:
                        line = line.strip()
                        if not line:
                            process.stdout.write(prompt_func())
                            continue

                        if line.lower() in ("exit", "quit", "logout"):
                            process.stdout.write("logout\n")
                            break

                        output = await self.handle_command(
                            session_id=session_id,
                            source_ip=source_ip,
                            source_port=source_port,
                            command=line,
                            username=username,
                        )
                        if output:
                            process.stdout.write(output + "\n")
                        # Get updated prompt (in case directory changed)
                        process.stdout.write(prompt_func())
                except asyncssh.BreakReceived:
                    pass
                except asyncssh.TerminalSizeChanged:
                    pass

                # Clean up filesystem/emulator on session end
                if session_id in self._filesystems:
                    del self._filesystems[session_id]
                if session_id in self._emulators:
                    del self._emulators[session_id]

                process.exit(0)

        except Exception as e:
            logger.error(f"CRITICAL ERROR in SSH _handle_process: {e}", exc_info=True)
            process.stderr.write("Internal Server Error\n")
            process.exit(1)

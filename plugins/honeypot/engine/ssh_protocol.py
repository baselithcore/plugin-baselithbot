from core.observability.logging import get_logger
import asyncio
import asyncssh
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ssh_handler import SSHHandler

logger = get_logger(__name__)


class SSHServerProtocol(asyncssh.SSHServer):
    """SSH server protocol handler."""

    def __init__(self, handler: "SSHHandler"):
        self.handler = handler
        self.session_id = handler._generate_session_id()
        self.source_ip = "unknown"
        self.source_port = 0
        self.auth_attempts = 0
        self.first_auth_time = None

    def connection_made(self, conn):
        """Handle new connection."""
        peername = conn.get_extra_info("peername")
        if peername:
            self.source_ip = peername[0]
            self.source_port = peername[1]

        # Feature: Service Rate Limiting
        if not self.handler.check_rate_limit(self.source_ip):
            logger.warning(
                f"Rate limit exceeded for {self.source_ip}, dropping SSH connection"
            )
            conn.close()
            return

        logger.info(f"SSH connection from {self.source_ip}:{self.source_port}")

    def connection_lost(self, exc):
        """Handle connection close."""
        reason = f" ({exc})" if exc else " (clean disconnect)"
        logger.info(f"SSH connection closed from {self.source_ip}{reason}")

    def begin_auth(self, username: str) -> bool:
        """Begin authentication."""
        return True  # Allow password auth

    def password_auth_supported(self) -> bool:
        """Support password authentication."""
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        """Validate password with realistic timing and fail2ban simulation."""
        import time

        self.auth_attempts += 1

        # Track first auth time for fail2ban simulation
        if self.first_auth_time is None:
            self.first_auth_time = time.time()

        # Check fail2ban status for this IP
        fail2ban_threshold = getattr(self.handler.config, "ssh_fail2ban_threshold", 5)
        fail2ban_timeout = getattr(self.handler.config, "ssh_fail2ban_timeout", 600)

        # Simple fail2ban simulation using handler's internal tracking
        if not hasattr(self.handler, "_failed_auth_tracker"):
            self.handler._failed_auth_tracker = {}

        tracker_key = self.source_ip
        current_time = time.time()

        # Clean up old entries
        if tracker_key in self.handler._failed_auth_tracker:
            failed_attempts = self.handler._failed_auth_tracker[tracker_key]
            # Remove attempts older than timeout
            failed_attempts["attempts"] = [
                t
                for t in failed_attempts["attempts"]
                if current_time - t < fail2ban_timeout
            ]

            # Check if IP is banned
            if len(failed_attempts["attempts"]) >= fail2ban_threshold:
                logger.warning(
                    f"fail2ban: Dropping connection from {self.source_ip} "
                    f"({len(failed_attempts['attempts'])} failed attempts)"
                )
                # Simulate fail2ban drop with a realistic delay
                await asyncio.sleep(random.uniform(0.5, 1.5))
                return False

        # Realistic authentication delay (increases with failed attempts)
        base_delay = getattr(self.handler.config, "ssh_auth_delay_min", 150) / 1000.0
        max_delay = getattr(self.handler.config, "ssh_auth_delay_max", 350) / 1000.0

        # Add progressive delay for brute force mitigation
        progressive_delay = self.auth_attempts * 0.1
        delay = random.uniform(base_delay, max_delay) + progressive_delay
        await asyncio.sleep(delay)

        # Validate password
        success = self.handler.validate_password(username, password)

        # Track failed attempts for fail2ban
        if not success:
            if tracker_key not in self.handler._failed_auth_tracker:
                self.handler._failed_auth_tracker[tracker_key] = {"attempts": []}
            self.handler._failed_auth_tracker[tracker_key]["attempts"].append(
                current_time
            )

        # Log the attempt
        try:
            await self.handler.handle_auth_attempt(
                session_id=self.session_id,
                source_ip=self.source_ip,
                source_port=self.source_port,
                username=username,
                password=password,
                success=success,
            )
        except Exception as e:
            logger.error(f"Error logging auth attempt: {e}", exc_info=True)

        # Disconnect after too many attempts in this session
        if self.auth_attempts >= self.handler.config.ssh_max_auth_attempts:
            logger.info(
                f"Max auth attempts reached for {self.source_ip}, disconnecting"
            )
            return False

        return success

    def session_requested(self) -> bool:
        """Allow session requests."""
        return True

    def pty_requested(
        self,
        term_type: str,
        term_size: tuple,
        term_modes: dict,
    ) -> bool:
        """Accept PTY requests."""
        logger.debug(f"PTY requested: {term_type} {term_size}")
        return True

    def shell_requested(self) -> bool:
        """Accept shell requests."""
        return True

    def exec_requested(self, command: str) -> bool:
        """Accept exec requests."""
        return True

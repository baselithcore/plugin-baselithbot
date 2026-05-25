"""TCP Honeypot Handler.

Generic TCP port listener for capturing arbitrary connections
on common service ports (FTP, Telnet, MySQL, Redis, etc.).
"""

import asyncio
from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ..config import HoneypotConfig, get_honeypot_config
from ..models import AttackEvent, HoneypotProtocol
from .base import BaseHandler

logger = get_logger(__name__)


# Protocol-specific banners
DEFAULT_BANNERS = {
    21: "220 FTP Server ready.\r\n",
    23: "\r\n\r\nUbuntu 20.04 LTS\r\nlogin: ",
    25: "220 mail.example.com ESMTP Postfix\r\n",
    110: "+OK POP3 server ready\r\n",
    143: "* OK IMAP4 Server ready\r\n",
    3306: None,  # MySQL uses binary protocol
    5432: None,  # PostgreSQL uses binary protocol
    6379: "+OK\r\n",  # Redis
    27017: None,  # MongoDB binary
}

# Protocol-specific response patterns
PROTOCOL_RESPONSES = {
    21: {  # FTP
        "USER": "331 Password required for {}\r\n",
        "PASS": "530 Login incorrect.\r\n",
        "QUIT": "221 Goodbye.\r\n",
        "LIST": "150 Opening data connection.\r\n550 Permission denied.\r\n",
        "PWD": '257 "/" is current directory.\r\n',
        "DEFAULT": "500 Unknown command.\r\n",
    },
    23: {  # Telnet
        "DEFAULT": "Login incorrect\r\n\r\nlogin: ",
    },
    25: {  # SMTP
        "HELO": "250 Hello {}\r\n",
        "EHLO": "250-mail.example.com\r\n250-SIZE 35882577\r\n250 8BITMIME\r\n",
        "MAIL FROM": "250 OK\r\n",
        "RCPT TO": "550 No such user\r\n",
        "QUIT": "221 Bye\r\n",
        "DEFAULT": "500 Command not recognized\r\n",
    },
    6379: {  # Redis
        "PING": "+PONG\r\n",
        "AUTH": "-ERR invalid password\r\n",
        "INFO": "-NOAUTH Authentication required.\r\n",
        "KEYS": "-NOAUTH Authentication required.\r\n",
        "CONFIG": "-NOAUTH Authentication required.\r\n",
        "DEFAULT": "-ERR unknown command\r\n",
    },
}


class TCPHandler(BaseHandler):
    """Generic TCP honeypot for multiple protocols."""

    def __init__(
        self,
        config: Optional[HoneypotConfig] = None,
        on_event: Optional[Callable[[AttackEvent], None]] = None,
        definition: Any = None,
    ):
        """Initialize TCP honeypot.

        Args:
            config: Honeypot configuration
            on_event: Callback for attack events
        """
        super().__init__(config or get_honeypot_config())
        self._on_event = on_event
        self._servers: Dict[int, asyncio.AbstractServer] = {}
        self._sessions: Dict[str, Dict[str, Any]] = {}

    async def start(self, port: Optional[int] = None) -> None:
        """Start TCP honeypot on configured ports.

        Args:
            port: Optional specific port to listen on (overrides config)
        """
        ports = [port] if port else self.config.tcp_ports

        for p in ports:
            try:
                server = await asyncio.start_server(
                    lambda r, w, port=p: self._handle_connection(r, w, port),
                    host="0.0.0.0",  # nosec B104
                    port=p,
                )
                self._servers[p] = server
                logger.info(f"TCP honeypot listening on port {p}")

            except OSError as e:
                logger.error(f"Failed to bind to port {p}: {e}")

    async def stop(self) -> None:
        """Stop all TCP servers."""
        for port, server in self._servers.items():
            server.close()
            await server.wait_closed()
            logger.info(f"TCP honeypot stopped on port {port}")

        self._servers.clear()

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming TCP connection.

        Args:
            reader: Stream reader
            writer: Stream writer
        """
        # Get connection info
        peername = writer.get_extra_info("peername")
        sockname = writer.get_extra_info("sockname")

        if not peername or not sockname:
            writer.close()
            return

        source_ip, source_port = peername
        _, local_port = sockname

        session_id = f"tcp-{uuid4().hex[:8]}"

        # Feature: Service Rate Limiting
        if not self.check_rate_limit(source_ip):
            logger.warning(
                f"Rate limit exceeded for {source_ip}, dropping TCP connection"
            )
            writer.close()
            return

        self._sessions[session_id] = {
            "source_ip": source_ip,
            "source_port": source_port,
            "local_port": local_port,
            "started_at": datetime.now(timezone.utc),
            "data_received": [],
        }

        logger.info(
            f"TCP connection from {source_ip}:{source_port} to port {local_port}"
        )

        try:
            # Send banner if available
            banner = self._get_banner(local_port)
            if banner:
                writer.write(banner.encode())
                await writer.drain()

            # Read data with timeout
            while True:
                try:
                    data = await asyncio.wait_for(
                        reader.read(4096),
                        timeout=self.config.max_session_duration_seconds,
                    )

                    if not data:
                        break

                    # Process received data
                    await self._process_data(
                        session_id=session_id,
                        data=data,
                        source_ip=source_ip,
                        source_port=source_port,
                        local_port=local_port,
                        writer=writer,
                    )

                except asyncio.TimeoutError:
                    break

        except (ConnectionResetError, BrokenPipeError):
            pass

        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass  # nosec B110

            # Cleanup session
            if session_id in self._sessions:
                del self._sessions[session_id]

            logger.debug(f"TCP connection closed: {session_id}")

    async def _process_data(
        self,
        session_id: str,
        data: bytes,
        source_ip: str,
        source_port: int,
        local_port: int,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process received data and generate response.

        Args:
            session_id: Session ID
            data: Raw bytes received
            source_ip: Attacker IP
            source_port: Attacker port
            local_port: Local honeypot port
            writer: Stream writer for responses
        """
        try:
            payload = data.decode("utf-8", errors="replace").strip()
        except Exception:
            payload = data.hex()

        # Store in session
        self._sessions[session_id]["data_received"].append(payload)

        # Detect attack patterns
        patterns, category = self.detect_patterns(payload)
        severity = self.calculate_severity(category, patterns)

        # Create attack event
        event = AttackEvent(
            event_id=f"tcp-evt-{uuid4().hex[:8]}",
            session_id=session_id,
            protocol=HoneypotProtocol.TCP,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            source_port=source_port,
            event_type="payload",
            raw_data=payload[: self.config.max_payload_size_kb * 1024],
            detected_patterns=patterns,
            category=category,
            severity=severity,
        )

        # Emit event
        if self._on_event:
            await self._on_event(event)

        # Log if significant
        if patterns:
            logger.warning(
                f"TCP attack detected on port {local_port} from {source_ip}: "
                f"{category.value} ({len(patterns)} patterns)"
            )

        # Send protocol-specific response
        response = self._get_response(local_port, payload)
        if response:
            try:
                writer.write(response.encode())
                await writer.drain()
            except Exception:
                pass  # nosec B110

    def _get_banner(self, port: int) -> Optional[str]:
        """Get banner for port."""
        # Check custom banners from config first
        custom = self.config.tcp_banners.get(str(port))
        if custom:
            return custom

        return DEFAULT_BANNERS.get(port)

    def _get_response(self, port: int, payload: str) -> Optional[str]:
        """Get response for payload on port."""
        responses = PROTOCOL_RESPONSES.get(port, {})
        if not responses:
            return None

        # Find matching response
        payload_upper = payload.upper()
        for cmd, response in responses.items():
            if cmd != "DEFAULT" and payload_upper.startswith(cmd):
                # Handle format strings
                if "{}" in response:
                    parts = payload.split()
                    arg = parts[1] if len(parts) > 1 else "anonymous"
                    return response.format(arg)
                return response

        return responses.get("DEFAULT")

    def get_protocol_info(self, port: int) -> Dict[str, Any]:
        """Get protocol info for a port.

        Args:
            port: Port number

        Returns:
            Protocol information
        """
        protocol_names = {
            21: "FTP",
            23: "Telnet",
            25: "SMTP",
            110: "POP3",
            143: "IMAP",
            3306: "MySQL",
            5432: "PostgreSQL",
            6379: "Redis",
            27017: "MongoDB",
        }

        return {
            "port": port,
            "protocol": protocol_names.get(port, "Unknown"),
            "has_banner": port in DEFAULT_BANNERS and DEFAULT_BANNERS[port] is not None,
            "has_responses": port in PROTOCOL_RESPONSES,
        }

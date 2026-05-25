"""Example Custom Honeypot Handler.

This file demonstrates how to create a custom honeypot handler by inheriting
from BaseHandler. You can use this template to implement handlers for
protocols like FTP, Telnet, Redis, etc.

To use this handler:
1. Rename/Copy this file (e.g., `ftp_handler.py`).
2. Implement the protocol logic in `handle_client`.
3. Register it in `coordinator.py`.
"""

import asyncio
from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from ..config import HoneypotConfig
from ..models import (
    AttackCategory,
    AttackEvent,
    AttackSeverity,
    HoneypotProtocol,
)
from .base import BaseHandler

logger = get_logger(__name__)


class CustomTCPHandler(BaseHandler):
    """Example custom TCP honeypot handler (e.g., Simple Telnet simulation)."""

    def __init__(self, config: HoneypotConfig):
        """Initialize the handler."""
        super().__init__(config)
        self._server: Optional[asyncio.AbstractServer] = None
        # Example: Listen on a custom port defined in config or hardcoded for example
        self._port = 2323  # Example: Telnet-like port

    async def start(self) -> None:
        """Start the custom honeypot service."""
        if self._running:
            return

        try:
            self._server = await asyncio.start_server(
                self.handle_connection,
                "0.0.0.0",  # nosec B104
                self._port,
            )
            self._running = True
            logger.info(f"Custom TCP Honeypot started on port {self._port}")

            # Keep serving indefinitely until stopped
            async with self._server:
                await self._server.serve_forever()

        except asyncio.CancelledError:
            # Normal shutdown
            pass
        except Exception as e:
            logger.error(f"Failed to start Custom TCP Honeypot: {e}")
            self._running = False

    async def stop(self) -> None:
        """Stop the custom honeypot service."""
        if not self._running:
            return

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._running = False
        logger.info("Custom TCP Honeypot stopped")

    async def handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming TCP connection."""
        addr = writer.get_extra_info("peername")
        source_ip = addr[0] if addr else "unknown"
        source_port = addr[1] if addr else 0
        session_id = self._generate_session_id()

        logger.info(f"New connection from {source_ip}:{source_port}")

        try:
            # 1. Send initial banner (Deception)
            writer.write(b"Welcome to Legacy System v2.0\r\nLogin: ")
            await writer.drain()

            # 2. Read input (Capture)
            # Simple line-based reading for example
            username_bytes = await reader.readuntil(b"\n")
            username = username_bytes.decode().strip()

            writer.write(b"Password: ")
            await writer.drain()

            password_bytes = await reader.readuntil(b"\n")
            password = password_bytes.decode().strip()

            # 3. Analyze captured data
            # Combine inputs to check for patterns
            full_payload = f"User: {username}, Pass: {password}"
            detected_patterns, category = self.detect_patterns(full_payload)

            # Calculate severity
            severity = self.calculate_severity(category, detected_patterns)

            # If nothing specific detected but they tried to login, mark as Low/Credential Harvesting
            if category == AttackCategory.UNKNOWN:
                category = AttackCategory.CREDENTIAL_HARVESTING
                severity = AttackSeverity.LOW

            # 4. create and Emit Event
            event = AttackEvent(
                event_id=self._generate_event_id(),
                session_id=session_id,
                protocol=HoneypotProtocol.TCP,  # Or add your CUSTOM enum if you extended it
                timestamp=datetime.now(timezone.utc).isoformat(),
                source_ip=source_ip,
                source_port=source_port,
                geo=None,  # Geo enrichment happens in coordinator or separately
                event_type="login_attempt",
                raw_data=full_payload,
                username=username,
                password=password,
                command=None,
                http_method=None,
                http_path=None,
                http_headers=None,
                http_body=None,
                detected_patterns=detected_patterns,
                category=category,
                severity=severity,
                ai_classification=None,
                matched_cves=[],
                matched_cwes=[],
                correlation_confidence=None,
            )

            await self.emit_event(event)

            # 5. Finalize interaction
            # Fake failure
            writer.write(b"\r\nLogin incorrect\r\n")
            await writer.drain()

        except Exception as e:
            logger.warning(f"Error handling connection from {source_ip}: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass  # nosec B110

"""S7CommHandler — core handler class."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from core.observability.logging import get_logger

from ...base import BaseHandler
from ....models import AttackCategory, AttackEvent, AttackSeverity, HoneypotProtocol
from ._constants import COTP_CR, COTP_DT, TPKT_HEADER_SIZE, TPKT_VERSION
from ._protocol import S7ProtocolMixin

import struct

logger = get_logger(__name__)


class S7CommHandler(S7ProtocolMixin, BaseHandler):
    """S7comm/COTP PLC honeypot handler.

    Emulates a Siemens S7-300/400 PLC with configurable CPU identification,
    data block memory, and attack event emission.
    """

    def __init__(self, config, definition=None):
        """Initialize S7comm handler.

        Args:
            config: HoneypotConfig instance.
            definition: HoneypotDefinition from YAML.
        """
        super().__init__(config, definition=definition)
        self._server: Optional[asyncio.AbstractServer] = None
        self._protocol = HoneypotProtocol.S7COMM

        s7_config = None
        if definition:
            s7_config = definition.get_protocol_config()

        self._rack = getattr(s7_config, "rack", 0)
        self._slot = getattr(s7_config, "slot", 2)
        self._cpu_type = getattr(s7_config, "cpu_type", "CPU 315-2 PN/DP")
        self._order_code = getattr(s7_config, "order_code", "6ES7 315-2EH14-0AB0")
        self._serial_number = getattr(s7_config, "serial_number", "S C-HONYPOT0001")
        self._module_info = getattr(s7_config, "module_info", "S7-300")

        # Initialize DB block memory
        raw_dbs = getattr(s7_config, "db_blocks", {1: {"size": 256, "fill": 0}})
        self._db_memory: Dict[int, bytearray] = {}
        for db_num, db_conf in raw_dbs.items():
            size = db_conf.get("size", 256) if isinstance(db_conf, dict) else 256
            fill = db_conf.get("fill", 0) if isinstance(db_conf, dict) else 0
            self._db_memory[int(db_num)] = bytearray([fill & 0xFF] * size)

    async def start(self, port: int = 102) -> None:
        """Start S7comm honeypot server.

        Args:
            port: TCP port to listen on (default 102, ISO-on-TCP).
        """
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",  # nosec B104
            port,
        )
        self._running = True
        logger.info(f"S7comm PLC honeypot started on port {port}")

    async def stop(self) -> None:
        """Stop S7comm honeypot server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("S7comm PLC honeypot stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming ISO-on-TCP connection."""
        peer = writer.get_extra_info("peername")
        source_ip = peer[0] if peer else "unknown"
        session_id = f"s7-{uuid.uuid4().hex[:12]}"

        logger.info(f"S7comm connection from {source_ip}")

        try:
            while self._running:
                # Read TPKT header (4 bytes)
                tpkt = await asyncio.wait_for(
                    reader.readexactly(TPKT_HEADER_SIZE), timeout=30.0
                )
                if len(tpkt) < TPKT_HEADER_SIZE:
                    break

                version = tpkt[0]
                total_length = struct.unpack(">H", tpkt[2:4])[0]

                if version != TPKT_VERSION or total_length < TPKT_HEADER_SIZE:
                    break

                # Read remaining data
                payload_length = total_length - TPKT_HEADER_SIZE
                if payload_length <= 0:
                    break

                payload = await asyncio.wait_for(
                    reader.readexactly(payload_length), timeout=10.0
                )

                await self._apply_stealth_delay_async()

                # Parse COTP header
                cotp_length = payload[0]
                cotp_pdu_type = payload[1] & 0xF0

                if cotp_pdu_type == COTP_CR:
                    response = self._handle_cotp_cr(payload, source_ip, session_id)
                elif cotp_pdu_type == COTP_DT:
                    # S7comm data after COTP DT header
                    s7_offset = cotp_length + 1
                    if s7_offset < len(payload):
                        response = self._handle_s7_data(
                            payload[s7_offset:], source_ip, session_id
                        )
                    else:
                        continue
                else:
                    continue

                if response:
                    writer.write(response)
                    await writer.drain()

        except asyncio.TimeoutError:
            pass
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        except Exception as e:
            logger.debug(f"S7comm connection error from {source_ip}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _emit_event(self, **kwargs) -> None:
        """Emit an attack event via the configured callback."""
        if not self._event_callback:
            return

        event = AttackEvent(
            event_id=str(uuid.uuid4()),
            session_id=kwargs.get("session_id", ""),
            honeypot_id=(self.definition.id if self.definition else "s7comm-default"),
            protocol=HoneypotProtocol.S7COMM,
            timestamp=datetime.now(timezone.utc),
            source_ip=kwargs.get("source_ip", "unknown"),
            source_port=kwargs.get("source_port", 0),
            event_type=kwargs.get("event_type", "s7_event"),
            command=kwargs.get("command"),
            raw_data=kwargs.get("raw_data", ""),
            category=kwargs.get("category", AttackCategory.PLC_SCAN),
            severity=kwargs.get("severity", AttackSeverity.MEDIUM),
            detected_patterns=kwargs.get("detected_patterns", []),
        )

        try:
            self._event_callback(event)
        except Exception as e:
            logger.error(f"Failed to emit S7comm event: {e}")

    async def _apply_stealth_delay_async(self) -> None:
        """Apply realistic response delay."""
        delay_ms = getattr(self._config, "stealth_response_delay_ms", 50)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

"""MQTT Broker Honeypot Handler.

Emulates an MQTT v3.1.1 broker for IoT honeypotting.
Parses the raw MQTT binary protocol from TCP without external dependencies.

Supported Packet Types:
  CONNECT   (1)  - Client authentication and connection tracking
  PUBLISH   (3)  - Topic-based message interception
  SUBSCRIBE (8)  - Subscription pattern monitoring
  PINGREQ   (12) - Keep-alive handling
  DISCONNECT (14) - Clean disconnect

Attack detection:
  - Credential brute-force attempts
  - Suspicious topic subscriptions ($SYS, firmware, cmd)
  - Payload injection via PUBLISH to control topics
"""

import asyncio
from core.observability.logging import get_logger
import struct
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from ..base import BaseHandler
from ...models import AttackCategory, AttackSeverity, HoneypotProtocol

logger = get_logger(__name__)

# MQTT packet type constants
CONNECT = 1
CONNACK = 2
PUBLISH = 3
PUBACK = 4
SUBSCRIBE = 8
SUBACK = 9
PINGREQ = 12
PINGRESP = 13
DISCONNECT = 14

# CONNACK return codes
CONNACK_ACCEPTED = 0
CONNACK_BAD_PROTOCOL = 1
CONNACK_ID_REJECTED = 2
CONNACK_SERVER_UNAVAILABLE = 3
CONNACK_BAD_CREDENTIALS = 4
CONNACK_NOT_AUTHORIZED = 5


def _decode_remaining_length(reader_data: bytes, offset: int) -> tuple[int, int]:
    """Decode MQTT variable-length encoding.

    Returns:
        Tuple of (remaining_length, bytes_consumed).
    """
    multiplier = 1
    value = 0
    idx = offset
    while idx < len(reader_data):
        encoded_byte = reader_data[idx]
        value += (encoded_byte & 0x7F) * multiplier
        idx += 1
        if (encoded_byte & 0x80) == 0:
            break
        multiplier *= 128
        if multiplier > 128 * 128 * 128:
            raise ValueError("Malformed remaining length")
    return value, idx - offset


def _decode_utf8_string(data: bytes, offset: int) -> tuple[str, int]:
    """Decode MQTT UTF-8 prefixed string.

    Returns:
        Tuple of (decoded_string, total_bytes_consumed).
    """
    if offset + 2 > len(data):
        return "", 0
    str_len = struct.unpack(">H", data[offset : offset + 2])[0]
    start = offset + 2
    end = start + str_len
    if end > len(data):
        return "", 0
    return data[start:end].decode("utf-8", errors="replace"), 2 + str_len


class MQTTHandler(BaseHandler):
    """MQTT broker honeypot handler.

    Emulates an MQTT v3.1.1 broker with credential trapping and
    topic monitoring for IoT/ICS attack detection.
    """

    def __init__(self, config, definition=None):
        """Initialize MQTT handler.

        Args:
            config: HoneypotConfig instance.
            definition: HoneypotDefinition from YAML.
        """
        super().__init__(config, definition=definition)
        self._server: Optional[asyncio.AbstractServer] = None
        self._protocol = HoneypotProtocol.MQTT

        mqtt_config = None
        if definition:
            mqtt_config = definition.get_protocol_config()

        self._allow_anonymous = getattr(mqtt_config, "allow_anonymous", True)
        self._valid_credentials: List[Dict[str, str]] = getattr(
            mqtt_config,
            "valid_credentials",
            [{"username": "admin", "password": "admin"}],
        )
        self._monitored_topics: List[str] = getattr(
            mqtt_config,
            "monitored_topics",
            ["factory/#", "plc/#", "sensor/#", "$SYS/#", "cmd/#"],
        )
        self._max_qos = getattr(mqtt_config, "max_qos", 2)
        self._broker_name = getattr(
            mqtt_config, "broker_name", "Eclipse Mosquitto/2.0.18"
        )

        # Runtime state
        self._connected_clients: Set[str] = set()

    async def start(self, port: int = 1883) -> None:
        """Start MQTT broker honeypot.

        Args:
            port: TCP port to listen on (default 1883).
        """
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",  # nosec B104
            port,
        )
        self._running = True
        logger.info(f"MQTT broker honeypot started on port {port}")

    async def stop(self) -> None:
        """Stop MQTT broker honeypot."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._connected_clients.clear()
        logger.info("MQTT broker honeypot stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming MQTT client connection."""
        peer = writer.get_extra_info("peername")
        source_ip = peer[0] if peer else "unknown"
        source_port = peer[1] if peer else 0
        session_id = f"mqtt-{uuid.uuid4().hex[:12]}"
        client_id = "unknown"
        authenticated = False

        try:
            while self._running:
                # Read fixed header (at least 2 bytes)
                first_byte_data = await asyncio.wait_for(reader.read(1), timeout=60.0)
                if not first_byte_data:
                    break

                packet_type = (first_byte_data[0] >> 4) & 0x0F
                flags = first_byte_data[0] & 0x0F

                # Read remaining length (variable encoding, up to 4 bytes)
                remaining_bytes = b""
                for _ in range(4):
                    b = await asyncio.wait_for(reader.read(1), timeout=10.0)
                    if not b:
                        break
                    remaining_bytes += b
                    if (b[0] & 0x80) == 0:
                        break

                if not remaining_bytes:
                    break

                remaining_length, _ = _decode_remaining_length(remaining_bytes, 0)

                # Read payload
                payload = b""
                if remaining_length > 0:
                    payload = await asyncio.wait_for(
                        reader.readexactly(remaining_length), timeout=10.0
                    )

                await self._apply_stealth_delay_async()

                # Dispatch
                if packet_type == CONNECT:
                    client_id, authenticated = self._handle_connect(
                        payload, source_ip, session_id, writer
                    )
                elif packet_type == PUBLISH:
                    self._handle_publish(
                        flags, payload, source_ip, session_id, client_id
                    )
                elif packet_type == SUBSCRIBE:
                    self._handle_subscribe(
                        payload, source_ip, session_id, client_id, writer
                    )
                elif packet_type == PINGREQ:
                    # PINGRESP: type=13, remaining=0
                    writer.write(bytes([PINGRESP << 4, 0]))
                    await writer.drain()
                elif packet_type == DISCONNECT:
                    break
                else:
                    # Unknown packet type — log it
                    self._emit_event(
                        source_ip=source_ip,
                        source_port=source_port,
                        session_id=session_id,
                        event_type="mqtt_unknown_packet",
                        command=f"PACKET_TYPE_{packet_type}",
                        raw_data=payload.hex()[:200],
                        category=AttackCategory.RECONNAISSANCE,
                        severity=AttackSeverity.LOW,
                    )

        except asyncio.TimeoutError:
            pass
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        except Exception as e:
            logger.debug(f"MQTT connection error from {source_ip}: {e}")
        finally:
            self._connected_clients.discard(client_id)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _handle_connect(
        self,
        payload: bytes,
        source_ip: str,
        session_id: str,
        writer: asyncio.StreamWriter,
    ) -> tuple[str, bool]:
        """Handle MQTT CONNECT packet.

        Returns:
            Tuple of (client_id, authenticated).
        """
        offset = 0
        # Protocol name
        proto_name, consumed = _decode_utf8_string(payload, offset)
        offset += consumed

        if offset >= len(payload):
            return "unknown", False

        # Protocol level
        proto_level = payload[offset]
        offset += 1

        # Connect flags
        if offset >= len(payload):
            return "unknown", False
        connect_flags = payload[offset]
        offset += 1
        has_username = bool(connect_flags & 0x80)
        has_password = bool(connect_flags & 0x40)

        # Keep-alive
        if offset + 2 > len(payload):
            return "unknown", False
        offset += 2  # skip keep-alive

        # Client ID
        client_id, consumed = _decode_utf8_string(payload, offset)
        offset += consumed

        # Extract credentials if present
        username = ""
        password = ""
        if has_username:
            username, consumed = _decode_utf8_string(payload, offset)
            offset += consumed
        if has_password:
            password, consumed = _decode_utf8_string(payload, offset)
            offset += consumed

        # Authentication check
        authenticated = False
        return_code = CONNACK_ACCEPTED

        if has_username:
            # Check against valid credentials
            for cred in self._valid_credentials:
                if (
                    cred.get("username") == username
                    and cred.get("password") == password
                ):
                    authenticated = True
                    break
            if not authenticated:
                return_code = CONNACK_BAD_CREDENTIALS

                self._emit_event(
                    source_ip=source_ip,
                    session_id=session_id,
                    event_type="mqtt_auth_failure",
                    command=f"CONNECT user={username}",
                    raw_data=f"client_id={client_id}",
                    category=AttackCategory.CREDENTIAL_HARVESTING,
                    severity=AttackSeverity.MEDIUM,
                    detected_patterns=["mqtt_brute_force"],
                )
                # Still allow connection for honeypot (trap)
                authenticated = True
                return_code = CONNACK_ACCEPTED
        elif self._allow_anonymous:
            authenticated = True
        else:
            return_code = CONNACK_NOT_AUTHORIZED

        # Send CONNACK
        # Fixed header: type=2, remaining=2
        # Variable: session_present=0, return_code
        connack = bytes([CONNACK << 4, 2, 0, return_code])
        writer.write(connack)

        self._connected_clients.add(client_id)

        self._emit_event(
            source_ip=source_ip,
            session_id=session_id,
            event_type="mqtt_connect",
            command=f"CONNECT proto={proto_name}/{proto_level} client={client_id}",
            raw_data=f"user={username}" if username else "anonymous",
            category=AttackCategory.RECONNAISSANCE,
            severity=AttackSeverity.LOW,
        )

        logger.info(
            f"MQTT CONNECT from {source_ip}: client={client_id} "
            f"user={username or 'anonymous'}"
        )

        return client_id, authenticated

    def _handle_publish(
        self,
        flags: int,
        payload: bytes,
        source_ip: str,
        session_id: str,
        client_id: str,
    ) -> None:
        """Handle MQTT PUBLISH packet."""
        offset = 0
        topic, consumed = _decode_utf8_string(payload, offset)
        offset += consumed

        qos = (flags >> 1) & 0x03

        # Skip packet identifier for QoS > 0
        if qos > 0 and offset + 2 <= len(payload):
            offset += 2

        # Remaining is the message payload
        message_data = payload[offset:].decode("utf-8", errors="replace")[:500]

        # Classify severity based on topic
        severity = AttackSeverity.MEDIUM
        category = AttackCategory.RECONNAISSANCE

        suspicious_prefixes = ("cmd/", "firmware/", "actuator/", "$SYS/")
        if any(topic.startswith(p) for p in suspicious_prefixes):
            severity = AttackSeverity.HIGH
            category = AttackCategory.SCADA_MANIPULATION

        if "update" in topic.lower() or "flash" in topic.lower():
            severity = AttackSeverity.CRITICAL
            category = AttackCategory.FIRMWARE_TAMPERING

        self._emit_event(
            source_ip=source_ip,
            session_id=session_id,
            event_type="mqtt_publish",
            command=f"PUBLISH topic={topic} qos={qos}",
            raw_data=message_data,
            category=category,
            severity=severity,
            detected_patterns=[f"mqtt_topic_{topic.split('/')[0]}"],
        )

        logger.info(
            f"MQTT PUBLISH from {source_ip} ({client_id}): "
            f"topic={topic} len={len(message_data)}"
        )

    def _handle_subscribe(
        self,
        payload: bytes,
        source_ip: str,
        session_id: str,
        client_id: str,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle MQTT SUBSCRIBE packet."""
        if len(payload) < 2:
            return

        # Packet identifier
        packet_id = struct.unpack(">H", payload[:2])[0]
        offset = 2

        topics: List[str] = []
        granted_qos: List[int] = []

        while offset < len(payload):
            topic, consumed = _decode_utf8_string(payload, offset)
            offset += consumed
            if offset < len(payload):
                requested_qos = payload[offset]
                offset += 1
            else:
                requested_qos = 0

            topics.append(topic)
            granted_qos.append(min(requested_qos, self._max_qos))

        # Send SUBACK
        suback = struct.pack(">BbH", SUBACK << 4, 2 + len(granted_qos), packet_id)
        suback += bytes(granted_qos)
        writer.write(suback)

        # Detect suspicious subscriptions
        severity = AttackSeverity.LOW
        category = AttackCategory.RECONNAISSANCE

        for topic in topics:
            if topic.startswith("$SYS") or topic.startswith("cmd/"):
                severity = AttackSeverity.HIGH
                category = AttackCategory.PLC_SCAN
            elif "#" in topic and topic != "#":
                severity = AttackSeverity.MEDIUM

        self._emit_event(
            source_ip=source_ip,
            session_id=session_id,
            event_type="mqtt_subscribe",
            command=f"SUBSCRIBE topics={','.join(topics)}",
            raw_data=f"client={client_id}",
            category=category,
            severity=severity,
            detected_patterns=["mqtt_subscription"],
        )

    # ---- Helpers ----

    def _emit_event(self, **kwargs) -> None:
        """Emit an attack event via the configured callback."""
        if not self._event_callback:
            return

        from ...models import AttackEvent

        event = AttackEvent(
            event_id=str(uuid.uuid4()),
            session_id=kwargs.get("session_id", ""),
            honeypot_id=(self.definition.id if self.definition else "mqtt-default"),
            protocol=HoneypotProtocol.MQTT,
            timestamp=datetime.now(timezone.utc),
            source_ip=kwargs.get("source_ip", "unknown"),
            source_port=kwargs.get("source_port", 0),
            event_type=kwargs.get("event_type", "mqtt_event"),
            command=kwargs.get("command"),
            raw_data=kwargs.get("raw_data", ""),
            category=kwargs.get("category", AttackCategory.RECONNAISSANCE),
            severity=kwargs.get("severity", AttackSeverity.LOW),
            detected_patterns=kwargs.get("detected_patterns", []),
        )

        try:
            self._event_callback(event)
        except Exception as e:
            logger.error(f"Failed to emit MQTT event: {e}")

    async def _apply_stealth_delay_async(self) -> None:
        """Apply realistic response delay."""
        delay_ms = getattr(self._config, "stealth_response_delay_ms", 50)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

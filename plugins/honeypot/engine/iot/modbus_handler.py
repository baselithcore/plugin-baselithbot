"""Modbus TCP Honeypot Handler.

Emulates a Modbus TCP slave device (PLC/RTU) for ICS/SCADA honeypotting.
Implements the Modbus Application Protocol (MBAP) over TCP with support
for common function codes used in industrial environments.

Supported Function Codes:
  1  - Read Coils
  2  - Read Discrete Inputs
  3  - Read Holding Registers
  4  - Read Input Registers
  5  - Write Single Coil
  6  - Write Single Register
  15 - Write Multiple Coils
  16 - Write Multiple Registers

Attack detection:
  - Unauthorized write attempts to critical registers
  - Full register scans (reconnaissance)
  - Unsupported function code probes
"""

import asyncio
from core.observability.logging import get_logger
import struct
from datetime import datetime, timezone
from typing import Dict, Optional

from ..base import BaseHandler
from ...models import AttackCategory, AttackSeverity, HoneypotProtocol

logger = get_logger(__name__)

# Modbus function code constants
FC_READ_COILS = 1
FC_READ_DISCRETE_INPUTS = 2
FC_READ_HOLDING_REGISTERS = 3
FC_READ_INPUT_REGISTERS = 4
FC_WRITE_SINGLE_COIL = 5
FC_WRITE_SINGLE_REGISTER = 6
FC_WRITE_MULTIPLE_COILS = 15
FC_WRITE_MULTIPLE_REGISTERS = 16

# Modbus exception codes
EX_ILLEGAL_FUNCTION = 0x01
EX_ILLEGAL_DATA_ADDRESS = 0x02
EX_ILLEGAL_DATA_VALUE = 0x03

# MBAP header size (Transaction ID: 2, Protocol ID: 2, Length: 2, Unit ID: 1)
MBAP_HEADER_SIZE = 7


class ModbusHandler(BaseHandler):
    """Modbus TCP honeypot handler.

    Emulates a Modbus TCP slave with configurable registers and coils.
    All interactions are logged as AttackEvents with protocol=MODBUS.
    """

    def __init__(self, config, definition=None):
        """Initialize Modbus handler.

        Args:
            config: HoneypotConfig instance.
            definition: HoneypotDefinition from YAML.
        """
        super().__init__(config, definition=definition)
        self._server: Optional[asyncio.AbstractServer] = None
        self._protocol = HoneypotProtocol.MODBUS

        # Load config from definition or use defaults
        modbus_config = None
        if definition:
            modbus_config = definition.get_protocol_config()

        self._unit_id = getattr(modbus_config, "unit_id", 1)
        self._supported_fcs = set(
            getattr(
                modbus_config, "supported_function_codes", [1, 2, 3, 4, 5, 6, 15, 16]
            )
        )
        self._device_id = getattr(
            modbus_config,
            "device_identification",
            "Siemens S7-1200 / Modbus TCP Gateway",
        )

        # Mutable register/coil state
        raw_regs = getattr(modbus_config, "holding_registers", {})
        self._holding_registers: Dict[int, int] = {
            int(k): int(v) for k, v in raw_regs.items()
        }
        raw_coils = getattr(modbus_config, "coils", {})
        self._coils: Dict[int, bool] = {int(k): bool(v) for k, v in raw_coils.items()}

    async def start(self, port: int = 502) -> None:
        """Start Modbus TCP server.

        Args:
            port: TCP port to listen on (default 502).
        """
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",  # nosec B104
            port,
        )
        self._running = True
        logger.info(f"Modbus TCP honeypot started on port {port}")

    async def stop(self) -> None:
        """Stop Modbus TCP server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("Modbus TCP honeypot stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming Modbus TCP connection."""
        peer = writer.get_extra_info("peername")
        source_ip = peer[0] if peer else "unknown"
        source_port = peer[1] if peer else 0
        session_id = self._generate_session_id()

        logger.info(f"Modbus connection from {source_ip}:{source_port}")

        try:
            while self._running:
                # Read MBAP header
                header_data = await asyncio.wait_for(
                    reader.read(MBAP_HEADER_SIZE), timeout=30.0
                )
                if not header_data or len(header_data) < MBAP_HEADER_SIZE:
                    break

                transaction_id, protocol_id, length, unit_id = struct.unpack(
                    ">HHHB", header_data
                )

                # Validate protocol ID (must be 0 for Modbus)
                if protocol_id != 0:
                    break

                # Read PDU (length - 1 for unit_id already consumed)
                pdu_length = length - 1
                if pdu_length <= 0 or pdu_length > 253:
                    break

                pdu_data = await asyncio.wait_for(reader.read(pdu_length), timeout=10.0)
                if not pdu_data or len(pdu_data) < pdu_length:
                    break

                function_code = pdu_data[0]

                # Apply stealth delay
                await self._apply_stealth_delay_async()

                # Process function code
                response_pdu = self._process_pdu(
                    function_code, pdu_data[1:], source_ip, session_id
                )

                # Build MBAP response
                resp_length = len(response_pdu) + 1  # +1 for unit_id
                response = (
                    struct.pack(">HHHB", transaction_id, 0, resp_length, unit_id)
                    + response_pdu
                )

                writer.write(response)
                await writer.drain()

        except asyncio.TimeoutError:
            pass
        except ConnectionResetError:
            pass
        except Exception as e:
            logger.debug(f"Modbus connection error from {source_ip}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _process_pdu(
        self,
        function_code: int,
        data: bytes,
        source_ip: str,
        session_id: str,
    ) -> bytes:
        """Process a Modbus PDU and return response PDU.

        Args:
            function_code: Modbus function code.
            data: PDU data (after function code).
            source_ip: Source IP address.
            session_id: Session identifier.

        Returns:
            Response PDU bytes.
        """
        # Emit event for all requests
        is_write = function_code in (
            FC_WRITE_SINGLE_COIL,
            FC_WRITE_SINGLE_REGISTER,
            FC_WRITE_MULTIPLE_COILS,
            FC_WRITE_MULTIPLE_REGISTERS,
        )

        category = (
            AttackCategory.SCADA_MANIPULATION if is_write else AttackCategory.PLC_SCAN
        )
        severity = AttackSeverity.HIGH if is_write else AttackSeverity.MEDIUM

        self._emit_event(
            source_ip=source_ip,
            source_port=0,
            session_id=session_id,
            event_type="modbus_request",
            command=f"FC{function_code}",
            raw_data=data.hex(),
            category=category,
            severity=severity,
            detected_patterns=[f"modbus_fc{function_code}"],
        )

        # Check if function code is supported
        if function_code not in self._supported_fcs:
            return self._exception_response(function_code, EX_ILLEGAL_FUNCTION)

        # Dispatch to handler
        if function_code == FC_READ_COILS:
            return self._read_coils(function_code, data)
        elif function_code == FC_READ_DISCRETE_INPUTS:
            return self._read_discrete_inputs(function_code, data)
        elif function_code == FC_READ_HOLDING_REGISTERS:
            return self._read_holding_registers(function_code, data)
        elif function_code == FC_READ_INPUT_REGISTERS:
            return self._read_input_registers(function_code, data)
        elif function_code == FC_WRITE_SINGLE_COIL:
            return self._write_single_coil(function_code, data, source_ip, session_id)
        elif function_code == FC_WRITE_SINGLE_REGISTER:
            return self._write_single_register(
                function_code, data, source_ip, session_id
            )
        elif function_code == FC_WRITE_MULTIPLE_COILS:
            return self._write_multiple_coils(
                function_code, data, source_ip, session_id
            )
        elif function_code == FC_WRITE_MULTIPLE_REGISTERS:
            return self._write_multiple_registers(
                function_code, data, source_ip, session_id
            )
        else:
            return self._exception_response(function_code, EX_ILLEGAL_FUNCTION)

    # ---- Read operations ----

    def _read_coils(self, fc: int, data: bytes) -> bytes:
        """FC1: Read coils."""
        if len(data) < 4:
            return self._exception_response(fc, EX_ILLEGAL_DATA_VALUE)

        start_addr, quantity = struct.unpack(">HH", data[:4])
        byte_count = (quantity + 7) // 8
        coil_bytes = bytearray(byte_count)

        for i in range(quantity):
            addr = start_addr + i
            if self._coils.get(addr, False):
                coil_bytes[i // 8] |= 1 << (i % 8)

        return struct.pack("BB", fc, byte_count) + bytes(coil_bytes)

    def _read_discrete_inputs(self, fc: int, data: bytes) -> bytes:
        """FC2: Read discrete inputs (mirrors coils for honeypot)."""
        return self._read_coils(fc, data)

    def _read_holding_registers(self, fc: int, data: bytes) -> bytes:
        """FC3: Read holding registers."""
        if len(data) < 4:
            return self._exception_response(fc, EX_ILLEGAL_DATA_VALUE)

        start_addr, quantity = struct.unpack(">HH", data[:4])
        byte_count = quantity * 2
        reg_bytes = bytearray()

        for i in range(quantity):
            addr = start_addr + i
            value = self._holding_registers.get(addr, 0)
            reg_bytes.extend(struct.pack(">H", value & 0xFFFF))

        return struct.pack("BB", fc, byte_count) + bytes(reg_bytes)

    def _read_input_registers(self, fc: int, data: bytes) -> bytes:
        """FC4: Read input registers (mirrors holding regs for honeypot)."""
        return self._read_holding_registers(fc, data)

    # ---- Write operations ----

    def _write_single_coil(
        self, fc: int, data: bytes, source_ip: str, session_id: str
    ) -> bytes:
        """FC5: Write single coil."""
        if len(data) < 4:
            return self._exception_response(fc, EX_ILLEGAL_DATA_VALUE)

        addr, value = struct.unpack(">HH", data[:4])
        self._coils[addr] = value == 0xFF00

        logger.warning(
            f"Modbus WRITE COIL from {source_ip}: "
            f"addr={addr} value={'ON' if value == 0xFF00 else 'OFF'}"
        )
        return struct.pack(">BHH", fc, addr, value)

    def _write_single_register(
        self, fc: int, data: bytes, source_ip: str, session_id: str
    ) -> bytes:
        """FC6: Write single register."""
        if len(data) < 4:
            return self._exception_response(fc, EX_ILLEGAL_DATA_VALUE)

        addr, value = struct.unpack(">HH", data[:4])
        self._holding_registers[addr] = value

        logger.warning(
            f"Modbus WRITE REGISTER from {source_ip}: addr={addr} value={value}"
        )
        return struct.pack(">BHH", fc, addr, value)

    def _write_multiple_coils(
        self, fc: int, data: bytes, source_ip: str, session_id: str
    ) -> bytes:
        """FC15: Write multiple coils."""
        if len(data) < 5:
            return self._exception_response(fc, EX_ILLEGAL_DATA_VALUE)

        start_addr, quantity = struct.unpack(">HH", data[:4])
        byte_count = data[4]
        coil_data = data[5 : 5 + byte_count]

        for i in range(quantity):
            if i // 8 < len(coil_data):
                self._coils[start_addr + i] = bool(coil_data[i // 8] & (1 << (i % 8)))

        logger.warning(
            f"Modbus WRITE MULTIPLE COILS from {source_ip}: "
            f"start={start_addr} qty={quantity}"
        )
        return struct.pack(">BHH", fc, start_addr, quantity)

    def _write_multiple_registers(
        self, fc: int, data: bytes, source_ip: str, session_id: str
    ) -> bytes:
        """FC16: Write multiple registers."""
        if len(data) < 5:
            return self._exception_response(fc, EX_ILLEGAL_DATA_VALUE)

        start_addr, quantity = struct.unpack(">HH", data[:4])
        byte_count = data[4]
        reg_data = data[5 : 5 + byte_count]

        for i in range(quantity):
            offset = i * 2
            if offset + 2 <= len(reg_data):
                value = struct.unpack(">H", reg_data[offset : offset + 2])[0]
                self._holding_registers[start_addr + i] = value

        logger.warning(
            f"Modbus WRITE MULTIPLE REGISTERS from {source_ip}: "
            f"start={start_addr} qty={quantity}"
        )
        return struct.pack(">BHH", fc, start_addr, quantity)

    # ---- Helpers ----

    @staticmethod
    def _exception_response(function_code: int, exception_code: int) -> bytes:
        """Build Modbus exception response.

        Args:
            function_code: Original function code.
            exception_code: Exception code (1-3).

        Returns:
            Exception response PDU.
        """
        return struct.pack("BB", function_code | 0x80, exception_code)

    def _emit_event(self, **kwargs) -> None:
        """Emit an attack event via the configured callback."""
        if not self._event_callback:
            return

        from ...models import AttackEvent
        import uuid

        event = AttackEvent(
            event_id=str(uuid.uuid4()),
            session_id=kwargs.get("session_id", ""),
            honeypot_id=self.definition.id if self.definition else "modbus-default",
            protocol=HoneypotProtocol.MODBUS,
            timestamp=datetime.now(timezone.utc),
            source_ip=kwargs.get("source_ip", "unknown"),
            source_port=kwargs.get("source_port", 0),
            event_type=kwargs.get("event_type", "modbus_request"),
            command=kwargs.get("command"),
            raw_data=kwargs.get("raw_data", ""),
            category=kwargs.get("category", AttackCategory.PLC_SCAN),
            severity=kwargs.get("severity", AttackSeverity.MEDIUM),
            detected_patterns=kwargs.get("detected_patterns", []),
        )

        try:
            self._event_callback(event)
        except Exception as e:
            logger.error(f"Failed to emit Modbus event: {e}")

    async def _apply_stealth_delay_async(self) -> None:
        """Apply realistic response delay asynchronously."""
        delay_ms = getattr(self._config, "stealth_response_delay_ms", 50)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

    @staticmethod
    def _generate_session_id() -> str:
        """Generate a unique session ID."""
        import uuid

        return f"modbus-{uuid.uuid4().hex[:12]}"

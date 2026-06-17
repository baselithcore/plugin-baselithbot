"""S7ProtocolMixin — protocol-level S7comm/COTP methods."""

import struct
from typing import Optional

from ._constants import (
    COTP_CC,
    COTP_DT,
    S7_ACK_DATA,
    S7_AREA_DB,
    S7_FUNC_READ_VAR,
    S7_FUNC_SETUP_COMM,
    S7_FUNC_WRITE_VAR,
    S7_JOB,
    S7_PROTOCOL_ID,
    TPKT_HEADER_SIZE,
    TPKT_VERSION,
)
from ....models import AttackCategory, AttackSeverity


class S7ProtocolMixin:
    """Mixin providing S7comm/COTP protocol handler methods."""

    def _handle_cotp_cr(
        self,
        payload: bytes,
        source_ip: str,
        session_id: str,
    ) -> bytes:
        """Handle COTP Connection Request, return Connection Confirm.

        Args:
            payload: Full COTP payload.
            source_ip: Attacker IP.
            session_id: Session identifier.

        Returns:
            TPKT + COTP CC response bytes.
        """
        self._emit_event(
            source_ip=source_ip,
            session_id=session_id,
            event_type="s7_cotp_connect",
            command="COTP_CR",
            category=AttackCategory.PLC_SCAN,
            severity=AttackSeverity.LOW,
        )

        # Build COTP CC response
        # COTP CC: length=6, PDU type=0xD0, dst_ref, src_ref, class
        cotp_cc = bytes(
            [
                0x06,  # COTP header length
                COTP_CC,  # PDU type
                0x00,
                0x01,  # Destination reference
                0x00,
                0x01,  # Source reference
                0x00,  # Class / options
            ]
        )

        # Wrap in TPKT
        total = TPKT_HEADER_SIZE + len(cotp_cc)
        tpkt = struct.pack(">BBH", TPKT_VERSION, 0, total)
        return tpkt + cotp_cc

    def _handle_s7_data(
        self,
        s7_data: bytes,
        source_ip: str,
        session_id: str,
    ) -> Optional[bytes]:
        """Handle S7comm PDU inside COTP DT.

        Args:
            s7_data: S7comm payload bytes (after COTP header).
            source_ip: Attacker IP.
            session_id: Session identifier.

        Returns:
            Full TPKT+COTP+S7 response or None.
        """
        if len(s7_data) < 10:
            return None

        protocol_id = s7_data[0]
        if protocol_id != S7_PROTOCOL_ID:
            return None

        msg_type = s7_data[1]
        seq_number = struct.unpack(">H", s7_data[4:6])[0]
        param_length = struct.unpack(">H", s7_data[6:8])[0]
        data_length = struct.unpack(">H", s7_data[8:10])[0]

        params = s7_data[10 : 10 + param_length]
        data = s7_data[10 + param_length : 10 + param_length + data_length]

        if msg_type != S7_JOB or not params:
            return None

        function_code = params[0]

        if function_code == S7_FUNC_SETUP_COMM:
            return self._handle_setup_comm(seq_number, params, source_ip, session_id)
        elif function_code == S7_FUNC_READ_VAR:
            return self._handle_read_var(seq_number, params, source_ip, session_id)
        elif function_code == S7_FUNC_WRITE_VAR:
            return self._handle_write_var(
                seq_number, params, data, source_ip, session_id
            )
        else:
            # SZL or unknown — treat as CPU info request
            return self._handle_szl_request(seq_number, params, source_ip, session_id)

    def _handle_setup_comm(
        self,
        seq_number: int,
        params: bytes,
        source_ip: str,
        session_id: str,
    ) -> bytes:
        """Handle S7 Setup Communication request."""
        self._emit_event(
            source_ip=source_ip,
            session_id=session_id,
            event_type="s7_setup_comm",
            command="SETUP_COMMUNICATION",
            category=AttackCategory.PLC_SCAN,
            severity=AttackSeverity.MEDIUM,
        )

        # S7 Setup Communication response
        s7_params = bytes(
            [
                S7_FUNC_SETUP_COMM,
                0x00,  # reserved
                0x00,
                0x01,  # max AMQcalling
                0x00,
                0x01,  # max AMQcalled
                0x01,
                0xE0,  # PDU length (480)
            ]
        )

        return self._build_s7_response(seq_number, s7_params, b"")

    def _handle_read_var(
        self,
        seq_number: int,
        params: bytes,
        source_ip: str,
        session_id: str,
    ) -> bytes:
        """Handle S7 Read Variable request."""
        # Parse item specifications
        items_data = b""

        if len(params) >= 2:
            item_count = params[1]
        else:
            item_count = 0

        offset = 2
        for _ in range(item_count):
            if offset + 12 > len(params):
                break

            # Parse read item specification (12 bytes each)
            _spec_type = params[offset]  # noqa: F841
            _spec_length = params[offset + 1]  # noqa: F841
            _syntax_id = params[offset + 2]  # noqa: F841
            _transport_size = params[offset + 3]  # noqa: F841
            length = struct.unpack(">H", params[offset + 4 : offset + 6])[0]
            db_number = struct.unpack(">H", params[offset + 6 : offset + 8])[0]
            area = params[offset + 8]
            address_bytes = params[offset + 9 : offset + 12]
            byte_offset = (
                address_bytes[0] << 16 | address_bytes[1] << 8 | address_bytes[2]
            ) >> 3

            offset += 12

            self._emit_event(
                source_ip=source_ip,
                session_id=session_id,
                event_type="s7_read_var",
                command=f"READ area=0x{area:02X} db={db_number} offset={byte_offset} len={length}",
                category=AttackCategory.PLC_SCAN,
                severity=AttackSeverity.MEDIUM,
                detected_patterns=["s7_memory_read"],
            )

            # Build read response data
            if area == S7_AREA_DB and db_number in self._db_memory:
                db = self._db_memory[db_number]
                end = min(byte_offset + length, len(db))
                read_data = bytes(db[byte_offset:end])
                # Success: return_code=0xFF, transport_size=4 (byte), length
                data_len_bits = len(read_data) * 8
                items_data += struct.pack(">BBH", 0xFF, 0x04, data_len_bits) + read_data
                # Pad to even
                if len(read_data) % 2 != 0:
                    items_data += b"\x00"
            else:
                # Error: item not available (0x0A)
                items_data += struct.pack(">BBH", 0x0A, 0x00, 0x0000)

        # Read var response parameters
        s7_params = bytes([S7_FUNC_READ_VAR, item_count])

        return self._build_s7_response(seq_number, s7_params, items_data)

    def _handle_write_var(
        self,
        seq_number: int,
        params: bytes,
        data: bytes,
        source_ip: str,
        session_id: str,
    ) -> bytes:
        """Handle S7 Write Variable request (critical attack indicator)."""
        from core.observability.logging import get_logger

        _logger = get_logger(__name__)

        item_count = params[1] if len(params) >= 2 else 0

        self._emit_event(
            source_ip=source_ip,
            session_id=session_id,
            event_type="s7_write_var",
            command=f"WRITE items={item_count}",
            raw_data=data.hex()[:200],
            category=AttackCategory.SCADA_MANIPULATION,
            severity=AttackSeverity.CRITICAL,
            detected_patterns=["s7_memory_write", "plc_manipulation"],
        )

        _logger.warning(
            f"S7comm WRITE from {source_ip}: {item_count} items — "
            f"potential PLC manipulation!"
        )

        # Accept writes to honeypot memory
        offset = 2
        for i in range(item_count):
            if offset + 12 > len(params):
                break
            area = params[offset + 8]
            db_number = struct.unpack(">H", params[offset + 6 : offset + 8])[0]
            address_bytes = params[offset + 9 : offset + 12]
            byte_offset = (
                address_bytes[0] << 16 | address_bytes[1] << 8 | address_bytes[2]
            ) >> 3
            length = struct.unpack(">H", params[offset + 4 : offset + 6])[0]
            offset += 12

            # Write data into honeypot DB memory
            if area == S7_AREA_DB and db_number in self._db_memory:
                db = self._db_memory[db_number]
                # Find write data from the data portion
                # (simplified — real protocol has per-item headers in data)
                for j in range(min(length, len(data))):
                    target = byte_offset + j
                    if target < len(db) and j < len(data):
                        db[target] = data[j]

        # Response: all items written OK
        result_data = bytes([0xFF]) * item_count
        s7_params = bytes([S7_FUNC_WRITE_VAR, item_count])

        return self._build_s7_response(seq_number, s7_params, result_data)

    def _handle_szl_request(
        self,
        seq_number: int,
        params: bytes,
        source_ip: str,
        session_id: str,
    ) -> bytes:
        """Handle SZL (System Status List) / CPU info query.

        Returns fake Siemens PLC identification that matches configured
        CPU type and order code.
        """
        from core.observability.logging import get_logger

        _logger = get_logger(__name__)

        self._emit_event(
            source_ip=source_ip,
            session_id=session_id,
            event_type="s7_szl_query",
            command="SZL_READ (CPU identification)",
            category=AttackCategory.PLC_SCAN,
            severity=AttackSeverity.HIGH,
            detected_patterns=["s7_cpu_info", "plc_reconnaissance"],
        )

        _logger.info(f"S7comm SZL query from {source_ip} — returning fake PLC ID")

        # Build a minimal SZL response with CPU identification
        order_code_bytes = self._order_code.encode("ascii")[:20].ljust(20, b"\x00")
        serial_bytes = self._serial_number.encode("ascii")[:20].ljust(20, b"\x00")
        module_bytes = self._module_info.encode("ascii")[:24].ljust(24, b"\x00")
        cpu_type_bytes = self._cpu_type.encode("ascii")[:32].ljust(32, b"\x00")

        szl_data = order_code_bytes + serial_bytes + module_bytes + cpu_type_bytes

        # Fake userdata response header
        s7_params = bytes(
            [
                0x00,  # function group = CPU services
                0x08,  # subfunction = SZL
                0x12,  # sequence (arbitrary)
                0x04,  # data unit reference
                0x11,  # last data unit = yes
                0x00,  # error code
            ]
        )

        return self._build_s7_response(seq_number, s7_params, szl_data)

    def _build_s7_response(
        self,
        seq_number: int,
        s7_params: bytes,
        s7_data: bytes,
    ) -> bytes:
        """Build complete TPKT + COTP DT + S7 ACK_DATA response.

        Args:
            seq_number: Sequence number from request.
            s7_params: S7 parameter bytes.
            s7_data: S7 data bytes.

        Returns:
            Complete wire-format response.
        """
        # S7comm header (10 bytes for ACK_DATA)
        param_len = len(s7_params)
        data_len = len(s7_data)

        s7_header = struct.pack(
            ">BBHHHHH",
            S7_PROTOCOL_ID,  # Protocol ID
            S7_ACK_DATA,  # Message type
            0x0000,  # Reserved
            seq_number,  # Sequence number
            param_len,  # Parameter length
            data_len,  # Data length
            0x0000,  # Error class + code (no error)
        )

        # COTP DT header (3 bytes)
        cotp_dt = bytes([0x02, COTP_DT, 0x80])  # length, type, TPDU number (EOT)

        # Full payload
        payload = cotp_dt + s7_header + s7_params + s7_data

        # TPKT wrapper
        total = TPKT_HEADER_SIZE + len(payload)
        tpkt = struct.pack(">BBH", TPKT_VERSION, 0, total)

        return tpkt + payload

"""Tests for IoT/OT Honeypot Handlers.

Covers Modbus TCP, MQTT, and S7comm protocol handlers with
protocol-level unit tests using direct method invocation.
"""

import struct
import pytest
from unittest.mock import MagicMock

from plugins.honeypot.engine.iot.modbus_handler import (
    ModbusHandler,
    FC_READ_COILS,
    FC_READ_HOLDING_REGISTERS,
    FC_WRITE_SINGLE_COIL,
    FC_WRITE_SINGLE_REGISTER,
    FC_WRITE_MULTIPLE_REGISTERS,
    EX_ILLEGAL_FUNCTION,
    EX_ILLEGAL_DATA_VALUE,
)
from plugins.honeypot.engine.iot.mqtt_handler import (
    MQTTHandler,
    _decode_remaining_length,
    _decode_utf8_string,
)
from plugins.honeypot.engine.iot.s7comm_handler import (
    S7CommHandler,
    S7_PROTOCOL_ID,
    S7_FUNC_SETUP_COMM,
    S7_FUNC_READ_VAR,
    S7_FUNC_WRITE_VAR,
)
from plugins.honeypot.models import HoneypotProtocol, AttackCategory


# =========================================================================
# Modbus Handler Tests
# =========================================================================


class TestModbusHandler:
    """Tests for Modbus TCP handler."""

    @pytest.fixture
    def handler(self):
        """Create Modbus handler with test config."""
        config = MagicMock()
        config.stealth_response_delay_ms = 0
        h = ModbusHandler(config)
        h._holding_registers = {0: 100, 1: 200, 2: 300}
        h._coils = {0: True, 1: False, 2: True}
        h._event_callback = MagicMock()
        return h

    def test_read_holding_registers(self, handler):
        """Test FC3: Read Holding Registers."""
        # Read 2 registers starting at address 0
        data = struct.pack(">HH", 0, 2)
        response = handler._read_holding_registers(FC_READ_HOLDING_REGISTERS, data)

        assert response[0] == FC_READ_HOLDING_REGISTERS
        assert response[1] == 4  # byte count = 2 registers * 2 bytes
        reg0 = struct.unpack(">H", response[2:4])[0]
        reg1 = struct.unpack(">H", response[4:6])[0]
        assert reg0 == 100
        assert reg1 == 200

    def test_read_coils(self, handler):
        """Test FC1: Read Coils."""
        # Read 3 coils starting at address 0
        data = struct.pack(">HH", 0, 3)
        response = handler._read_coils(FC_READ_COILS, data)

        assert response[0] == FC_READ_COILS
        assert response[1] == 1  # byte count
        # Coils: addr0=True, addr1=False, addr2=True → bits = 0b101 = 5
        assert response[2] == 5

    def test_write_single_register(self, handler):
        """Test FC6: Write Single Register."""
        data = struct.pack(">HH", 10, 999)
        response = handler._write_single_register(
            FC_WRITE_SINGLE_REGISTER, data, "1.2.3.4", "test-session"
        )

        # Echo back request
        assert response[0] == FC_WRITE_SINGLE_REGISTER
        # Verify register updated
        assert handler._holding_registers[10] == 999

    def test_write_single_coil(self, handler):
        """Test FC5: Write Single Coil (ON)."""
        data = struct.pack(">HH", 5, 0xFF00)  # ON value
        handler._write_single_coil(
            FC_WRITE_SINGLE_COIL, data, "1.2.3.4", "test-session"
        )

        assert handler._coils[5] is True

    def test_exception_for_unsupported_fc(self, handler):
        """Test exception response for unsupported function code."""
        handler._supported_fcs = {1, 3}
        response = handler._process_pdu(
            99, b"\x00\x00\x00\x00", "1.2.3.4", "test-session"
        )

        assert response[0] == (99 | 0x80)
        assert response[1] == EX_ILLEGAL_FUNCTION

    def test_exception_for_short_data(self, handler):
        """Test exception on data too short for register read."""
        response = handler._read_holding_registers(FC_READ_HOLDING_REGISTERS, b"\x00")

        assert response[0] == (FC_READ_HOLDING_REGISTERS | 0x80)
        assert response[1] == EX_ILLEGAL_DATA_VALUE

    def test_write_multiple_registers(self, handler):
        """Test FC16: Write Multiple Registers."""
        start, qty = 0, 2
        reg_data = struct.pack(">HH", 750, 850)
        data = struct.pack(">HHB", start, qty, len(reg_data)) + reg_data

        handler._write_multiple_registers(
            FC_WRITE_MULTIPLE_REGISTERS, data, "1.2.3.4", "test-session"
        )

        assert handler._holding_registers[0] == 750
        assert handler._holding_registers[1] == 850

    def test_event_emission_on_pdu(self, handler):
        """Verify events are emitted for each PDU processed."""
        data = struct.pack(">HH", 0, 1)
        handler._process_pdu(FC_READ_HOLDING_REGISTERS, data, "1.2.3.4", "test-session")

        assert handler._event_callback.called


# =========================================================================
# MQTT Handler Tests
# =========================================================================


class TestMQTTHandler:
    """Tests for MQTT broker handler."""

    def test_decode_remaining_length_single_byte(self):
        """Test variable-length decoding with single byte."""
        data = bytes([0x42])
        length, consumed = _decode_remaining_length(data, 0)
        assert length == 0x42
        assert consumed == 1

    def test_decode_remaining_length_multi_byte(self):
        """Test variable-length decoding with continuation bytes."""
        # 128 = 0x80 0x01 in MQTT encoding
        data = bytes([0x80, 0x01])
        length, consumed = _decode_remaining_length(data, 0)
        assert length == 128
        assert consumed == 2

    def test_decode_utf8_string(self):
        """Test MQTT UTF-8 prefixed string decoding."""
        test_str = "hello"
        data = struct.pack(">H", len(test_str)) + test_str.encode("utf-8")
        result, consumed = _decode_utf8_string(data, 0)
        assert result == "hello"
        assert consumed == 7  # 2 (length prefix) + 5 (string)

    def test_decode_utf8_string_empty(self):
        """Test decoding with insufficient data."""
        result, consumed = _decode_utf8_string(b"\x00", 0)
        assert result == ""
        assert consumed == 0

    @pytest.fixture
    def mqtt_handler(self):
        """Create MQTT handler with test config."""
        config = MagicMock()
        config.stealth_response_delay_ms = 0
        h = MQTTHandler(config)
        h._event_callback = MagicMock()
        return h

    def test_handler_protocol(self, mqtt_handler):
        """Verify handler protocol is MQTT."""
        assert mqtt_handler._protocol == HoneypotProtocol.MQTT

    def test_handler_default_config(self, mqtt_handler):
        """Verify default configuration is loaded."""
        assert mqtt_handler._allow_anonymous is True
        assert mqtt_handler._max_qos == 2


# =========================================================================
# S7comm Handler Tests
# =========================================================================


class TestS7CommHandler:
    """Tests for S7comm/COTP handler."""

    @pytest.fixture
    def handler(self):
        """Create S7comm handler with test config."""
        config = MagicMock()
        config.stealth_response_delay_ms = 0
        h = S7CommHandler(config)
        h._db_memory = {1: bytearray(256), 2: bytearray(128)}
        h._db_memory[1][0:4] = b"\xde\xad\xbe\xef"
        h._event_callback = MagicMock()
        return h

    def test_cotp_cr_response(self, handler):
        """Test COTP Connection Request returns valid CC."""
        # Minimal COTP CR payload
        payload = bytes(
            [
                0x06,
                0xE0,  # length=6, PDU type=CR
                0x00,
                0x00,  # dst reference
                0x00,
                0x01,  # src reference
                0x00,  # class
            ]
        )

        response = handler._handle_cotp_cr(payload, "1.2.3.4", "test-session")

        # Check TPKT header
        assert response[0] == 3  # TPKT version
        # Check COTP CC PDU type
        assert (response[5] & 0xF0) == 0xD0  # CC type

    def test_setup_comm_response(self, handler):
        """Test S7 Setup Communication response."""
        s7_params = bytes(
            [
                S7_FUNC_SETUP_COMM,
                0x00,  # reserved
                0x00,
                0x01,  # max AMQ calling
                0x00,
                0x01,  # max AMQ called
                0x03,
                0xC0,  # PDU length
            ]
        )

        response = handler._handle_setup_comm(
            seq_number=1,
            params=s7_params,
            source_ip="1.2.3.4",
            session_id="test",
        )

        # TPKT(4) + COTP DT(3) + S7 header(12+) + params
        assert len(response) > 12
        # Check S7 protocol ID
        s7_start = 7  # TPKT(4) + COTP DT(3)
        assert response[s7_start] == S7_PROTOCOL_ID

    def test_read_var_from_db1(self, handler):
        """Test reading data from DB1 returns expected bytes."""
        # Build read var request parameters
        # FC=4 (read var), item_count=1
        # Item: spec_type=0x12, length=10, syntax_id=0x10, transport_size=4
        #        quantity=4, db_number=1, area=0x84, address=0
        item = bytes(
            [
                0x12,  # Specification type
                0x0A,  # Length of this item
                0x10,  # Syntax ID
                0x02,  # Transport size (byte)
                0x00,
                0x04,  # Length = 4 bytes
                0x00,
                0x01,  # DB number = 1
                0x84,  # Area = DB
                0x00,
                0x00,
                0x00,  # Address = byte 0, bit 0
            ]
        )

        params = bytes([S7_FUNC_READ_VAR, 0x01]) + item

        response = handler._handle_read_var(
            seq_number=1,
            params=params,
            source_ip="1.2.3.4",
            session_id="test",
        )

        # Response should contain our 0xDEADBEEF data
        assert b"\xde\xad\xbe\xef" in response

    def test_write_var_emits_critical_event(self, handler):
        """Test write var emits critical severity event."""
        params = bytes([S7_FUNC_WRITE_VAR, 0x01]) + bytes(12)
        data = b"\x00\x01\x02\x03"

        handler._handle_write_var(
            seq_number=1,
            params=params,
            data=data,
            source_ip="10.0.0.1",
            session_id="test",
        )

        handler._event_callback.assert_called_once()
        emitted_event = handler._event_callback.call_args[0][0]
        assert emitted_event.category == AttackCategory.SCADA_MANIPULATION

    def test_szl_response_contains_cpu_info(self, handler):
        """Test SZL response contains configured CPU type."""
        response = handler._handle_szl_request(
            seq_number=1,
            params=b"\x00",
            source_ip="1.2.3.4",
            session_id="test",
        )

        # CPU type should be in the response
        assert handler._cpu_type.encode("ascii")[:20] in response

    def test_handler_protocol(self, handler):
        """Verify handler protocol is S7COMM."""
        assert handler._protocol == HoneypotProtocol.S7COMM

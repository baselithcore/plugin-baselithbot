"""ICS/IoT honeypot configuration models."""

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ModbusHoneypotConfig(BaseModel):
    """Modbus TCP honeypot configuration for ICS/SCADA emulation."""

    unit_id: int = Field(
        default=1,
        description="Modbus unit/slave ID",
    )
    supported_function_codes: List[int] = Field(
        default_factory=lambda: [1, 2, 3, 4, 5, 6, 15, 16],
        description="Supported Modbus function codes",
    )
    holding_registers: Dict[int, int] = Field(
        default_factory=lambda: {
            0: 0,
            1: 100,
            2: 250,
            3: 0,
            4: 1,
            100: 2400,
            101: 500,
            102: 60,
        },
        description="Register address to value map (simulated PLC state)",
    )
    coils: Dict[int, bool] = Field(
        default_factory=lambda: {0: True, 1: False, 2: True, 3: True},
        description="Coil address to state map",
    )
    device_identification: str = Field(
        default="Siemens S7-1200 / Modbus TCP Gateway",
        description="Device identification string for Modbus device ID",
    )

    model_config = ConfigDict(extra="ignore")


class MQTTHoneypotConfig(BaseModel):
    """MQTT broker honeypot configuration for IoT emulation."""

    allow_anonymous: bool = Field(
        default=True,
        description="Allow connections without credentials",
    )
    valid_credentials: List[Dict[str, str]] = Field(
        default_factory=lambda: [
            {"username": "admin", "password": "admin"},
            {"username": "device", "password": "device123"},
        ],
        description="Credentials that allow successful authentication",
    )
    monitored_topics: List[str] = Field(
        default_factory=lambda: [
            "factory/#",
            "plc/#",
            "sensor/#",
            "actuator/#",
            "$SYS/#",
            "cmd/#",
            "firmware/#",
        ],
        description="MQTT topic patterns to monitor for ICS activity",
    )
    max_qos: int = Field(
        default=2,
        description="Maximum QoS level supported (0, 1, or 2)",
        ge=0,
        le=2,
    )
    broker_name: str = Field(
        default="Eclipse Mosquitto/2.0.18",
        description="Broker identification string",
    )

    model_config = ConfigDict(extra="ignore")


class S7CommHoneypotConfig(BaseModel):
    """S7comm/COTP PLC honeypot configuration for Siemens PLC emulation."""

    rack: int = Field(
        default=0,
        description="PLC rack number",
    )
    slot: int = Field(
        default=2,
        description="PLC slot number",
    )
    cpu_type: str = Field(
        default="CPU 315-2 PN/DP",
        description="Siemens CPU type identifier",
    )
    order_code: str = Field(
        default="6ES7 315-2EH14-0AB0",
        description="Siemens order code for SZL identification",
    )
    serial_number: str = Field(
        default="S C-HONYPOT0001",
        description="PLC serial number",
    )
    db_blocks: Dict[int, Dict[str, int]] = Field(
        default_factory=lambda: {
            1: {"size": 256, "fill": 0},
            2: {"size": 128, "fill": 0},
        },
        description="DB block number to configuration map (size in bytes, fill value)",
    )
    module_info: str = Field(
        default="S7-300",
        description="Module identification string for SZL list",
    )

    model_config = ConfigDict(extra="ignore")

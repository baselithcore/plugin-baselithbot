"""IoT/OT Honeypot Handler Package.

Provides protocol handlers for industrial control systems:
- Modbus TCP (ICS/SCADA)
- MQTT (IoT broker)
- S7comm (Siemens PLCs)
"""

from typing import Optional, TYPE_CHECKING

from ..base import BaseHandler

if TYPE_CHECKING:
    from ...honeypot_definition import HoneypotDefinition

_HANDLER_MAP = {
    "modbus": "plugins.honeypot.engine.iot.modbus_handler.ModbusHandler",
    "mqtt": "plugins.honeypot.engine.iot.mqtt_handler.MQTTHandler",
    "s7comm": "plugins.honeypot.engine.iot.s7comm_handler.S7CommHandler",
}


def get_iot_handler(
    protocol: str,
    config,
    definition: "HoneypotDefinition",
) -> Optional[BaseHandler]:
    """Factory function to instantiate the correct IoT handler.

    Args:
        protocol: Protocol name (modbus, mqtt, s7comm).
        config: HoneypotConfig instance.
        definition: HoneypotDefinition from YAML.

    Returns:
        Instantiated handler or None if protocol is not supported.
    """
    import importlib

    class_path = _HANDLER_MAP.get(protocol)
    if not class_path:
        return None

    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    handler_class = getattr(module, class_name)
    return handler_class(config, definition=definition)


__all__ = ["get_iot_handler"]

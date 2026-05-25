# IoT/OT Honeypots — Baselith Honeypot Plugin

Industrial Control System (ICS) and Internet of Things (IoT) honeypot support for the Baselith Honeypot Plugin.

## Overview

The Honeypot Plugin extends beyond traditional IT protocols (SSH, HTTP, TCP) to emulate **industrial and IoT systems**. These honeypots are purpose-built to attract and detect attacks targeting operational technology (OT) environments, including SCADA systems, PLCs, and IoT device networks.

## Supported Protocols

| Protocol       | Handler         | Default Port | Emulates                               |
| -------------- | --------------- | :----------: | -------------------------------------- |
| **Modbus TCP** | `ModbusHandler` |     502      | ICS/SCADA PLC with registers and coils |
| **MQTT**       | `MQTTHandler`   |     1883     | IoT message broker (Mosquitto-like)    |
| **S7comm**     | `S7CommHandler` |     102      | Siemens S7-300/400 PLC (ISO-on-TCP)    |

---

## Modbus TCP Honeypot

### Description

Emulates a Modbus TCP slave device (PLC/RTU). The handler processes the complete MBAP (Modbus Application Protocol) header and supports the most common function codes used in industrial environments.

### Supported Function Codes

| FC  | Name                     | Detection                   |
| --- | ------------------------ | --------------------------- |
| 1   | Read Coils               | `PLC_SCAN` (Medium)         |
| 2   | Read Discrete Inputs     | `PLC_SCAN` (Medium)         |
| 3   | Read Holding Registers   | `PLC_SCAN` (Medium)         |
| 4   | Read Input Registers     | `PLC_SCAN` (Medium)         |
| 5   | Write Single Coil        | `SCADA_MANIPULATION` (High) |
| 6   | Write Single Register    | `SCADA_MANIPULATION` (High) |
| 15  | Write Multiple Coils     | `SCADA_MANIPULATION` (High) |
| 16  | Write Multiple Registers | `SCADA_MANIPULATION` (High) |

### Configuration (`modbus_config`)

```yaml
modbus_config:
  unit_id: 1
  device_identification: "Siemens S7-1200 / Modbus TCP Gateway"
  supported_function_codes: [1, 2, 3, 4, 5, 6, 15, 16]
  holding_registers:
    0: 100      # Tank level
    100: 2400   # Pressure setpoint
  coils:
    0: true     # Pump 1 active
    4: false    # Emergency stop
```

### Deployment

```bash
# Via YAML definition (recommended)
cp plugins/honeypot/honeypots/modbus-plc.yaml honeypots/

# Requires port 502 (or unprivileged alternative)
```

---

## MQTT Broker Honeypot

### MQTT Overview

Emulates an MQTT v3.1.1 broker. Parses the raw MQTT binary wire protocol from TCP without external dependencies. Supports authentication trapping, topic monitoring, and payload interception for IoT/ICS attack detection.

### Supported Packet Types

| Packet | Name       | Purpose                            |
| ------ | ---------- | ---------------------------------- |
| 1      | CONNECT    | Client authentication and tracking |
| 3      | PUBLISH    | Topic-based message interception   |
| 8      | SUBSCRIBE  | Subscription pattern monitoring    |
| 12     | PINGREQ    | Keep-alive handling                |
| 14     | DISCONNECT | Clean session teardown             |

### Attack Detection

- **Credential brute-force**: All CONNECT attempts with credentials are logged
- **Suspicious topics**: `$SYS/#`, `cmd/#`, `firmware/#` trigger elevated severity
- **Firmware tampering**: PUBLISH to `firmware/update` or `flash/` → `CRITICAL`
- **Wildcard harvesting**: Full `#` subscription patterns flagged

### Configuration (`mqtt_config`)

```yaml
mqtt_config:
  broker_name: "Eclipse Mosquitto/2.0.18"
  allow_anonymous: true
  max_qos: 2
  valid_credentials:
    - username: admin
      password: admin
    - username: device
      password: device123
  monitored_topics:
    - "factory/#"
    - "plc/#"
    - "$SYS/#"
    - "cmd/#"
    - "firmware/#"
```

---

## S7comm PLC Honeypot

### S7comm Overview

Emulates a Siemens S7-300/400 PLC over ISO-on-TCP (RFC 1006) with the full COTP + S7comm protocol stack. Designed to detect reconnaissance from tools like **PLCScan**, **Metasploit s7 modules**, and **Stuxnet-class** attacks.

### Protocol Stack

```text
TCP → TPKT (RFC 1006) → COTP (ISO 8073) → S7comm
```

### Supported Operations

| Operation               | Classification       | Severity     |
| ----------------------- | -------------------- | ------------ |
| COTP Connection Request | `PLC_SCAN`           | Low          |
| Setup Communication     | `PLC_SCAN`           | Medium       |
| Read Variable (DB)      | `PLC_SCAN`           | Medium       |
| Write Variable (DB)     | `SCADA_MANIPULATION` | **Critical** |
| SZL/CPU Identification  | `PLC_SCAN`           | High         |

### Configuration (`s7comm_config`)

```yaml
s7comm_config:
  rack: 0
  slot: 2
  cpu_type: "CPU 315-2 PN/DP"
  order_code: "6ES7 315-2EH14-0AB0"
  serial_number: "S C-HONYPOT0001"
  module_info: "S7-300"
  db_blocks:
    1:
      size: 256
      fill: 0
    2:
      size: 128
      fill: 0
```

### What It Catches

- **PLCScan / Nmap S7 scripts**: SZL queries return realistic CPU identification
- **Metasploit `s7_enumerate`**: Full setup communication and SZL response
- **Stuxnet-class writes**: Any DB write triggers `CRITICAL` severity with `SCADA_MANIPULATION` category
- **Memory extraction**: Multi-block reads flagged as systematic reconnaissance

---

## Architecture

```text
engine/iot/
├── __init__.py          # Handler factory (get_iot_handler)
├── modbus_handler.py    # Modbus TCP protocol handler
├── mqtt_handler.py      # MQTT v3.1.1 broker handler
└── s7comm_handler.py    # S7comm/COTP/TPKT handler
```

All handlers:

- Inherit from `BaseHandler` (same as SSH/HTTP/TCP handlers)
- Use the standard `_event_callback` mechanism for event emission
- Support stealth response delays
- Parse protocols directly from raw TCP (zero external dependencies)
- Are loaded dynamically via the handler factory in `engine/iot/__init__.py`

## YAML Definitions

Pre-built honeypot definitions are available in `honeypots/`:

| File               | Protocol | Scenario                  |
| ------------------ | -------- | ------------------------- |
| `modbus-plc.yaml`  | Modbus   | Water treatment plant PLC |
| `mqtt-broker.yaml` | MQTT     | Smart factory IoT broker  |
| `s7comm-plc.yaml`  | S7comm   | Siemens S7-300 PLC        |

## Testing

```bash
# Run IoT handler tests
pytest plugins/honeypot/tests/test_iot_honeypots.py -v

# Run all honeypot tests
pytest plugins/honeypot/tests/ -v
```

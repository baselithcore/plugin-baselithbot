"""S7comm/COTP protocol constants."""

# TPKT header size
TPKT_HEADER_SIZE = 4
TPKT_VERSION = 3

# COTP PDU types
COTP_CR = 0xE0  # Connection Request
COTP_CC = 0xD0  # Connection Confirm
COTP_DT = 0xF0  # Data Transfer

# S7comm constants
S7_PROTOCOL_ID = 0x32
S7_JOB = 0x01
S7_ACK_DATA = 0x03

# S7 function codes
S7_FUNC_SETUP_COMM = 0xF0
S7_FUNC_READ_VAR = 0x04
S7_FUNC_WRITE_VAR = 0x05
S7_FUNC_CPU_SERVICES = 0x00  # SZL / userdata

# S7 area codes
S7_AREA_DB = 0x84
S7_AREA_INPUTS = 0x81
S7_AREA_OUTPUTS = 0x82
S7_AREA_MARKERS = 0x83

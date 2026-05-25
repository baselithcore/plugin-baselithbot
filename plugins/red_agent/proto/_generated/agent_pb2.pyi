import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import duration_pb2 as _duration_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AgentCapability(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CAPABILITY_UNSPECIFIED: _ClassVar[AgentCapability]
    CAPABILITY_PROC_INVENTORY: _ClassVar[AgentCapability]
    CAPABILITY_PKG_INVENTORY: _ClassVar[AgentCapability]
    CAPABILITY_FILE_HASH: _ClassVar[AgentCapability]
    CAPABILITY_NET_LISTEN: _ClassVar[AgentCapability]
    CAPABILITY_USER_INVENTORY: _ClassVar[AgentCapability]
    CAPABILITY_EBPF_EXEC: _ClassVar[AgentCapability]
    CAPABILITY_EBPF_OPEN: _ClassVar[AgentCapability]
    CAPABILITY_EBPF_CONNECT: _ClassVar[AgentCapability]
    CAPABILITY_ESF_EXEC: _ClassVar[AgentCapability]
    CAPABILITY_ESF_FILE: _ClassVar[AgentCapability]
    CAPABILITY_SCAN_LOCAL_TRIVY: _ClassVar[AgentCapability]
    CAPABILITY_SCAN_LOCAL_NMAP: _ClassVar[AgentCapability]
    CAPABILITY_SCAN_LOCAL_NUCLEI: _ClassVar[AgentCapability]
    CAPABILITY_SCAN_LOCAL_SECRETS: _ClassVar[AgentCapability]
    CAPABILITY_SANDBOX_LANDLOCK: _ClassVar[AgentCapability]
    CAPABILITY_SANDBOX_SECCOMP: _ClassVar[AgentCapability]
    CAPABILITY_SANDBOX_SBX_EXEC: _ClassVar[AgentCapability]
    CAPABILITY_SELF_UPDATE: _ClassVar[AgentCapability]

class Severity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SEVERITY_UNSPECIFIED: _ClassVar[Severity]
    SEVERITY_INFO: _ClassVar[Severity]
    SEVERITY_LOW: _ClassVar[Severity]
    SEVERITY_MEDIUM: _ClassVar[Severity]
    SEVERITY_HIGH: _ClassVar[Severity]
    SEVERITY_CRITICAL: _ClassVar[Severity]

class LogLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOG_LEVEL_UNSPECIFIED: _ClassVar[LogLevel]
    LOG_LEVEL_TRACE: _ClassVar[LogLevel]
    LOG_LEVEL_DEBUG: _ClassVar[LogLevel]
    LOG_LEVEL_INFO: _ClassVar[LogLevel]
    LOG_LEVEL_WARN: _ClassVar[LogLevel]
    LOG_LEVEL_ERROR: _ClassVar[LogLevel]

CAPABILITY_UNSPECIFIED: AgentCapability
CAPABILITY_PROC_INVENTORY: AgentCapability
CAPABILITY_PKG_INVENTORY: AgentCapability
CAPABILITY_FILE_HASH: AgentCapability
CAPABILITY_NET_LISTEN: AgentCapability
CAPABILITY_USER_INVENTORY: AgentCapability
CAPABILITY_EBPF_EXEC: AgentCapability
CAPABILITY_EBPF_OPEN: AgentCapability
CAPABILITY_EBPF_CONNECT: AgentCapability
CAPABILITY_ESF_EXEC: AgentCapability
CAPABILITY_ESF_FILE: AgentCapability
CAPABILITY_SCAN_LOCAL_TRIVY: AgentCapability
CAPABILITY_SCAN_LOCAL_NMAP: AgentCapability
CAPABILITY_SCAN_LOCAL_NUCLEI: AgentCapability
CAPABILITY_SCAN_LOCAL_SECRETS: AgentCapability
CAPABILITY_SANDBOX_LANDLOCK: AgentCapability
CAPABILITY_SANDBOX_SECCOMP: AgentCapability
CAPABILITY_SANDBOX_SBX_EXEC: AgentCapability
CAPABILITY_SELF_UPDATE: AgentCapability
SEVERITY_UNSPECIFIED: Severity
SEVERITY_INFO: Severity
SEVERITY_LOW: Severity
SEVERITY_MEDIUM: Severity
SEVERITY_HIGH: Severity
SEVERITY_CRITICAL: Severity
LOG_LEVEL_UNSPECIFIED: LogLevel
LOG_LEVEL_TRACE: LogLevel
LOG_LEVEL_DEBUG: LogLevel
LOG_LEVEL_INFO: LogLevel
LOG_LEVEL_WARN: LogLevel
LOG_LEVEL_ERROR: LogLevel

class AgentMessage(_message.Message):
    __slots__ = (
        "seq",
        "nonce",
        "ts",
        "hello",
        "heartbeat",
        "telemetry",
        "command_result",
        "logs",
        "policy_ack",
        "rotation_request",
        "disconnect_notice",
    )
    SEQ_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    TS_FIELD_NUMBER: _ClassVar[int]
    HELLO_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_FIELD_NUMBER: _ClassVar[int]
    COMMAND_RESULT_FIELD_NUMBER: _ClassVar[int]
    LOGS_FIELD_NUMBER: _ClassVar[int]
    POLICY_ACK_FIELD_NUMBER: _ClassVar[int]
    ROTATION_REQUEST_FIELD_NUMBER: _ClassVar[int]
    DISCONNECT_NOTICE_FIELD_NUMBER: _ClassVar[int]
    seq: int
    nonce: bytes
    ts: _timestamp_pb2.Timestamp
    hello: AgentHello
    heartbeat: Heartbeat
    telemetry: TelemetryBatch
    command_result: CommandResult
    logs: LogBatch
    policy_ack: PolicyAck
    rotation_request: RotationRequest
    disconnect_notice: DisconnectNotice
    def __init__(
        self,
        seq: _Optional[int] = ...,
        nonce: _Optional[bytes] = ...,
        ts: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
        hello: _Optional[_Union[AgentHello, _Mapping]] = ...,
        heartbeat: _Optional[_Union[Heartbeat, _Mapping]] = ...,
        telemetry: _Optional[_Union[TelemetryBatch, _Mapping]] = ...,
        command_result: _Optional[_Union[CommandResult, _Mapping]] = ...,
        logs: _Optional[_Union[LogBatch, _Mapping]] = ...,
        policy_ack: _Optional[_Union[PolicyAck, _Mapping]] = ...,
        rotation_request: _Optional[_Union[RotationRequest, _Mapping]] = ...,
        disconnect_notice: _Optional[_Union[DisconnectNotice, _Mapping]] = ...,
    ) -> None: ...

class ServerMessage(_message.Message):
    __slots__ = (
        "seq",
        "nonce",
        "ts",
        "hello",
        "heartbeat",
        "command",
        "policy",
        "rotation_grant",
        "disconnect",
    )
    SEQ_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    TS_FIELD_NUMBER: _ClassVar[int]
    HELLO_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    POLICY_FIELD_NUMBER: _ClassVar[int]
    ROTATION_GRANT_FIELD_NUMBER: _ClassVar[int]
    DISCONNECT_FIELD_NUMBER: _ClassVar[int]
    seq: int
    nonce: bytes
    ts: _timestamp_pb2.Timestamp
    hello: ServerHello
    heartbeat: Heartbeat
    command: Command
    policy: PolicyUpdate
    rotation_grant: RotationGrant
    disconnect: Disconnect
    def __init__(
        self,
        seq: _Optional[int] = ...,
        nonce: _Optional[bytes] = ...,
        ts: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
        hello: _Optional[_Union[ServerHello, _Mapping]] = ...,
        heartbeat: _Optional[_Union[Heartbeat, _Mapping]] = ...,
        command: _Optional[_Union[Command, _Mapping]] = ...,
        policy: _Optional[_Union[PolicyUpdate, _Mapping]] = ...,
        rotation_grant: _Optional[_Union[RotationGrant, _Mapping]] = ...,
        disconnect: _Optional[_Union[Disconnect, _Mapping]] = ...,
    ) -> None: ...

class AgentHello(_message.Message):
    __slots__ = (
        "protocol_version",
        "daemon_version",
        "agent_uuid",
        "platform",
        "capabilities",
        "last_acked_server_seq",
    )
    PROTOCOL_VERSION_FIELD_NUMBER: _ClassVar[int]
    DAEMON_VERSION_FIELD_NUMBER: _ClassVar[int]
    AGENT_UUID_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    LAST_ACKED_SERVER_SEQ_FIELD_NUMBER: _ClassVar[int]
    protocol_version: int
    daemon_version: str
    agent_uuid: str
    platform: Platform
    capabilities: _containers.RepeatedScalarFieldContainer[AgentCapability]
    last_acked_server_seq: int
    def __init__(
        self,
        protocol_version: _Optional[int] = ...,
        daemon_version: _Optional[str] = ...,
        agent_uuid: _Optional[str] = ...,
        platform: _Optional[_Union[Platform, _Mapping]] = ...,
        capabilities: _Optional[_Iterable[_Union[AgentCapability, str]]] = ...,
        last_acked_server_seq: _Optional[int] = ...,
    ) -> None: ...

class ServerHello(_message.Message):
    __slots__ = (
        "protocol_version_min",
        "capabilities",
        "heartbeat_interval",
        "telemetry_batch_max",
        "message_size_max_bytes",
        "tenant_id_echo",
    )
    PROTOCOL_VERSION_MIN_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_INTERVAL_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_BATCH_MAX_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_SIZE_MAX_BYTES_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_ECHO_FIELD_NUMBER: _ClassVar[int]
    protocol_version_min: int
    capabilities: _containers.RepeatedScalarFieldContainer[AgentCapability]
    heartbeat_interval: _duration_pb2.Duration
    telemetry_batch_max: int
    message_size_max_bytes: int
    tenant_id_echo: str
    def __init__(
        self,
        protocol_version_min: _Optional[int] = ...,
        capabilities: _Optional[_Iterable[_Union[AgentCapability, str]]] = ...,
        heartbeat_interval: _Optional[
            _Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]
        ] = ...,
        telemetry_batch_max: _Optional[int] = ...,
        message_size_max_bytes: _Optional[int] = ...,
        tenant_id_echo: _Optional[str] = ...,
    ) -> None: ...

class Platform(_message.Message):
    __slots__ = (
        "os",
        "os_version",
        "kernel_version",
        "arch",
        "hostname",
        "boot_id",
        "cpu_count",
        "mem_total_bytes",
    )
    class OS(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        OS_UNSPECIFIED: _ClassVar[Platform.OS]
        OS_LINUX: _ClassVar[Platform.OS]
        OS_MACOS: _ClassVar[Platform.OS]
        OS_WINDOWS: _ClassVar[Platform.OS]

    OS_UNSPECIFIED: Platform.OS
    OS_LINUX: Platform.OS
    OS_MACOS: Platform.OS
    OS_WINDOWS: Platform.OS
    OS_FIELD_NUMBER: _ClassVar[int]
    OS_VERSION_FIELD_NUMBER: _ClassVar[int]
    KERNEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    ARCH_FIELD_NUMBER: _ClassVar[int]
    HOSTNAME_FIELD_NUMBER: _ClassVar[int]
    BOOT_ID_FIELD_NUMBER: _ClassVar[int]
    CPU_COUNT_FIELD_NUMBER: _ClassVar[int]
    MEM_TOTAL_BYTES_FIELD_NUMBER: _ClassVar[int]
    os: Platform.OS
    os_version: str
    kernel_version: str
    arch: str
    hostname: str
    boot_id: str
    cpu_count: int
    mem_total_bytes: int
    def __init__(
        self,
        os: _Optional[_Union[Platform.OS, str]] = ...,
        os_version: _Optional[str] = ...,
        kernel_version: _Optional[str] = ...,
        arch: _Optional[str] = ...,
        hostname: _Optional[str] = ...,
        boot_id: _Optional[str] = ...,
        cpu_count: _Optional[int] = ...,
        mem_total_bytes: _Optional[int] = ...,
    ) -> None: ...

class Heartbeat(_message.Message):
    __slots__ = ("health",)
    HEALTH_FIELD_NUMBER: _ClassVar[int]
    health: HealthSnapshot
    def __init__(
        self, health: _Optional[_Union[HealthSnapshot, _Mapping]] = ...
    ) -> None: ...

class HealthSnapshot(_message.Message):
    __slots__ = (
        "cpu_percent",
        "mem_rss_bytes",
        "disk_free_bytes",
        "telemetry_buffer_lag",
        "uptime",
    )
    CPU_PERCENT_FIELD_NUMBER: _ClassVar[int]
    MEM_RSS_BYTES_FIELD_NUMBER: _ClassVar[int]
    DISK_FREE_BYTES_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_BUFFER_LAG_FIELD_NUMBER: _ClassVar[int]
    UPTIME_FIELD_NUMBER: _ClassVar[int]
    cpu_percent: float
    mem_rss_bytes: int
    disk_free_bytes: int
    telemetry_buffer_lag: int
    uptime: _duration_pb2.Duration
    def __init__(
        self,
        cpu_percent: _Optional[float] = ...,
        mem_rss_bytes: _Optional[int] = ...,
        disk_free_bytes: _Optional[int] = ...,
        telemetry_buffer_lag: _Optional[int] = ...,
        uptime: _Optional[
            _Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]
        ] = ...,
    ) -> None: ...

class TelemetryBatch(_message.Message):
    __slots__ = ("batch_id", "events")
    BATCH_ID_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    batch_id: str
    events: _containers.RepeatedCompositeFieldContainer[TelemetryEvent]
    def __init__(
        self,
        batch_id: _Optional[str] = ...,
        events: _Optional[_Iterable[_Union[TelemetryEvent, _Mapping]]] = ...,
    ) -> None: ...

class TelemetryEvent(_message.Message):
    __slots__ = ("observed_at", "kind", "severity", "attributes", "correlation_id")
    OBSERVED_AT_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    observed_at: _timestamp_pb2.Timestamp
    kind: str
    severity: Severity
    attributes: _struct_pb2.Struct
    correlation_id: str
    def __init__(
        self,
        observed_at: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
        kind: _Optional[str] = ...,
        severity: _Optional[_Union[Severity, str]] = ...,
        attributes: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
        correlation_id: _Optional[str] = ...,
    ) -> None: ...

class LogBatch(_message.Message):
    __slots__ = ("entries",)
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[LogEntry]
    def __init__(
        self, entries: _Optional[_Iterable[_Union[LogEntry, _Mapping]]] = ...
    ) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ("ts", "level", "target", "message", "fields", "trace_id")
    TS_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    ts: _timestamp_pb2.Timestamp
    level: LogLevel
    target: str
    message: str
    fields: _struct_pb2.Struct
    trace_id: str
    def __init__(
        self,
        ts: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
        level: _Optional[_Union[LogLevel, str]] = ...,
        target: _Optional[str] = ...,
        message: _Optional[str] = ...,
        fields: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
        trace_id: _Optional[str] = ...,
    ) -> None: ...

class Command(_message.Message):
    __slots__ = (
        "idempotency_key",
        "correlation_id",
        "deadline",
        "run_inventory",
        "run_local_scan",
        "hash_files",
        "collect_artifact",
        "apply_config",
        "self_update",
    )
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_FIELD_NUMBER: _ClassVar[int]
    RUN_INVENTORY_FIELD_NUMBER: _ClassVar[int]
    RUN_LOCAL_SCAN_FIELD_NUMBER: _ClassVar[int]
    HASH_FILES_FIELD_NUMBER: _ClassVar[int]
    COLLECT_ARTIFACT_FIELD_NUMBER: _ClassVar[int]
    APPLY_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SELF_UPDATE_FIELD_NUMBER: _ClassVar[int]
    idempotency_key: str
    correlation_id: str
    deadline: _timestamp_pb2.Timestamp
    run_inventory: RunInventoryCmd
    run_local_scan: RunLocalScanCmd
    hash_files: HashFilesCmd
    collect_artifact: CollectArtifactCmd
    apply_config: ApplyConfigCmd
    self_update: SelfUpdateCmd
    def __init__(
        self,
        idempotency_key: _Optional[str] = ...,
        correlation_id: _Optional[str] = ...,
        deadline: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
        run_inventory: _Optional[_Union[RunInventoryCmd, _Mapping]] = ...,
        run_local_scan: _Optional[_Union[RunLocalScanCmd, _Mapping]] = ...,
        hash_files: _Optional[_Union[HashFilesCmd, _Mapping]] = ...,
        collect_artifact: _Optional[_Union[CollectArtifactCmd, _Mapping]] = ...,
        apply_config: _Optional[_Union[ApplyConfigCmd, _Mapping]] = ...,
        self_update: _Optional[_Union[SelfUpdateCmd, _Mapping]] = ...,
    ) -> None: ...

class RunInventoryCmd(_message.Message):
    __slots__ = ("kinds",)
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_UNSPECIFIED: _ClassVar[RunInventoryCmd.Kind]
        KIND_PACKAGES: _ClassVar[RunInventoryCmd.Kind]
        KIND_PROCESSES: _ClassVar[RunInventoryCmd.Kind]
        KIND_USERS: _ClassVar[RunInventoryCmd.Kind]
        KIND_LISTENERS: _ClassVar[RunInventoryCmd.Kind]

    KIND_UNSPECIFIED: RunInventoryCmd.Kind
    KIND_PACKAGES: RunInventoryCmd.Kind
    KIND_PROCESSES: RunInventoryCmd.Kind
    KIND_USERS: RunInventoryCmd.Kind
    KIND_LISTENERS: RunInventoryCmd.Kind
    KINDS_FIELD_NUMBER: _ClassVar[int]
    kinds: _containers.RepeatedScalarFieldContainer[RunInventoryCmd.Kind]
    def __init__(
        self, kinds: _Optional[_Iterable[_Union[RunInventoryCmd.Kind, str]]] = ...
    ) -> None: ...

class RunLocalScanCmd(_message.Message):
    __slots__ = ("bundle_id", "argv", "limits")
    BUNDLE_ID_FIELD_NUMBER: _ClassVar[int]
    ARGV_FIELD_NUMBER: _ClassVar[int]
    LIMITS_FIELD_NUMBER: _ClassVar[int]
    bundle_id: str
    argv: _containers.RepeatedScalarFieldContainer[str]
    limits: ResourceLimits
    def __init__(
        self,
        bundle_id: _Optional[str] = ...,
        argv: _Optional[_Iterable[str]] = ...,
        limits: _Optional[_Union[ResourceLimits, _Mapping]] = ...,
    ) -> None: ...

class ResourceLimits(_message.Message):
    __slots__ = ("cpu_quota_us_per_sec", "mem_max_bytes", "pids_max", "wall_timeout")
    CPU_QUOTA_US_PER_SEC_FIELD_NUMBER: _ClassVar[int]
    MEM_MAX_BYTES_FIELD_NUMBER: _ClassVar[int]
    PIDS_MAX_FIELD_NUMBER: _ClassVar[int]
    WALL_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    cpu_quota_us_per_sec: int
    mem_max_bytes: int
    pids_max: int
    wall_timeout: _duration_pb2.Duration
    def __init__(
        self,
        cpu_quota_us_per_sec: _Optional[int] = ...,
        mem_max_bytes: _Optional[int] = ...,
        pids_max: _Optional[int] = ...,
        wall_timeout: _Optional[
            _Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]
        ] = ...,
    ) -> None: ...

class HashFilesCmd(_message.Message):
    __slots__ = ("paths", "algorithm")
    class Algorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        ALGORITHM_UNSPECIFIED: _ClassVar[HashFilesCmd.Algorithm]
        ALGORITHM_SHA256: _ClassVar[HashFilesCmd.Algorithm]
        ALGORITHM_BLAKE3: _ClassVar[HashFilesCmd.Algorithm]

    ALGORITHM_UNSPECIFIED: HashFilesCmd.Algorithm
    ALGORITHM_SHA256: HashFilesCmd.Algorithm
    ALGORITHM_BLAKE3: HashFilesCmd.Algorithm
    PATHS_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    paths: _containers.RepeatedScalarFieldContainer[str]
    algorithm: HashFilesCmd.Algorithm
    def __init__(
        self,
        paths: _Optional[_Iterable[str]] = ...,
        algorithm: _Optional[_Union[HashFilesCmd.Algorithm, str]] = ...,
    ) -> None: ...

class CollectArtifactCmd(_message.Message):
    __slots__ = ("path", "max_bytes")
    PATH_FIELD_NUMBER: _ClassVar[int]
    MAX_BYTES_FIELD_NUMBER: _ClassVar[int]
    path: str
    max_bytes: int
    def __init__(
        self, path: _Optional[str] = ..., max_bytes: _Optional[int] = ...
    ) -> None: ...

class ApplyConfigCmd(_message.Message):
    __slots__ = ("config",)
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    config: _struct_pb2.Struct
    def __init__(
        self, config: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...
    ) -> None: ...

class SelfUpdateCmd(_message.Message):
    __slots__ = ("target_version", "bundle_url", "bundle_sig")
    TARGET_VERSION_FIELD_NUMBER: _ClassVar[int]
    BUNDLE_URL_FIELD_NUMBER: _ClassVar[int]
    BUNDLE_SIG_FIELD_NUMBER: _ClassVar[int]
    target_version: str
    bundle_url: str
    bundle_sig: bytes
    def __init__(
        self,
        target_version: _Optional[str] = ...,
        bundle_url: _Optional[str] = ...,
        bundle_sig: _Optional[bytes] = ...,
    ) -> None: ...

class CommandResult(_message.Message):
    __slots__ = (
        "idempotency_key",
        "correlation_id",
        "status",
        "error_code",
        "error_message",
        "payload",
        "artifact",
        "elapsed",
    )
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        STATUS_UNSPECIFIED: _ClassVar[CommandResult.Status]
        STATUS_OK: _ClassVar[CommandResult.Status]
        STATUS_PARTIAL: _ClassVar[CommandResult.Status]
        STATUS_FAILED: _ClassVar[CommandResult.Status]
        STATUS_TIMEOUT: _ClassVar[CommandResult.Status]
        STATUS_REJECTED: _ClassVar[CommandResult.Status]
        STATUS_UNSUPPORTED: _ClassVar[CommandResult.Status]

    STATUS_UNSPECIFIED: CommandResult.Status
    STATUS_OK: CommandResult.Status
    STATUS_PARTIAL: CommandResult.Status
    STATUS_FAILED: CommandResult.Status
    STATUS_TIMEOUT: CommandResult.Status
    STATUS_REJECTED: CommandResult.Status
    STATUS_UNSUPPORTED: CommandResult.Status
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_FIELD_NUMBER: _ClassVar[int]
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    idempotency_key: str
    correlation_id: str
    status: CommandResult.Status
    error_code: str
    error_message: str
    payload: _struct_pb2.Struct
    artifact: ArtifactChunk
    elapsed: _duration_pb2.Duration
    def __init__(
        self,
        idempotency_key: _Optional[str] = ...,
        correlation_id: _Optional[str] = ...,
        status: _Optional[_Union[CommandResult.Status, str]] = ...,
        error_code: _Optional[str] = ...,
        error_message: _Optional[str] = ...,
        payload: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
        artifact: _Optional[_Union[ArtifactChunk, _Mapping]] = ...,
        elapsed: _Optional[
            _Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]
        ] = ...,
    ) -> None: ...

class ArtifactChunk(_message.Message):
    __slots__ = ("artifact_id", "chunk_index", "chunk_total", "data", "sha256_hex")
    ARTIFACT_ID_FIELD_NUMBER: _ClassVar[int]
    CHUNK_INDEX_FIELD_NUMBER: _ClassVar[int]
    CHUNK_TOTAL_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    SHA256_HEX_FIELD_NUMBER: _ClassVar[int]
    artifact_id: str
    chunk_index: int
    chunk_total: int
    data: bytes
    sha256_hex: str
    def __init__(
        self,
        artifact_id: _Optional[str] = ...,
        chunk_index: _Optional[int] = ...,
        chunk_total: _Optional[int] = ...,
        data: _Optional[bytes] = ...,
        sha256_hex: _Optional[str] = ...,
    ) -> None: ...

class PolicyUpdate(_message.Message):
    __slots__ = ("version", "bundle", "bundle_sig", "issued_at", "expires_at")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    BUNDLE_FIELD_NUMBER: _ClassVar[int]
    BUNDLE_SIG_FIELD_NUMBER: _ClassVar[int]
    ISSUED_AT_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    version: int
    bundle: bytes
    bundle_sig: bytes
    issued_at: _timestamp_pb2.Timestamp
    expires_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        version: _Optional[int] = ...,
        bundle: _Optional[bytes] = ...,
        bundle_sig: _Optional[bytes] = ...,
        issued_at: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
        expires_at: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
    ) -> None: ...

class PolicyAck(_message.Message):
    __slots__ = ("version", "applied", "error")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    APPLIED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    version: int
    applied: bool
    error: str
    def __init__(
        self,
        version: _Optional[int] = ...,
        applied: bool = ...,
        error: _Optional[str] = ...,
    ) -> None: ...

class RotationRequest(_message.Message):
    __slots__ = ("csr_pem", "old_cert_not_after")
    CSR_PEM_FIELD_NUMBER: _ClassVar[int]
    OLD_CERT_NOT_AFTER_FIELD_NUMBER: _ClassVar[int]
    csr_pem: bytes
    old_cert_not_after: _timestamp_pb2.Timestamp
    def __init__(
        self,
        csr_pem: _Optional[bytes] = ...,
        old_cert_not_after: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
    ) -> None: ...

class RotationGrant(_message.Message):
    __slots__ = ("new_cert_pem", "chain_pem", "not_after")
    NEW_CERT_PEM_FIELD_NUMBER: _ClassVar[int]
    CHAIN_PEM_FIELD_NUMBER: _ClassVar[int]
    NOT_AFTER_FIELD_NUMBER: _ClassVar[int]
    new_cert_pem: bytes
    chain_pem: bytes
    not_after: _timestamp_pb2.Timestamp
    def __init__(
        self,
        new_cert_pem: _Optional[bytes] = ...,
        chain_pem: _Optional[bytes] = ...,
        not_after: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
    ) -> None: ...

class DisconnectNotice(_message.Message):
    __slots__ = ("reason", "message")
    class Reason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        REASON_UNSPECIFIED: _ClassVar[DisconnectNotice.Reason]
        REASON_SHUTDOWN: _ClassVar[DisconnectNotice.Reason]
        REASON_UPGRADING: _ClassVar[DisconnectNotice.Reason]
        REASON_RECONFIG: _ClassVar[DisconnectNotice.Reason]

    REASON_UNSPECIFIED: DisconnectNotice.Reason
    REASON_SHUTDOWN: DisconnectNotice.Reason
    REASON_UPGRADING: DisconnectNotice.Reason
    REASON_RECONFIG: DisconnectNotice.Reason
    REASON_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    reason: DisconnectNotice.Reason
    message: str
    def __init__(
        self,
        reason: _Optional[_Union[DisconnectNotice.Reason, str]] = ...,
        message: _Optional[str] = ...,
    ) -> None: ...

class Disconnect(_message.Message):
    __slots__ = ("reason", "message", "retry_after")
    class Reason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        REASON_UNSPECIFIED: _ClassVar[Disconnect.Reason]
        REASON_SERVER_SHUTDOWN: _ClassVar[Disconnect.Reason]
        REASON_RATE_LIMIT: _ClassVar[Disconnect.Reason]
        REASON_INCOMPATIBLE: _ClassVar[Disconnect.Reason]
        REASON_REVOKED: _ClassVar[Disconnect.Reason]
        REASON_TENANT_DISABLED: _ClassVar[Disconnect.Reason]

    REASON_UNSPECIFIED: Disconnect.Reason
    REASON_SERVER_SHUTDOWN: Disconnect.Reason
    REASON_RATE_LIMIT: Disconnect.Reason
    REASON_INCOMPATIBLE: Disconnect.Reason
    REASON_REVOKED: Disconnect.Reason
    REASON_TENANT_DISABLED: Disconnect.Reason
    REASON_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRY_AFTER_FIELD_NUMBER: _ClassVar[int]
    reason: Disconnect.Reason
    message: str
    retry_after: _duration_pb2.Duration
    def __init__(
        self,
        reason: _Optional[_Union[Disconnect.Reason, str]] = ...,
        message: _Optional[str] = ...,
        retry_after: _Optional[
            _Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]
        ] = ...,
    ) -> None: ...

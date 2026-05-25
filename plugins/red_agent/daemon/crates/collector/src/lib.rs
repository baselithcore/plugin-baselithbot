//! Telemetry collectors.
//!
//! Phase 1: synchronous snapshots via `sysinfo` (process list, listening
//! sockets, package inventory) plus on-demand SHA-256 file hashing.
//! Phase 2: eBPF tracepoints on linux, Endpoint Security Framework
//! subscriptions on macOS.
//!
//! Each collector emits `TelemetryEvent`s on a shared bounded channel
//! that the transport crate drains into the gRPC stream.
//!
//! Stable wire kinds emitted by Phase 1:
//!
//! | kind                   | meaning                                  |
//! |------------------------|------------------------------------------|
//! | `host.proc.snapshot`        | running processes                   |
//! | `host.pkg.snapshot`         | installed system packages           |
//! | `host.net.listeners`        | listening tcp/udp sockets           |
//! | `host.file.hashes`          | sha256 digests of requested files   |
//! | `host.user.snapshot`        | local users / groups / sudoers      |
//! | `host.persistence.snapshot` | autostart / cron / systemd / launchd|
//! | `host.kernel.modules`       | loaded kernel modules / kexts       |
//! | `host.ssh.snapshot`         | authorized_keys + sshd_config meta  |
//! | `host.daemon.selfintegrity` | running daemon binary sha256        |

#![deny(unsafe_code)]
#![warn(missing_docs)]

pub mod firewall;
pub mod hash;
pub mod inventory;
pub mod kernel;
pub mod mitre;
pub mod net;
pub mod persistence;
pub mod selfintegrity;
pub mod ssh;
pub mod users;

use baselith_redagent_proto::TelemetryEvent;
use prost_types::{value::Kind, Struct, Value};
use tokio::sync::mpsc;

/// Producer trait every collector implements.
pub trait Collector: Send + Sync {
    /// Stable namespaced name (e.g. `"linux.proc.exec"`).
    fn name(&self) -> &'static str;

    /// Run the collector to completion. Implementations return when
    /// cancelled by the runtime.
    fn run(&self, sink: mpsc::Sender<TelemetryEvent>);
}

/// Default sink channel capacity. Buffered telemetry blocks the
/// collector when the transport stream is slow to drain — better
/// than unbounded growth that OOM-kills the daemon under load.
pub const DEFAULT_SINK_CAPACITY: usize = 1024;

/// Build a `TelemetryEvent` from a JSON attribute payload. Centralized
/// so every collector emits a consistent envelope (kind + severity +
/// observed_at + struct attributes).
pub fn build_event(
    kind: &str,
    severity: baselith_redagent_proto::Severity,
    attributes: serde_json::Value,
) -> TelemetryEvent {
    TelemetryEvent {
        observed_at: Some(now_timestamp()),
        kind: kind.to_string(),
        severity: severity as i32,
        attributes: Some(json_to_struct(attributes)),
        correlation_id: String::new(),
    }
}

/// Build a `TelemetryEvent` with a caller-supplied correlation id.
/// Used for events emitted as part of a server-issued command so the
/// backend can stitch findings back to the request.
pub fn build_event_corr(
    kind: &str,
    severity: baselith_redagent_proto::Severity,
    attributes: serde_json::Value,
    correlation_id: &str,
) -> TelemetryEvent {
    TelemetryEvent {
        observed_at: Some(now_timestamp()),
        kind: kind.to_string(),
        severity: severity as i32,
        attributes: Some(json_to_struct(attributes)),
        correlation_id: correlation_id.to_string(),
    }
}

/// Current wall-clock as a protobuf `Timestamp`. UNIX-epoch monotonic
/// for the daemon process. Phase 2 will swap this for a CLOCK_BOOTTIME
/// derived value where available so events from a host whose wall
/// clock jumps backwards still correlate against the boot id.
pub fn now_timestamp() -> prost_types::Timestamp {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    prost_types::Timestamp {
        seconds: now.as_secs() as i64,
        nanos: now.subsec_nanos() as i32,
    }
}

/// Convert a `serde_json::Value` into a protobuf `Struct`. Top-level
/// scalars are wrapped under a `value` key so the protobuf type
/// constraint (Struct expects an object) is preserved without losing
/// the original payload.
pub fn json_to_struct(value: serde_json::Value) -> Struct {
    match value {
        serde_json::Value::Object(map) => {
            let fields = map
                .into_iter()
                .map(|(k, v)| (k, json_to_value(v)))
                .collect();
            Struct { fields }
        }
        other => {
            let mut s = Struct::default();
            s.fields.insert("value".to_string(), json_to_value(other));
            s
        }
    }
}

/// Convert a single `serde_json::Value` into a protobuf `Value`.
pub fn json_to_value(value: serde_json::Value) -> Value {
    let kind = match value {
        serde_json::Value::Null => Kind::NullValue(0),
        serde_json::Value::Bool(b) => Kind::BoolValue(b),
        serde_json::Value::Number(n) => {
            if let Some(f) = n.as_f64() {
                Kind::NumberValue(f)
            } else {
                Kind::StringValue(n.to_string())
            }
        }
        serde_json::Value::String(s) => Kind::StringValue(s),
        serde_json::Value::Array(arr) => Kind::ListValue(prost_types::ListValue {
            values: arr.into_iter().map(json_to_value).collect(),
        }),
        serde_json::Value::Object(map) => Kind::StructValue(Struct {
            fields: map
                .into_iter()
                .map(|(k, v)| (k, json_to_value(v)))
                .collect(),
        }),
    };
    Value { kind: Some(kind) }
}

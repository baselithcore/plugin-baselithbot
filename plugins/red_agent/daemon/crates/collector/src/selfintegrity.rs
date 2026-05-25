//! Daemon self-integrity probe.
//!
//! Computes the sha256 of the running daemon binary at every
//! invocation. The backend persists the first observed value as the
//! per-agent baseline; subsequent snapshots that diverge surface a
//! `host.daemon.tampered` finding without the daemon needing to know
//! its own baseline (which an attacker who has rooted the host could
//! tamper with as readily as the binary).
//!
//! Also captures the resolved path, file size, and modification time
//! so basic file-tampering attacks (timestomp, partial overwrite) can
//! be ruled in or out at a glance.
//!
//! Wire kind: `host.daemon.selfintegrity`.

use baselith_redagent_proto as proto;
use serde_json::json;

use crate::{build_event, hash::hash_file};

const SCHEMA_VERSION: u32 = 1;

/// Hash the running daemon binary and emit the event.
pub fn snapshot(severity: proto::Severity, daemon_version: &str) -> proto::TelemetryEvent {
    let exe = std::env::current_exe().ok();
    let attrs = if let Some(path) = exe {
        let digest = hash_file(&path);
        let metadata = std::fs::metadata(&path).ok();
        let mtime = metadata.as_ref().and_then(|m| {
            m.modified()
                .ok()
                .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                .map(|d| d.as_secs())
        });
        json!({
            "schema_version": SCHEMA_VERSION,
            "daemon_version": daemon_version,
            "exe_path": digest.path,
            "sha256": digest.sha256,
            "size_bytes": digest.size_bytes,
            "mtime_unix": mtime,
            "error_code": digest.error_code,
        })
    } else {
        json!({
            "schema_version": SCHEMA_VERSION,
            "daemon_version": daemon_version,
            "error_code": "EXE_PATH_UNAVAILABLE",
        })
    };
    build_event("host.daemon.selfintegrity", severity, attrs)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_emits_event_with_kind() {
        let evt = snapshot(proto::Severity::Info, "0.1.0");
        assert_eq!(evt.kind, "host.daemon.selfintegrity");
        assert!(evt.attributes.is_some());
    }
}
